import os
import random
import string
from datetime import timedelta
from io import BytesIO

import magic
from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage as storage
from PIL import Image
from rest_framework.serializers import ValidationError
from rest_framework.views import exception_handler

# Session key storages


class ResetCodeManager:
    __ttl = timedelta(minutes=2)

    @classmethod
    def get_or_create_code(cls, email: str) -> str:
        key = email + "__code"
        code = cache.get(key, None)
        if code is not None:
            return code
        code = "".join(random.choices(string.digits, k=4))
        cache.add(key, code, timeout=cls.__ttl.seconds)
        return cache.get(key)

    @classmethod
    def try_use_code(cls, email: str, code: str) -> bool:
        key = email + "__code"
        if cache.get(key) != code:
            return False
        cache.delete(key)
        return True


class SessionTokenManager:
    __ttl = timedelta(minutes=10)

    @classmethod
    def get_or_create_token(cls, email: str) -> str:
        key = email + "__token"
        token = cache.get(key, None)
        if token is not None:
            return token
        token = "".join(random.choices(string.digits + string.ascii_letters, k=32))
        cache.add(key, token, timeout=cls.__ttl.seconds)
        return cache.get(key)

    @classmethod
    def try_use_token(cls, email: str, token: str) -> bool:
        key = email + "__token"
        if cache.get(key) != token:
            return False
        cache.delete(key)
        return True


# Custom Django Exception handler


def custom_exception_handler(exc, context):
    newdata = dict()
    newdata["errors"] = []

    def get_list_from_errors(data):
        to_return = []
        if not isinstance(data, (list, dict)):
            to_return.append(data)
        elif isinstance(data, list):
            for err in data:
                to_return.extend(get_list_from_errors(err))
        elif isinstance(data, dict):
            for err in data.values():
                to_return.extend(get_list_from_errors(err))
        return to_return

    response = exception_handler(exc, context)
    if response is not None:
        newdata["errors"].extend(get_list_from_errors(response.data))
        newdata["old_repr"] = response.data
        response.data = newdata
    return response


# File uploading callbacks


def upload_avatar_to(instance, filename):
    """Instance is of type User."""
    return (
        f"{settings.UPLOAD_ROOT}/{instance.email.replace('@', 'AT')}"
        + f"/avatar{os.path.splitext(filename)[1]}"
    )


def upload_coverimg_to(instance, filename):
    """Instance is of type Song."""
    return (
        f"{settings.UPLOAD_ROOT}/songs/{instance.id}"
        + f"/coverimg{os.path.splitext(filename)[1]}"
    )


def upload_thumbnail_to(instance, filename):
    """Instance is of type Song."""
    return (
        f"{settings.UPLOAD_ROOT}/songs/{instance.id}"
        + f"/thumbnail_{os.path.splitext(filename)[1]}"
    )


def upload_audio_to(instance, filename):
    """Instance is of type Song."""
    return (
        f"{settings.UPLOAD_ROOT}/songs/{instance.id}"
        + f"/audio{os.path.splitext(filename)[1]}"
    )


# MIME type FileField validators


def validate_is_music(file):
    valid_mime_types = [
        "audio/aac",
        "audio/midi",
        "audio/x-midi",
        "audio/mpeg",
        "audio/ogg",
        "audio/opus",
        "audio/wav",
        "audio/webm",
    ]
    file_mime_type = magic.from_buffer(file.read(1024), mime=True)
    if file_mime_type not in valid_mime_types:
        raise ValidationError("Unsupported file type.")
    valid_file_extensions = [
        ".aac",
        ".mid",
        ".midi",
        ".mp3",
        ".oga",
        ".opus",
        ".wav",
        ".weba",
    ]
    ext = os.path.splitext(file.name)[1]
    if ext.lower() not in valid_file_extensions:
        raise ValidationError("Unacceptable file extension.")


def validate_file_size(file):
    limit = 10 * 1024 * 1024
    if file.size > limit:
        raise ValidationError("File is too large. Size should not exceed 10 MB.")


# Thumbnail helper function


def make_thumbnail(song):
    with storage.open(song.cover_img.name, "r") as image_read:
        image = Image.open(image_read)
        if image.height > 150 or image.width > 150:
            size = (150, 150)
            imageBuffer = BytesIO()
            image.thumbnail(size)
            # Save the image as jpeg, png, etc. to the buffer
            image.save(imageBuffer, image.format)
            # Save the modified image
            song.thumbnail.save(
                song.cover_img.name, ContentFile(imageBuffer.getvalue())
            )
