"""
Default Django settings for config project.
These settings are always loaded and can be overridden by dev.py or prod.py
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-4)b1vxpv(=c$zwmw8f+&g(n!@3qg(azyrl!lm*e-!xt9)#=q##')

# Field encryption key for django-encrypted-model-fields
# IMPORTANT: In production, use a different key from SECRET_KEY and store it securely
FIELD_ENCRYPTION_KEY = os.environ.get('FIELD_ENCRYPTION_KEY', SECRET_KEY)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_celery_beat',  # For periodic tasks
    'account',  # Authentication and LDAP sync
    'sync_manager',  # Our new app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.LoginRequiredMiddleware',  # Force login for all views
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DB_NAME', 'network_manager'),
        'USER': os.environ.get('DB_USER', 'root'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Authentication settings
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Django auth (fallback)
]

LDAP_BACKEND = os.getenv('LDAP_BACKEND', 'account.backends.CustomLDAPBackend')
SYSTEM_SUPER_ADMIN_USERNAME = os.environ.get('SYSTEM_SUPER_ADMIN_USERNAME', 'admin')



# Try to enable LDAP if available
try:
    import ldap
    from django_auth_ldap.config import LDAPSearch, GroupOfNamesType
    
    # Add custom LDAP backend if package is installed
    AUTHENTICATION_BACKENDS+= [
        LDAP_BACKEND,
    ]
    # LDAP Configuration
    # LDAP Server URI
    AUTH_LDAP_SERVER_URI = os.environ.get('LDAP_SERVER_URI', 'ldap://localhost:389')

    # Bind credentials for searching
    AUTH_LDAP_BIND_DN = os.environ.get('LDAP_BIND_DN', '')
    AUTH_LDAP_BIND_PASSWORD = os.environ.get('LDAP_BIND_PASSWORD', '')
    LDAP_USER_SEARCH_BASE = os.environ.get('LDAP_USER_SEARCH_BASE', 'ou=users,dc=example,dc=top')
    LDAP_GROUP_SEARCH_BASE = os.environ.get('LDAP_GROUP_SEARCH_BASE', 'ou=groups,dc=example,dc=top')

    # User search settings
    # cn -> username (登录用户名)
    # sn -> first_name (姓名/昵称)
    # employeeNumber -> profile.employee_number (业务用户ID)
    # departmentNumber -> profile.department_number (部门ID)
    AUTH_LDAP_USER_SEARCH = LDAPSearch(
        os.environ.get('LDAP_USER_SEARCH_BASE', 'ou=ikuaier,dc=example,dc=top'),
        ldap.SCOPE_SUBTREE,
        "(cn=%(user)s)"
    )

    # LDAP 属性映射到 Django User
    AUTH_LDAP_USER_ATTR_MAP = {
        "username": "cn",            # 登录用户名
        "first_name": "sn",          # 姓名
        "email": "mail",             # 邮箱
    }
    
    # LDAP 属性映射到 UserProfile
    AUTH_LDAP_PROFILE_ATTR_MAP = {
        "employee_number": "employeeNumber",      # 业务用户ID
        "department_number": "departmentNumber",  # 部门ID
    }

    # Group settings
    # 组类型: groupOfNames (级联结构)
    # 组结构: cn=<group_id>,ou=groups,dc=example,dc=top
    #         cn=<sub_group_id>,cn=<parent_group_id>,ou=groups,dc=example,dc=top
    AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
        os.environ.get('LDAP_GROUP_SEARCH_BASE', 'ou=groups,dc=example,dc=top'),
        ldap.SCOPE_SUBTREE,
        "(objectClass=groupOfNames)"
    )

    # 使用 GroupOfNamesType 而不是 PosixGroupType
    AUTH_LDAP_GROUP_TYPE = GroupOfNamesType(name_attr="cn")

    # Mirror LDAP groups to Django groups
    AUTH_LDAP_MIRROR_GROUPS = True
    
    # 查找嵌套组 (支持级联结构)
    AUTH_LDAP_FIND_GROUP_PERMS = True

    # Set permissions based on LDAP groups
    # 可以根据特定的组 ID 设置权限
    AUTH_LDAP_USER_FLAGS_BY_GROUP = {
        "is_active": os.environ.get('LDAP_ACTIVE_GROUP', 'cn=active,ou=groups,dc=example,dc=top'),
        "is_staff": os.environ.get('LDAP_STAFF_GROUP', 'cn=staff,ou=groups,dc=example,dc=top'),
        "is_superuser": os.environ.get('LDAP_ADMIN_GROUP', 'cn=admin,ou=groups,dc=example,dc=top'),
    }

    # Always update user on login
    AUTH_LDAP_ALWAYS_UPDATE_USER = False

    # Cache LDAP groups for 1 hour
    AUTH_LDAP_CACHE_TIMEOUT = 3600
    
    # 启用详细日志以便调试
    import logging
    logger = logging.getLogger('django_auth_ldap')
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
    
    print("LDAP authentication enabled (inetOrgPerson + groupOfNames)")
except ImportError:
    print("LDAP packages not installed. Using Django authentication only.")
    print("To enable LDAP, install: uv sync --extra ldap")

# Login settings
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# URLs that don't require authentication
LOGIN_EXEMPT_URLS = [
    r'^/accounts/login$',
    r'^/admin/',
    r'^/static/',
]


# Redis Configuration
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = os.environ.get('REDIS_PORT', '6379')
REDIS_DB = os.environ.get('REDIS_DB', '0')
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')

REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}' if REDIS_PASSWORD else f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Cache configuration using Redis
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'db': REDIS_DB,
        }
    }
}

# Session configuration using Redis
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'


# Celery Configuration
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Celery Beat Schedule (for periodic tasks)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Celery Beat 定时任务配置
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # 每小时同步一次 LDAP 用户和组织架构
    'sync-ldap-users-hourly': {
        'task': 'account.tasks.sync_ldap_users_task',
        'schedule': crontab(minute=0),  # 每小时的第 0 分钟执行
        'options': {
            'expires': 3600,  # 任务过期时间 1 小时
        }
    },
    # 每10分钟同步一次 OpenVPN 账号状态
    'sync-openvpn-accounts': {
        'task': 'sync_manager.tasks.sync_openvpn_accounts',
        'schedule': crontab(minute='*/10'),  # 每10分钟执行
        'options': {
            'expires': 600,
        }
    },
    # 每天检查一次过期账号
    'check-expired-accounts': {
        'task': 'sync_manager.tasks.check_expired_accounts',
        'schedule': crontab(hour=0, minute=0),  # 每天0点执行
        'options': {
            'expires': 3600,
        }
    },
}


# iKuai API Configuration
IKUAI_CONFIG = {
    'base_url': os.environ.get('IKUAI_BASE_URL', 'http://192.168.1.1'),
    'username': os.environ.get('IKUAI_USERNAME', 'admin'),
    'password': os.environ.get('IKUAI_PASSWORD', 'admin'),
}

# OpenVPN Server Configuration
OPENVPN_CONFIG = {
    'server_host': os.environ.get('OPENVPN_SERVER_HOST', 'vpn.example.com'),
    'server_port': os.environ.get('OPENVPN_SERVER_PORT', '1194'),
    'protocol': os.environ.get('OPENVPN_PROTOCOL', 'udp'),  # udp or tcp
    'ca_cert': os.environ.get('OPENVPN_CA_CERT', '请联系管理员获取CA证书'),  # CA 证书内容
}
