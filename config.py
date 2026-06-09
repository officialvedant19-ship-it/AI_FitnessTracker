import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "your-super-secret-key-change-this-in-production-2025"
    )

    # MySQL Configuration (Railway)

    MYSQL_HOST = os.environ.get("MYSQLHOST")
    MYSQL_PORT = os.environ.get("MYSQLPORT", "3306")
    MYSQL_USER = os.environ.get("MYSQLUSER")
    MYSQL_PASSWORD = os.environ.get("MYSQLPASSWORD")
    MYSQL_DB = os.environ.get("MYSQLDATABASE")

    # SQLAlchemy Database URI

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
        "?charset=utf8mb4"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    # Session

    SESSION_TYPE = "filesystem"
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    # Security

    BCRYPT_LOG_ROUNDS = 12
    JWT_EXPIRATION_HOURS = 24


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": ProductionConfig
}