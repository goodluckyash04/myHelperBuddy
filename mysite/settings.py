import os
from pathlib import Path
from decouple import config


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Create logs directory if not exists
log_dir = BASE_DIR / "logs"
log_dir.mkdir(exist_ok=True)

# Security settings
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default="True", cast=lambda v: v.lower() in ("true", "1", "yes"))
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*").split(",") if not DEBUG else ["*"]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.SimpleRateLimitMiddleware',  # Rate limiting for sensitive endpoints
]

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

ROOT_URLCONF = 'mysite.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mysite.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR /  config('DB_NAME'),
    }
}

# JSON database
JSON_DB = BASE_DIR /config("JSON_DB")

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Localization settings
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST  = 'smtp.gmail.com'
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

ENCRYPTION_KEY = config('ENCRYPTION_KEY')
SALT = config('SALT')

# Admin and user access controls
ADMIN = config('ADMIN')
ADMIN_EMAIL = config('ADMIN_EMAIL')
ADMIN_ACCESS = bool(config('ADMIN_ACCESS'))
REMINDER_USER_ACCESS = config('REMINDER_USER_ACCESS')
FINANCE_USER_ACCESS = config('FINANCE_USER_ACCESS')
TASK_USER_ACCESS = config('TASK_USER_ACCESS')
TRANSACTION_USER_ACCESS = config('TRANSACTION_USER_ACCESS')
LEDGER_USER_ACCESS = config('LEDGER_USER_ACCESS')
OTHER_UTILITIES_USER_ACCESS = config('OTHER_UTILITIES_USER_ACCESS')
MUSIC_USER_ACCESS = config('MUSIC_USER_ACCESS')
DOCUMENT_MANAGER_USER_ACCESS = config('DOCUMENT_MANAGER_USER_ACCESS')

# Site configuration
SITE_URL = config('SITE_URL')
EMAIL_SERVICE = config('EMAIL_SERVICE')
STREAMLIT_URL = config('STREAMLIT_URL')

# Google Drive API settings
CLIENT_ID = config("CLIENT_ID")
CLIENT_SECRET = config("CLIENT_SECRET")
REDIRECT_URI = config("REDIRECT_URI")
REFRESH_TOKEN = config("REFRESH_TOKEN")
TOKEN_URI = config("TOKEN_URI")
BACKUP_FOLDER_ID = config("BACKUP_FOLDER_ID")

# Document Manager settings
MAX_TOTAL_BYTES_PER_USER = config("MAX_TOTAL_BYTES_PER_USER")
TOTAL_DB_FILE_SIZE = config("TOTAL_DB_FILE_SIZE")

# Security middleware settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = not DEBUG and config("FORCE_HTTPS", default="False", cast=lambda v: v.lower() in ("true", "1", "yes"))
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG