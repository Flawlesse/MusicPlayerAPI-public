from io import BytesIO

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage as storage
from django.db import models
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from PIL import Image

from music_player_api.utils import (
    upload_audio_to,
    upload_avatar_to,
    upload_coverimg_to,
    upload_thumbnail_to,
    validate_file_size,
    validate_is_music,
)


# MODELS
class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User model."""

    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    avatar = models.ImageField(
        upload_to=upload_avatar_to,
        blank=True,
        null=True,
        validators=[validate_file_size],
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def __str__(self):
        return self.email


class Song(models.Model):
    added_by = models.ForeignKey(
        to=User, on_delete=models.CASCADE, null=False, related_name="songs"
    )
    title = models.CharField(blank=False, null=False, max_length=100)
    author = models.CharField(blank=False, null=False, max_length=100)
    lyrics = models.TextField(blank=True, null=False)
    audio_file = models.FileField(
        upload_to=upload_audio_to,
        blank=True,
        null=True,
        validators=[validate_is_music, validate_file_size],
    )
    cover_img = models.ImageField(
        upload_to=upload_coverimg_to,
        blank=True,
        null=True,
        validators=[validate_file_size],
    )
    thumbnail = models.ImageField(
        upload_to=upload_thumbnail_to,
        blank=True,
        null=True,
        validators=[validate_file_size],
    )

    def __str__(self):
        return f"{self.id}: {self.title}; Author: {self.author}"


class Genre(models.Model):
    name = models.CharField(blank=False, null=False, max_length=100, unique=True)
    songs = models.ManyToManyField(to=Song, related_name="genres", blank=True)

    def __str__(self):
        return f"{self.id}: {self.name}"


class Playlist(models.Model):
    name = models.CharField(blank=False, null=False, max_length=100)
    added_by = models.ForeignKey(
        to=User, on_delete=models.CASCADE, null=False, related_name="playlists"
    )
    songs = models.ManyToManyField(
        to=Song, through="SongPlaylist", related_name="playlists", blank=True
    )

    def __str__(self):
        return f"{self.id}: {self.name}"


class SongPlaylist(models.Model):
    song = models.ForeignKey(to=Song, on_delete=models.CASCADE)
    playlist = models.ForeignKey(to=Playlist, on_delete=models.CASCADE)
    order_num = models.IntegerField(null=False)  # order id of song in playlist

    def __str__(self):
        return f"{self.id}: {self.song.name}; {self.playlist.name}"


# SIGNAL RECEIVERS


@receiver(models.signals.post_delete, sender=User)
def remove_avatar_on_delete(sender, instance, using, **kwargs):
    if instance.avatar is not None:
        instance.avatar.delete(save=False)
    return True


@receiver(models.signals.pre_save, sender=User)
def remove_old_avatar_on_save(sender, instance, using, **kwargs):
    try:
        old_instance = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        return True
    if old_instance.avatar is not None and instance.avatar != old_instance.avatar:
        old_instance.avatar.delete(save=False)
    return True


@receiver(models.signals.post_delete, sender=Song)
def remove_audiofile_and_coverimg_on_delete(sender, instance, using, **kwargs):
    if instance.cover_img is not None:
        instance.cover_img.delete(save=False)
    if instance.thumbnail is not None:
        instance.thumbnail.delete(save=False)
    if instance.audio_file is not None:
        instance.audio_file.delete(save=False)
    return True


@receiver(models.signals.pre_save, sender=Song)
def remove_old_coverimg_on_save(sender, instance, using, **kwargs):
    try:
        old_instance = Song.objects.get(pk=instance.pk)
    except Song.DoesNotExist:
        return True
    if (
        old_instance.cover_img is not None
        and instance.cover_img != old_instance.cover_img
    ):
        old_instance.cover_img.delete(save=False)
    return True
