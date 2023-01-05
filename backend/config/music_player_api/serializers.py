import string

import sendgrid
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import BaseUserManager
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, Serializer, ValidationError

from music_player_api.models import Genre, Playlist, Song, SongPlaylist, User
from music_player_api.utils import ResetCodeManager, SessionTokenManager, make_thumbnail

# User model serializers


class RegisterUserSerializer(ModelSerializer):
    confirmation_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("email", "password", "confirmation_password")
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def create(self, validated_data):
        validated_data.pop("confirmation_password")
        email = validated_data.pop("email")
        password = validated_data.pop("password")
        return User.objects.create_user(email, password, **validated_data)

    def validate(self, raw_data):
        if raw_data["password"] != raw_data["confirmation_password"]:
            raise serializers.ValidationError("Passwords don't match!")
        return raw_data


class ChangePasswordSerializer(ModelSerializer):
    new_password = serializers.CharField(write_only=True)
    confirmation_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("password", "new_password", "confirmation_password")
        extra_kwargs = {"password": {"write_only": True}}

    def __init__(self, *args, **kwargs):
        kwargs["partial"] = True
        super(ChangePasswordSerializer, self).__init__(*args, **kwargs)

    def validate(self, raw_data):
        if any(list(map(lambda x: x not in raw_data, self.Meta.fields))):
            raise ValidationError("No fields were provided.")
        if not check_password(raw_data["password"], self.instance.password):
            raise serializers.ValidationError("Old password is incorrect!")
        if check_password(raw_data["new_password"], self.instance.password):
            raise serializers.ValidationError(
                "Changing to the same password is not allowed!"
            )
        if raw_data["new_password"] != raw_data["confirmation_password"]:
            raise serializers.ValidationError("New passwords don't match!")
        return raw_data

    def save(self):
        self.instance.set_password(self.validated_data["new_password"])
        self.instance.save()
        return self.instance


class ChangePasswordForgotSerializer(Serializer):
    email = serializers.EmailField(required=True)
    session_token = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True)
    confirmation_password = serializers.CharField(write_only=True, required=True)

    def validate(self, raw_data):
        norm_email = BaseUserManager.normalize_email(raw_data["email"])
        if not User.objects.filter(email=norm_email).exists():
            raise ValidationError({"email": f"No user {norm_email} was found."})
        self.instance = User.objects.get(email=norm_email)

        if len(raw_data["session_token"]) != 32 or not all(
            [
                (ch in (string.digits + string.ascii_letters))
                for ch in raw_data["session_token"]
            ]
        ):
            raise ValidationError({"session_token": "Invalid session token provided."})
        if raw_data["new_password"] != raw_data["confirmation_password"]:
            raise serializers.ValidationError("New passwords don't match!")
        if not SessionTokenManager.try_use_token(norm_email, raw_data["session_token"]):
            raise ValidationError(
                {"session_token": "Session token has expired or it is incorrect."}
            )
        return raw_data

    def save(self):
        # instance will be provided during validation!!!
        self.instance.set_password(self.validated_data["new_password"])
        self.instance.save()
        return self.instance


class FindEmailSerializer(Serializer):
    email = serializers.EmailField(required=True)

    def validate(self, raw_data):
        norm_email = BaseUserManager.normalize_email(raw_data["email"])
        if not User.objects.filter(email=norm_email).exists():
            raise ValidationError({"email": f"No user {norm_email} was found."})
        return raw_data

    def save(self):
        email = self.validated_data["email"]
        code_to_send = ResetCodeManager.get_or_create_code(email)
        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        data = {
            "personalizations": [
                {
                    "to": [{"email": email}],
                    "subject": "Reset password code",
                }
            ],
            "from": {"email": settings.SENDGRID_SENDER_EMAIL},
            "content": [
                {
                    "type": "text/plain",
                    "value": f"Hi there, {email}. "
                    + f"Please enter this code to reset your password: {code_to_send}. "
                    + "It is only working for 2 minutes, so you should hurry!",
                }
            ],
        }
        try:
            response = sg.client.mail.send.post(request_body=data)
        except:
            if settings.DEBUG:
                print("Failed to send an email.")

        if settings.DEBUG:
            print("Email status: ")
            print(response.status_code)
            print(response.body)
            print(response.headers)
        return User.objects.get(email=email)


class CodeWithEmailSerializer(Serializer):
    email = serializers.EmailField(required=True)
    code = serializers.CharField(required=True)

    def validate(self, raw_data):
        norm_email = BaseUserManager.normalize_email(raw_data["email"])
        if not User.objects.filter(email=norm_email).exists():
            raise ValidationError({"email": f"No user {norm_email} was found."})
        if len(raw_data["code"]) != 4 or not all(
            [(ch in string.digits) for ch in raw_data["code"]]
        ):
            raise ValidationError({"code": "Invalid code provided."})
        if not ResetCodeManager.try_use_code(norm_email, raw_data["code"]):
            raise ValidationError({"code": "Code has expired or it is incorrect."})
        return raw_data

    def save(self, **kwargs):
        """Overriden to return password reset session token."""
        email = self.validated_data["email"]
        session_token = SessionTokenManager.get_or_create_token(email)
        return session_token


class UserInfoSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "avatar",
        )
        read_only_fields = ("email",)

    def save(self, **kwargs):
        try:
            if self.validated_data["avatar"] is None:
                self.instance.avatar.delete(save=False)
        except KeyError:
            pass
        super().save(**kwargs)


# Song model serializers


