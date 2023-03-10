"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 4.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

import os
from datetime import timedelta
from pathlib import Path

from decouple import Config, RepositoryEnv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ.get("DEBUG") not in ("false", "False", "0", "f", "F"))
if DEBUG is None:
    DEBUG = True

if DEBUG:
    env_config = Config(RepositoryEnv(BASE_DIR.parent / ".env_dev"))
else:
    env_config = Config(RepositoryEnv(BASE_DIR.parent / ".env_prod"))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env_config.get("SECRET_KEY")
ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "cloudinary_storage",
    "django.contrib.staticfiles",
    "cloudinary",
    # our app
    "music_player_api.apps.MusicPlayerApiConfig",
    # 3d party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework.authtoken",
    "storages",
]

AUTH_USER_MODEL = "music_player_api.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{env_config.get('REDIS_HOST')}:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# REST Framework

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "djangorestframework_camel_case.render.CamelCaseJSONRenderer",
        "djangorestframework_camel_case.render.CamelCaseBrowsableAPIRenderer",
        # Any other renders
    ),
    "DEFAULT_PARSER_CLASSES": (
        # If you use MultiPartFormParser or FormParser, we also have a camel case version
        "djangorestframework_camel_case.parser.CamelCaseFormParser",
        "djangorestframework_camel_case.parser.CamelCaseMultiPartParser",
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
        # Any other parsers
    ),
    "EXCEPTION_HANDLER": "music_player_api.utils.custom_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=3653),
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "JWK_URL": None,
    "AUTH_HEADER_TYPES": ("Bearer", "JWT"),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",
    "JTI_CLAIM": "jti",
}


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env_config.get("POSTGRES_NAME"),
        "USER": env_config.get("POSTGRES_USER"),
        "PASSWORD": env_config.get("POSTGRES_PASSWORD"),
        "HOST": env_config.get("HOST"),
        "PORT": env_config.get("PORT"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "static"


# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Sendgrid integration
SENDGRID_API_KEY = env_config.get("SENDGRID_API_KEY")
SENDGRID_SENDER_EMAIL = env_config.get("SENDGRID_SENDER_EMAIL")


# Media files upload
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": env_config.get("CLOUDINARY_CLOUD_NAME"),
    "API_KEY": env_config.get("CLOUDINARY_API_KEY"),
    "API_SECRET": env_config.get("CLOUDINARY_API_SECRET"),
}
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.RawMediaCloudinaryStorage"
MEDIA_URL = "/music_player_api/media/"
MEDIA_ROOT = BASE_DIR / "media"
UPLOAD_ROOT = env_config.get("UPLOAD_ROOT")

# DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"
# STATICFILES_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# LINODE_BUCKET_NAME = env_config.get("LINODE_BUCKET_NAME")
# LINODE_BUCKET_REGION = env_config.get("LINODE_BUCKET_REGION")
# LINODE_BUCKET_ACCESS_KEY = env_config.get("LINODE_BUCKET_ACCESS_KEY")
# LINODE_BUCKET_SECRET_KEY = env_config.get("LINODE_BUCKET_SECRET_KEY")


# AWS_S3_ACCESS_KEY_ID = LINODE_BUCKET_ACCESS_KEY
# AWS_S3_SECRET_ACCESS_KEY = LINODE_BUCKET_SECRET_KEY
# AWS_STORAGE_BUCKET_NAME = LINODE_BUCKET_NAME
# AWS_S3_REGION_NAME = LINODE_BUCKET_REGION
# # AWS_QUERYSTRING_AUTH = False
# AWS_S3_FILE_OVERWRITE = True
# AWS_S3_USE_SSL = True
# AWS_DEFAULT_ACL = "public-read-write"
# AWS_S3_ENDPOINT_URL = f"https://{LINODE_BUCKET_REGION}.linodeobjects.com"
