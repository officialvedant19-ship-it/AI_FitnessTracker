import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")

    # 1. Prefer the public URL (Railway standard)
    db_url = os.getenv("DATABASE_PUBLIC_URL") or os.getenv("MYSQL_URL")

    if db_url and db_url.startswith("mysql://"):
        db_url = db_url.replace("mysql://", "mysql+pymysql://", 1)

    # 2. Fallback: build from individual variables (for local development)
    if not db_url:
        MYSQL_HOST = os.getenv("MYSQLHOST", "localhost")
        MYSQL_USER = os.getenv("MYSQLUSER", "root")
        MYSQL_PASSWORD = os.getenv("MYSQLPASSWORD", "")
        MYSQL_DB = os.getenv("MYSQLDATABASE", "railway")
        MYSQL_PORT = os.getenv("MYSQLPORT", "3306")
        db_url = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"

    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }

    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    BCRYPT_LOG_ROUNDS = 12
    JWT_EXPIRATION_HOURS = 24

class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}