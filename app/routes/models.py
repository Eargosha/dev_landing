"""
Swagger модели данных для Flask-RESTX.
Используются для:
  - Валидации входных данных
  - Генерации документации
  - Примеров в Swagger UI
"""
from flask_restx import fields

# Импортируем api из __init__.py
from app.routes import api


# ===== МОДЕЛИ ЗАПРОСОВ =====

contact_request_model = api.model('ContactRequest', {
    'name': fields.String(
        required=True,
        description='Имя пользователя (2-100 символов)',
        example='Иван Петров'
    ),
    'email': fields.String(
        required=True,
        description='Email пользователя',
        example='ivan@example.com'
    ),
    'phone': fields.String(
        required=False,
        description='Телефон (опционально)',
        example='+7 999 123-45-67'
    ),
    'message': fields.String(
        required=True,
        description='Текст сообщения (10-2000 символов)',
        example='Здравствуйте! Хочу предложить вам вакансию Flutter-разработчика.'
    ),
})


# ===== МОДЕЛИ ОТВЕТОВ =====

ai_analysis_model = api.model('AIAnalysis', {
    'sentiment': fields.String(
        description='Тональность: positive/neutral/negative',
        example='positive'
    ),
    'category': fields.String(
        description='Категория: job_offer/collaboration/question/feedback/other',
        example='job_offer'
    ),
    'priority': fields.String(
        description='Приоритет: high/medium/low',
        example='high'
    ),
    'ai_used': fields.Boolean(
        description='Был ли использован AI (true) или fallback (false)',
        example=True
    ),
    'ai_fallback': fields.Boolean(
        description='Использовался ли fallback',
        example=False
    ),
})

email_status_model = api.model('EmailStatus', {
    'owner_sent': fields.Boolean(
        description='Письмо владельцу отправлено',
        example=True
    ),
    'user_sent': fields.Boolean(
        description='Письмо пользователю отправлено',
        example=True
    ),
})

contact_success_response = api.model('ContactSuccessResponse', {
    'success': fields.Boolean(description='Успех операции', example=True),
    'contact_id': fields.Integer(description='ID созданного обращения', example=42),
    'ai_analysis': fields.Nested(ai_analysis_model, description='Результат AI-анализа'),
    'email_status': fields.Nested(email_status_model, description='Статус отправки email'),
    'message': fields.String(
        description='Сообщение для пользователя',
        example='Обращение успешно отправлено! Мы свяжемся с вами в ближайшее время.'
    ),
})

error_response_model = api.model('ErrorResponse', {
    'error': fields.String(description='Тип ошибки', example='Validation Error'),
    'message': fields.String(description='Описание ошибки', example='Имя должно быть от 2 до 100 символов'),
})

health_response_model = api.model('HealthResponse', {
    'status': fields.String(description='Статус сервиса', example='healthy'),
    'service': fields.String(description='Название сервиса', example='portfolio-api'),
})

metrics_response_model = api.model('MetricsResponse', {
    'total_requests': fields.Integer(description='Всего запросов', example=150),
    'successful_requests': fields.Integer(description='Успешных запросов', example=140),
    'failed_requests': fields.Integer(description='Неуспешных запросов', example=10),
    'by_endpoint': fields.Raw(description='Статистика по эндпоинтам', example={'/api/contact': 50}),
    'by_status': fields.Raw(description='Статистика по статусам', example={'200': 100, '400': 10}),
    'last_updated': fields.String(description='Время последнего обновления', example='2026-06-21T12:00:00'),
})