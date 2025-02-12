# boot_django.py
#
# This file sets up and configures Django. It's used by scripts that need to
# execute as if running in a Django server.

import os
import django
from django.conf import settings

APP_NAME = 'tom_tns'  # the stand-alone app we are testing

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), APP_NAME))


def boot_django():
    settings.configure(
        BASE_DIR=BASE_DIR,
        # SECURITY WARNING: keep the secret key used in production secret!
        SECRET_KEY='v5j-rg7sc+leg-m+vf947vi34+fs1%+$m%*l%sb7^fnwb$-29y',
        DEBUG=True,
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
            }
        },
        INSTALLED_APPS=(
            'django.contrib.admin',
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.messages',
            'django.contrib.staticfiles',
            'django.contrib.sites',
            'django_extensions',
            'guardian',
            'tom_common',
            'django_comments',
            'bootstrap4',
            'crispy_forms',
            'rest_framework',
            'rest_framework.authtoken',
            'django_filters',
            'django_gravatar',
            'tom_targets',
            'tom_alerts',
            'tom_catalogs',
            'tom_observations',
            'tom_dataproducts',
            APP_NAME,  # defined above
        ),
        EXTRA_FIELDS={},
        TIME_ZONE='UTC',
        USE_TZ=True,
        HOOKS={
            'target_post_save': 'tom_common.hooks.target_post_save',
            'observation_change_state': 'tom_common.hooks.observation_change_state',
            'data_product_post_upload': 'tom_dataproducts.hooks.data_product_post_upload'
        },
        MIDDLEWARE=[
            'django.middleware.security.SecurityMiddleware',
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.common.CommonMiddleware',
            'django.middleware.csrf.CsrfViewMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
            'django.contrib.messages.middleware.MessageMiddleware',
            'django.middleware.clickjacking.XFrameOptionsMiddleware',
            'tom_common.middleware.Raise403Middleware',
            'tom_common.middleware.ExternalServiceMiddleware',
            'tom_common.middleware.AuthStrategyMiddleware',
        ],
        TEMPLATES=[
            {
                'BACKEND': 'django.template.backends.django.DjangoTemplates',
                'DIRS': [os.path.join(BASE_DIR, 'templates')],
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
        ],
        AUTHENTICATION_BACKENDS=(
            'django.contrib.auth.backends.ModelBackend',
            'guardian.backends.ObjectPermissionBackend',
        ),
        AUTH_STRATEGY='READ_ONLY',
        STATIC_URL='/static/',
        STATIC_ROOT=os.path.join(BASE_DIR, '_static'),
        STATICFILES_DIRS=[os.path.join(BASE_DIR, 'static')],
        MEDIA_ROOT=os.path.join(BASE_DIR, 'data'),
        MEDIA_URL='/data/',
        # ROOT_URLCONF='tom_tns.tests.urls.test_urls',
        TOM_REGISTRATION={
            'REGISTRATION_AUTHENTICATION_BACKEND': 'django.contrib.auth.backends.ModelBackend',
            'REGISTRATION_REDIRECT_PATTERN': 'home',
            'SEND_APPROVAL_EMAILS': True,
            'REGISTRATION_STRATEGY': 'open'  # ['open', 'approval_required']
        },
        DATA_PRODUCT_TYPES={
            'photometry': ('photometry', 'Photometry'),
            'fits_file': ('fits_file', 'FITS File'),
            'spectroscopy': ('spectroscopy', 'Spectroscopy'),
            'image_file': ('image_file', 'Image File')
        },
        FACILITIES={
            'LCO': {
                'portal_url': 'https://observe.lco.global',
                'api_key': '',
            },
            'GEM': {
                'portal_url': {
                    'GS': 'https://139.229.34.15:8443',
                    'GN': 'https://128.171.88.221:8443',
                },
                'api_key': {
                    'GS': '',
                    'GN': '',
                },
                'user_email': '',
                'programs': {
                    'GS-YYYYS-T-NNN': {
                        'MM': 'Std: Some descriptive text',
                        'NN': 'Rap: Some descriptive text'
                    },
                    'GN-YYYYS-T-NNN': {
                        'QQ': 'Std: Some descriptive text',
                        'PP': 'Rap: Some descriptive text',
                    },
                },
            },
        },
        TOM_FACILITY_CLASSES=[
            'tom_observations.facilities.lco.LCOFacility',
            'tom_observations.facilities.gemini.GEMFacility',
            'tom_observations.facilities.soar.SOARFacility',
            'tom_observations.facilities.lt.LTFacility'
        ]
    )
    django.setup()
