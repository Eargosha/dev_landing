"""
Конфигурация приложения.
"""
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


class Config:
    """Базовая конфигурация приложения."""
    
    @staticmethod
    def _to_bool(value, default=False):
        """Преобразует строку 'true'/'false' в boolean."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes')
        return default
    
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Database (SQLite)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///portfolio.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mail (SMTP)
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.yandex.ru")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 465))
    MAIL_USE_SSL = _to_bool(os.getenv("MAIL_USE_SSL", "False"))
    MAIL_USE_TLS = _to_bool(os.getenv("MAIL_USE_TLS", "True"))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_USERNAME")
    MAIL_OWNER_EMAIL = os.getenv("MAIL_OWNER_EMAIL", "eargosha@mail.ru")
    
    # AI (Ollama — локальный, бесплатный, работает без интернета)
    AI_ENABLED = os.getenv("AI_ENABLED", "True").lower() == "true"
    AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", 60))
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/generate")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

    # Rate Limiting
    RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", 5))
    RATE_LIMIT_WINDOW_MINUTES = int(os.getenv("RATE_LIMIT_WINDOW_MINUTES", 60))
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = os.getenv("LOG_FILE", "logs/app.log")
    
    # Data Directory
    DATA_DIR = os.getenv("DATA_DIR", "data")


class DevelopmentConfig(Config):
    """Конфигурация для разработки."""
    DEBUG = True


class ProductionConfig(Config):
    """Конфигурация для продакшена."""
    DEBUG = False


class TestingConfig(Config):
    """Конфигурация для тестирования."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///test.db"


# Словарь для выбора конфигурации по имени окружения
config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config():
    """Получить конфигурацию на основе переменной окружения FLASK_ENV."""
    env = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(env, config_by_name["default"])