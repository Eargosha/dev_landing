"""
Repository для работы со статистикой (файловое хранилище).

Храним метрики запросов в JSON файле.
Это проще чем БД для счётчиков и не требует миграций.
"""
import json
import os
import logging
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)


class MetricsRepository:
    """Repository для метрик (файловое хранилище)."""
    
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self._file_path = os.path.join(data_dir, "metrics.json")
        self._lock = Lock()
        
        os.makedirs(data_dir, exist_ok=True)
    
    def _load_data(self):
        """Загружаем метрики из файла."""
        if not os.path.exists(self._file_path):
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "by_endpoint": {},
                "by_status": {},
                "last_updated": None,
            }
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Не удалось загрузить метрики: %s", e)
            return {}
    
    def _save_data(self, data):
        """Сохраняем метрики в файл."""
        try:
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error("Не удалось сохранить метрики: %s", e)
    
    def record_request(self, endpoint, status_code, success=True):
        """
        Записываем запрос в метрики.
        
        Args:
            endpoint: Путь эндпоинта (например, "/api/contact")
            status_code: HTTP статус код
            success: Успешен ли запрос
        """
        with self._lock:
            data = self._load_data()
            
            data["total_requests"] = data.get("total_requests", 0) + 1
            
            if success:
                data["successful_requests"] = data.get("successful_requests", 0) + 1
            else:
                data["failed_requests"] = data.get("failed_requests", 0) + 1
            
            # По эндпоинтам
            if "by_endpoint" not in data:
                data["by_endpoint"] = {}
            data["by_endpoint"][endpoint] = data["by_endpoint"].get(endpoint, 0) + 1
            
            # По статусам
            if "by_status" not in data:
                data["by_status"] = {}
            status_str = str(status_code)
            data["by_status"][status_str] = data["by_status"].get(status_str, 0) + 1
            
            data["last_updated"] = datetime.utcnow().isoformat()
            
            self._save_data(data)
    
    def get_metrics(self):
        """Получить все метрики."""
        with self._lock:
            return self._load_data()


# Глобальный экземпляр
metrics_repo = None


def init_metrics_repository(data_dir="data"):
    """Инициализация metrics repository."""
    global metrics_repo
    metrics_repo = MetricsRepository(data_dir)
    logger.info("Metrics repository инициализирован")