"""
Модуль маршрутов API.
Создаём Flask Blueprint с Flask-RESTX для автоматической Swagger документации.

Swagger UI будет доступен на /api/docs
"""
from flask import Blueprint
from flask_restx import Api

# Blueprint для всех API маршрутов
api_bp = Blueprint('api', __name__, url_prefix='')

# Создаём Api объект с настройками Swagger
api = Api(
    api_bp,
    version='1.0',
    title='Portfolio API',
    description='''
## Backend-сервис для лендинг-презентации разработчика

API предоставляет следующие возможности:
- Приём контактных обращений с AI-анализом
- Анализ тональности и классификация обращений
- Автоматическая генерация ответов через Ollama (Qwen2.5)
- Отправка email-уведомлений
- Rate limiting для защиты от спама

### AI-интеграция
Используется локальная модель **Qwen2.5:3b** через **Ollama**.
При недоступности AI — graceful fallback на rule-based анализ.
    ''',
    doc='/api/docs',  # Swagger UI на /api/docs
    prefix='/api',
    authorizations={
        'Bearer Auth': {
            'type': 'apiKey',
            'in': 'header',
            'name': 'Authorization'
        }
    },
    security='Bearer Auth'
)

# Импортируем namespaces (маршруты)
from app.routes import contact, health, metrics