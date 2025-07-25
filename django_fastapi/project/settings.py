import os

import sentry_sdk

from config import (DB_USER,
                    DB_PASS,
                    DB_HOST,
                    DB_NAME,
                    DB_PORT,
                    CSRF_TOKEN,
                    REDIS_URL,
                    PGBOUNCER_HOST)


sentry_sdk.init(
    dsn="https://092663a7578a856b241d61d8c326be00@o4506694926336000.ingest.sentry.io/4506739040190464",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

####SWITCH FOR DEV/PROD#########
# PROD
DEBUG = False
STATIC_URL = "/static/"

# DEV
# DEBUG = True
# STATIC_URL = "/django/static/"


#################################



BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'django_error.log'),
            'formatter': 'verbose',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}


SECRET_KEY = CSRF_TOKEN

LANGUAGE_CODE = 'ru'

TIME_ZONE = 'Europe/Moscow'

USE_TZ = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    'debug_toolbar',
    "django_celery_beat",
    'django_summernote',
    'django_admin_action_forms',
    'rangefilter',

    "general_models",
    "no_cash",
    "cash",
    "partners",
    'seo_admin'
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

INTERNAL_IPS = [
     "127.0.0.1",
]

ROOT_URLCONF = "project.urls"

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
            ]
        },
    }
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        # "NAME": "test_db2",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASS,
        "HOST": PGBOUNCER_HOST,
        # "HOST": DB_HOST,
        "PORT": DB_PORT,
        "CONN_MAX_AGE": 60,
    }
}


CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# CACHES = {
#     "default": {
#         "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
#         "LOCATION": "./cache_holder",
#     }
# }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")


STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

PROJECT_NAME = "django-fastapi-project"

FASTAPI_PREFIX = "/api"
DJANGO_PREFIX = "/django"

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000


SITE_DOMAIN = 'api.moneyswap.online'
# SITE_DOMAIN = '127.0.0.1:81'

# ALLOWED_HOSTS = [SITE_DOMAIN]
ALLOWED_HOSTS = ['*']

PROTOCOL = 'https://'

CSRF_TRUSTED_ORIGINS = [f'{PROTOCOL}{SITE_DOMAIN}']

#RabbitMQ  PROD
# CELERY_BROKER_URL = 'amqp://guest:guest@rabbitmq3:5672/'

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL


X_FRAME_OPTIONS = 'SAMEORIGIN'

SUMMERNOTE_THEME = 'bs4'

SUMMERNOTE_CONFIG = {
    'toolbar': [
        ['style', ['bold', 'italic', 'underline', 'clear']],
        ['font', ['strikethrough']],
        ['insert', ['link']],
    ]
}


# SUMMERNOTE_CONFIG = {
#     'summernote': {
#         'toolbar': [
#             ['style', ['bold', 'italic', 'underline']],
#             ['para', ['paragraph']],
#             ['insert', ['link']],
#             ['view', ['codeview']],
#         ],
#         'styleTags': [],
#     },
#     'css': (),  # Убрать лишние стили
# }