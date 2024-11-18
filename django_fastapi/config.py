import os
from dotenv import load_dotenv

load_dotenv()


# DATABASE
DB_USER = os.environ.get('DB_USER')
DB_PASS = os.environ.get('POSTGRES_PASSWORD')
DB_HOST = os.environ.get('POSTGRES_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_NAME = os.environ.get('DB_NAME')

# DJANGO SECURE
CSRF_TOKEN = os.environ.get('CSRF_TOKEN')

# SELENIUM
SELENIUM_DRIVER = os.environ.get('SELENIUM_DRIVER')

#PGBOUNCER
PGBOUNCER_HOST = os.environ.get('PGBOUNCER_HOST')

# REDIS
REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
REDIS_PORT = os.environ.get('REDIS_PORT')
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/0"

# JWT SECURE
JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM')