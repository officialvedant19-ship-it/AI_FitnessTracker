import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""

    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "your-super-secret-key-change-this-in-production-2025"
    )

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("MYSQL_URL")
        .replace("mysql://", "mysql+pymysql://", 1)
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