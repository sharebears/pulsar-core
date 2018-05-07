DEBUG = True
PRESERVE_CONTEXT_ON_EXCEPTION = False
SQLALCHEMY_TRACK_MODIFICATIONS = False

SQLALCHEMY_DATABASE_URI = 'postgresql:///pulsar-testing'
SECRET_KEY = b'a very insecure secret key'

# Redis connection parameters
REDIS_PARAMS = {
    'host': 'localhost',
    'port': 6379,
    'password': None,
    'db': None,
    'key_prefix': None,
    }

SITE_PRIVATE = True
REQUIRE_INVITE_CODE = None
LOCKED_ACCOUNT_PERMISSIONS = [
    'view_staff_pm',
    'send_staff_pm',
    'resolve_staff_pm',
    ]
INVITE_LIFETIME = 60 * 60 * 24 * 3  # 3 days
