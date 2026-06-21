"""
Прогрев AI-модели при старте приложения.

Первый запрос к Ollama всегда медленный (4+ секунды)
из-за загрузки модели в RAM. Чтобы пользователи не ждали,
прогреваем модель при старте приложения.
"""
import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)


def warmup_ai_model():
    """
    Отправляем тестовый запрос в Ollama при старте.
    
    Это загружает модель в RAM, и последующие запросы
    будут быстрыми (~2-3 секунды вместо ~7).
    """
    try:
        base_url = current_app.config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = current_app.config.get("OLLAMA_MODEL", "qwen2.5:3b")
        ai_enabled = current_app.config.get("AI_ENABLED", True)
        
        if not ai_enabled:
            logger.info("AI отключён, прогрев пропущен")
            return
        
        # Убираем /v1 из URL
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        if base_url.endswith("/v1/"):
            base_url = base_url[:-4]
        
        url = f"{base_url}/api/chat"
        
        logger.info("Прогреваем модель %s...", model)
        
        # Минимальный запрос для загрузки модели в RAM
        response = requests.post(
            url,
            json={
                "model": model,
                "messages": [
                    {"role": "user", "content": "Hi"}
                ],
                "stream": False,
                "options": {
                    "num_predict": 5,  # Минимум токенов
                }
            },
            timeout=120  # Первый запрос может быть долгим
        )
        
        response.raise_for_status()
        data = response.json()
        total_duration = data.get("total_duration", 0) / 1_000_000_000
        
        logger.info(
            "Модель %s прогрета за %.2f сек",
            model, total_duration
        )
        
    except requests.exceptions.ConnectionError:
        logger.warning(
            "Ollama недоступен по адресу %s. "
            "AI будет использовать fallback. "
            "Запусти 'ollama serve' для включения AI.",
            base_url
        )
    except Exception as e:
        logger.warning("Не удалось прогреть модель: %s. Будет использоваться fallback.", str(e))