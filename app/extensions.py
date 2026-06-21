"""
Flask-расширения приложения.

Выносим создание расширений в отдельный файл,
чтобы избежать циклических импортов и упростить тестирование.

"""

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_cors import CORS

# Создаём экземпляры расширений
db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
cors = CORS()