class GetFlatSongSerializer(ModelSerializer):
    can_edit = serializers.SerializerMethodField()
    added_by = serializers.StringRelatedField()

    class Meta:
        model = Song
        fields = [
            "id",
            "added_by",
            "audio_file",
            "thumbnail",
            "title",
            "author",
            "genres",
            "can_edit",
        ]

    def get_can_edit(self, obj):
        return self.context["user"] == obj.added_by


class GetSongSerializer(ModelSerializer):
    can_edit = serializers.SerializerMethodField()
    added_by = serializers.StringRelatedField()

    class Meta:
        model = Song
        fields = [
            "id",
            "added_by",
            "audio_file",
            "cover_img",
            "thumbnail",
            "title",
            "author",
            "genres",
            "lyrics",
            "can_edit",
        ]

    def get_can_edit(self, obj):
        return self.context["user"] == obj.added_by


class CreateSongSerializer(ModelSerializer):
    genres = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Genre.objects.all(), read_only=False
    )

    class Meta:
        model = Song
        fields = ["audio_file", "cover_img", "title", "author", "genres", "lyrics"]
        extra_kwargs = {"audio_file": {"required": True, "allow_null": False}}

    def create(self, validated_data):
        tmp_audio_file = validated_data.pop("audio_file")
        tmp_cover_img = validated_data.pop("cover_img", None)
        genres = validated_data.pop("genres")
        instance = self.Meta.model.objects.create(**validated_data)
        instance.genres.set(genres)
        instance.audio_file.save(tmp_audio_file.name, tmp_audio_file.file, True)
        if tmp_cover_img is not None:
            instance.cover_img.save(tmp_cover_img.name, tmp_cover_img.file, True)
            make_thumbnail(instance)
        instance.refresh_from_db()
        return instance

    def save(self, **kwargs):
        kwargs["added_by"] = self.context["request"].user
        return super().save(**kwargs)


class EditSongSerializer(ModelSerializer):
    class Meta:
        model = Song
        fields = ["cover_img", "title", "author", "genres", "lyrics"]

    def update(self, instance, validated_data):
        super().update(instance, validated_data)
        if "cover_img" in validated_data:
            instance.thumbnail.delete()
            if validated_data["cover_img"] is not None:
                make_thumbnail(instance)
        instance.refresh_from_db()
        return instance


class GetSongInPlaylistSerializer(ModelSerializer):
    can_edit = serializers.SerializerMethodField()
    added_by = serializers.StringRelatedField()
    order_num = serializers.SerializerMethodField()
    genres = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Song
        fields = [
            "id",
            "order_num",
            "added_by",
            "audio_file",
            "thumbnail",
            "title",
            "author",
            "genres",
            "can_edit",
        ]

    def get_can_edit(self, obj):
        return self.context["user"] == obj.added_by

    def get_order_num(self, obj):
        curr_song = self.instance
        curr_playlist = self.context["playlist"]
        return SongPlaylist.objects.get(
            song=curr_song, playlist=curr_playlist
        ).order_num


# Genre model serializers


class GetGenreSerializer(ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


# Playlist model serializers
class GetFlatPlaylistSerializer(ModelSerializer):
    added_by = serializers.StringRelatedField()

    class Meta:
        model = Playlist
        fields = ["id", "name", "added_by"]


class GetDeepPlaylistSerializer(ModelSerializer):
    added_by = serializers.StringRelatedField()
    songs = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Playlist
        fields = ["id", "name", "added_by", "songs", "can_edit"]

    def get_can_edit(self, obj):
        return self.context["user"] == obj.added_by

    def get_songs(self, obj):
        data = [
            GetSongInPlaylistSerializer(
                song,
                context={"playlist": self.instance, "user": self.context["user"]},
            ).data
            for song in self.instance.songs.all()
        ]
        return sorted(
            data,
            key=lambda song: song["order_num"],
        )


class CreateUpdatePlaylistSerializer(Serializer):
    name = serializers.CharField(required=True, max_length=100)
    song_ids_ordered = serializers.PrimaryKeyRelatedField(
        required=True, read_only=False, queryset=Song.objects.all(), many=True
    )

    def validate(self, raw_data):
        if "playlist" in self.context:
            self.instance = self.context["playlist"]
        else:
            self.instance = None
        max_playlist_length = 50
        if "song_ids_ordered" in raw_data:
            if raw_data["song_ids_ordered"] is None:
                raw_data["song_ids_ordered"] = []
            if len(raw_data["song_ids_ordered"]) > max_playlist_length:
                raise ValidationError(
                    f"Too much entries passed! Maximum amount is {max_playlist_length}."
                )
            if len(set(raw_data["song_ids_ordered"])) != len(
                raw_data["song_ids_ordered"]
            ):
                raise ValidationError(
                    {"song_ids_ordered": "Ordering values are invalid!"}
                )
        return raw_data

    def save(self):
        if self.instance is not None:
            if "name" in self.validated_data:
                self.instance.name = self.validated_data["name"].strip()
                self.instance.save(update_fields=["name"])
        else:
            self.instance = Playlist.objects.create(
                added_by=self.context["user"],
                name=self.validated_data["name"].strip(),
            )
        if "song_ids_ordered" in self.validated_data:
            song_order_list = list(
                zip(
                    self.validated_data["song_ids_ordered"],
                    [_ for _ in range(len(self.validated_data["song_ids_ordered"]))],
                )
            )
            SongPlaylist.objects.filter(playlist=self.instance).delete()
            for entry in song_order_list:
                SongPlaylist.objects.create(
                    song=entry[0],
                    playlist=self.instance,
                    order_num=entry[1],
                )
        self.instance.refresh_from_db()
        return self.instance
