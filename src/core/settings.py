import sys
from pathlib import Path

import dj_database_url

from core.env import env_settings

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / 'apps'))

SECRET_KEY = env_settings.SECRET_KEY
DEBUG = env_settings.DEBUG

ALLOWED_HOSTS = env_settings.ALLOWED_HOSTS
CSRF_TRUSTED_ORIGINS = env_settings.CSRF_TRUSTED_ORIGINS


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party apps
    'django_cotton',
    'widget_tweaks',
    'whitenoise',
    # Local apps
    'accounts',
    'events',
    'reviews',
    'papers',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.LoginRequiredMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'static'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.parse(
        env_settings.DATABASE_URL,
        conn_max_age=600,
        conn_health_checks=True,
    ),
}


# Authentication

AUTH_USER_MODEL = 'accounts.User'
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
]

LOGIN_URL = 'signin'


# Email

EMAIL_HOST = env_settings.EMAIL_HOST
EMAIL_PORT = env_settings.EMAIL_PORT
EMAIL_HOST_USER = env_settings.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = env_settings.EMAIL_HOST_PASSWORD
EMAIL_USE_TLS = env_settings.EMAIL_USE_TLS
EMAIL_USE_SSL = env_settings.EMAIL_USE_SSL
DEFAULT_FROM_EMAIL = env_settings.DEFAULT_FROM_EMAIL


# Internationalization

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

# Django Cotton

COTTON_DIR = 'components'


# Django Debug Toolbar

if DEBUG and 'test' not in sys.argv:
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.insert(
        MIDDLEWARE.index('django.middleware.common.CommonMiddleware') + 1,
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

    def show_toolbar(request):
        return True

    DEBUG_TOOLBAR_CONFIG = {
        'SHOW_TOOLBAR_CALLBACK': 'core.settings.show_toolbar',
        'ROOT_TAG_EXTRA_ATTRS': 'hx-preserve',
        'UPDATE_ON_FETCH': True,
    }
