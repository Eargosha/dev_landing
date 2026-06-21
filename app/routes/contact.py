"""
Маршрут для контактной формы.
POST /api/contact
"""
import logging
from flask import request
from flask_restx import Resource, Namespace
from app.routes import api
from app.routes.models import (
    contact_request_model,
    contact_success_response,
    error_response_model,
)
from app.services import ContactService

logger = logging.getLogger(__name__)

# Создаём namespace для группировки
ns = Namespace('contact', description='Контактная форма')


@ns.route('/contact')
class ContactResource(Resource):
    """Ресурс для обработки контактных обращений."""
    
    @ns.expect(contact_request_model)
    @ns.response(201, 'Обращение успешно создано', contact_success_response)
    @ns.response(400, 'Ошибка валидации', error_response_model)
    @ns.response(429, 'Превышен лимит запросов', error_response_model)
    @ns.response(500, 'Внутренняя ошибка сервера', error_response_model)
    @ns.doc(
        summary='Отправить контактное обращение',
        description='''
Принимает контактное обращение и обрабатывает его через полный цикл:

1. **Валидация** — проверка имени, email, телефона, сообщения
2. **Rate limiting** — защита от спама (5 запросов в час на IP)
3. **AI анализ** — определение тональности, категории, приоритета + генерация ответа
4. **Сохранение в БД** — запись в PostgreSQL/SQLite
5. **Email** — уведомление владельцу + автоответ пользователю
6. **Метрики** — запись статистики

AI работает на локальной модели Qwen2.5:3b (Ollama). При недоступности — fallback.
        '''
    )
    def post(self):
        """Отправить контактное обращение."""
        try:
            # Получаем данные запроса
            request_data = request.get_json()
            
            if not request_data:
                return {
                    'error': 'Bad Request',
                    'message': 'Тело запроса должно быть в формате JSON'
                }, 400
            
            # Получаем метаданные
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')
            
            # Обрабатываем обращение через сервис
            result = ContactService.process_contact(
                request_data=request_data,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return result, 201
            
        except ValueError as e:
            # Ошибка валидации
            logger.warning("Ошибка валидации: %s", str(e))
            return {
                'error': 'Validation Error',
                'message': str(e)
            }, 400
            
        except RuntimeError as e:
            # Rate limit превышен
            logger.warning("Rate limit: %s", str(e))
            return {
                'error': 'Too Many Requests',
                'message': str(e)
            }, 429
            
        except Exception as e:
            # Внутренняя ошибка
            logger.error("Внутренняя ошибка: %s", str(e), exc_info=True)
            return {
                'error': 'Internal Server Error',
                'message': 'Произошла внутренняя ошибка сервера. Попробуйте позже.'
            }, 500


# Регистрируем namespace в api
api.add_namespace(ns, path='/')