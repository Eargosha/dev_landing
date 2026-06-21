"""
Маршрут для получения метрик.
GET /api/metrics
"""
from flask_restx import Resource, Namespace
from app.routes import api
from app.routes.models import metrics_response_model
import app.repositories.metrics_repository as metrics_repository

ns = Namespace('metrics', description='Статистика обращений')


@ns.route('/metrics')
class MetricsResource(Resource):
    """Ресурс для получения метрик."""
    
    @ns.marshal_with(metrics_response_model)
    @ns.doc(
        summary='Получить статистику',
        description='Возвращает статистику по запросам: общее количество, по эндпоинтам, по статусам.'
    )
    def get(self):
        """Получить метрики."""
        if not metrics_repository.metrics_repo:
            return {'error': 'Metrics repository not initialized'}, 500
        
        return metrics_repository.metrics_repo.get_metrics(), 200


api.add_namespace(ns, path='/')