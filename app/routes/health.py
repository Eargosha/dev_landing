"""
Маршрут для проверки здоровья сервиса.
GET /api/health
"""
from flask_restx import Resource, Namespace
from app.routes import api
from app.routes.models import health_response_model

ns = Namespace('health', description='Проверка здоровья сервиса')


@ns.route('/health')
class HealthResource(Resource):
    """Ресурс для health check."""
    
    @ns.marshal_with(health_response_model)
    @ns.doc(
        summary='Проверка работоспособности',
        description='Возвращает статус сервиса. Используется для мониторинга.'
    )
    def get(self):
        """Проверить работоспособность сервиса."""
        return {
            'status': 'healthy',
            'service': 'portfolio-api'
        }, 200


api.add_namespace(ns, path='/')