"""
Сервис AI-интеграции с graceful fallback.

Зачем: Автоматический анализ обращений пользователей.
Что делает:
  1. Определяет тональность комментария (positive/neutral/negative)
  2. Классифицирует тип запроса (job_offer/collaboration/question/feedback/other)
  3. Определяет приоритет (high/medium/low)
  4. Генерирует автоматический ответ на обращение

AI-провайдер: Ollama (локальный, бесплатный, без интернета).
Используем модель Qwen2.5:3b через OpenAI-совместимый API.

Graceful fallback: Если Ollama недоступен (сервис не запущен, модель не скачана,
ошибка ответа), используем rule-based анализ на основе ключевых слов.
Сервис ВСЕГДА возвращает результат и не упадёт при отсутствии Ollama.
"""
import json
import logging
import re
from flask import current_app

logger = logging.getLogger(__name__)


class AIService:
    """
    Сервис для AI-анализа обращений.
    
    Все методы статические — не нужно создавать экземпляр, проще использовать.
    """
    
    # ===== СЛОВАРИ ДЛЯ FALLBACK-АНАЛИЗА =====
    
    POSITIVE_WORDS = {
        # Русские
        "спасибо", "благодарю", "отлично", "замечательно", "превосходно",
        "хорошо", "класс", "супер", "нравится", "молодец", "круто",
        "потрясающе", "великолепно", "прекрасно", "идеально",
        # Английские
        "great", "thanks", "awesome", "excellent", "good", "nice", 
        "love", "amazing", "wonderful", "fantastic", "perfect"
    }
    
    NEGATIVE_WORDS = {
        # Русские
        "плохо", "ужасно", "отвратительно", "косяк", "ошибка", "баг",
        "проблема", "не работает", "сломалось", "разочарован",
        "бесит", "раздражает", "неудобно", "глючит",
        # Английские
        "bad", "terrible", "awful", "horrible", "hate", "bug", 
        "error", "broken", "disappointed", "frustrating"
    }
    
    CATEGORY_KEYWORDS = {
        "job_offer": [
            "вакансия", "работа", "работу", "зарплата", "офер", "оффер",
            "нужен разработчик", "ищем", "трудоустройство", "позиция",
            "стек", "удалёнка", "офис", "собеседование", "резюме",
            "job", "hire", "position", "salary", "offer", "remote"
        ],
        "collaboration": [
            "сотрудничество", "совместно", "проект", "партнёрство",
            "давайте работать", "фриланс", "заказ", "контракт",
            "collaboration", "project", "freelance", "together", "contract"
        ],
        "question": [
            "вопрос", "подскажите", "расскажите", "как", "почему",
            "можно ли", "хотел узнать", "интересует", "объясните",
            "question", "how", "what", "tell me", "ask", "explain"
        ],
        "feedback": [
            "отзыв", "фидбек", "мнение", "впечатление", "понравилось",
            "не понравилось", "предложение", "рекомендация", "совет",
            "feedback", "review", "opinion", "suggestion", "advice"
        ],
    }
    
    HIGH_PRIORITY_KEYWORDS = [
        "срочно", "urgent", "asap", "быстро", "немедленно", "вакансия",
        "оффер", "job offer", "предложение работы", "интервью"
    ]
    
    # ===== FALLBACK-МЕТОДЫ (rule-based) =====
    
    @classmethod
    def _fallback_sentiment(cls, text):
        """
        Определяем тональность по ключевым словам.
        
        Проверяем ЦЕЛЫЕ СЛОВА (word boundaries), а не подстроки.
        Например, "работает" НЕ должно совпадать с "работа".
        """
        text_lower = text.lower()
        positive_count = 0
        negative_count = 0
        
        for word in cls.POSITIVE_WORDS:
            # \b — граница слова (начало/конец слова)
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, text_lower):
                positive_count += 1
        
        for word in cls.NEGATIVE_WORDS:
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, text_lower):
                negative_count += 1
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"

    @classmethod
    def _fallback_category(cls, text):
        """
        Классифицируем тип запроса по ключевым словам.
        
        Проверяем ЦЕЛЫЕ СЛОВА (word boundaries), а не подстроки.
        Например, "работает" НЕ должно совпадать с "работа".
        """
        text_lower = text.lower()
        scores = {}
        
        for category, keywords in cls.CATEGORY_KEYWORDS.items():
            score = 0
            for kw in keywords:
                # \b — граница слова (начало/конец слова)
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, text_lower):
                    score += 1
            scores[category] = score
        
        best_category = max(scores, key=scores.get)
        if scores[best_category] == 0:
            return "other"
        return best_category
    
    @classmethod
    def _fallback_priority(cls, text, category):
        """
        Определяем приоритет.
        
        Проверяем ЦЕЛЫЕ СЛОВА (word boundaries).
        """
        text_lower = text.lower()
        
        # Проверяем ключевые слова высокого приоритета
        for keyword in cls.HIGH_PRIORITY_KEYWORDS:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                return "high"
        
        # По категории
        if category in ("job_offer",):
            return "high"
        if category in ("collaboration",):
            return "medium"
        return "low"
    
    @classmethod
    def _fallback_response(cls, name, category):
        """
        Генерируем шаблонный ответ на основе категории.
        
        Это простой, но рабочий способ дать пользователю
        персонализированный ответ без AI.
        """
        templates = {
            "job_offer": (
                f"Здравствуйте, {name}! Спасибо за интерес к моему профилю. "
                "Я открыт к новым возможностям и буду рад обсудить детали вакансии. "
                "Свяжусь с вами в ближайшее время!"
            ),
            "collaboration": (
                f"Здравствуйте, {name}! Спасибо за предложение о сотрудничестве. "
                "Мне интересно узнать подробнее о проекте. "
                "Давайте обсудим детали — я свяжусь с вами в ближайшее время."
            ),
            "question": (
                f"Здравствуйте, {name}! Спасибо за ваш вопрос. "
                "Я получил ваше сообщение и подготовлю развёрнутый ответ. "
                "Свяжусь с вами в течение 24 часов."
            ),
            "feedback": (
                f"Здравствуйте, {name}! Спасибо за ваш отзыв, мне это очень важно. "
                "Я обязательно учту ваши слова в дальнейшей работе."
            ),
            "other": (
                f"Здравствуйте, {name}! Спасибо за ваше обращение. "
                "Я получил ваше сообщение и свяжусь с вами в ближайшее время."
            ),
        }
        return templates.get(category, templates["other"])
    
    @classmethod
    def _fallback_analysis(cls, name, message):
        """
        Полный fallback-анализ без AI.
        
        Возвращает тот же формат данных, что и Ollama анализ.
        """
        sentiment = cls._fallback_sentiment(message)
        category = cls._fallback_category(message)
        priority = cls._fallback_priority(message, category)
        auto_response = cls._fallback_response(name, category)
        
        return {
            "sentiment": sentiment,
            "category": category,
            "priority": priority,
            "auto_response": auto_response,
            "ai_used": False,
            "ai_fallback": True,
        }
    
    # ===== OLLAMA ИНТЕГРАЦИЯ (ДВА ЗАПРОСА) =====
    
    @classmethod
    def _build_classification_prompt(cls, name, message):
        """
        Промпт для ПЕРВОГО запроса: классификация обращения.
        """
        return (
            "Ты — AI-ассистент, анализирующий обращения с сайта-портфолио разработчика.\n"
            "Разработчик — Web (Vue.js) / Flutter / Backend разработчик из России (Чита).\n\n"
            "Проанализируй сообщение и верни ТОЛЬКО валидный JSON объект (без markdown, без пояснений, без обёрток ```json) со следующими полями:\n"
            '- "sentiment": одно из "positive", "neutral", "negative"\n'
            '- "category": одно из "job_offer", "collaboration", "question", "feedback", "other"\n'
            '- "priority": одно из "high", "medium", "low"\n\n'
            
            f"От кого: {name}\n"
            f"Сообщение: {message}\n\n"
            "Верни ТОЛЬКО JSON объект:"
        )
    
    @classmethod
    def _build_response_prompt(cls, name, message, classification_result):
        """
        Промпт для ВТОРОГО запроса: генерация ПОЛНОГО ответа.
        """
        sentiment = classification_result.get("sentiment", "neutral")
        category = classification_result.get("category", "other")
        priority = classification_result.get("priority", "medium")
        
        return (
            "Ты — AI-ассистент разработчика из России (Чита). Разработчик ищет работу.\n\n"
            f"Пользователь {name} написал обращение.\n"
            f"Текст сообщения: {message}\n\n"
            f"Анализ обращения:\n"
            f"- Тональность: {sentiment}\n"
            f"- Тип: {category}\n"
            f"- Приоритет: {priority}\n\n"
            "Напиши ВЕЖЛИВЫЙ, ПРОФЕССИОНАЛЬНЫЙ ОТВЕТ на русском языке от лица разработчика (от первого лица: Я получил, Я свяжусь).\n"
            "ОТВЕТ ДОЛЖЕН БЫТЬ ПОЛНЫМ И САМОДОСТАТОЧНЫМ — включать:\n"
            "1. Приветствие (Здравствуйте, {name}!)\n"
            "2. Благодарность за обращение\n"
            "3. Подтверждение получения сообщения\n"
            "4. Краткий ответ по сути (соответствующий типу обращения)\n"
            "5. Обещание связаться в ближайшее время\n\n"
            "Максимум 4-5 предложений. НЕ добавляй подписи в конце.\n\n"
            "ПРИМЕРЫ ПРАВИЛЬНЫХ ОТВЕТОВ:\n"
            "— 'Здравствуйте, Анна! Спасибо за ваше обращение. Я получил ваше сообщение и благодарю за интерес к открытой вакансии. Я свяжусь с вами в ближайшее время для обсуждения деталей.'\n"
            "— 'Добрый день, Иван! Благодарю за вопрос. Я получил ваше сообщение и подготовлю подробный ответ. Свяжусь с вами в течение 24 часов.'\n\n"
            "Верни ТОЛЬКО валидный JSON объект без markdown и пояснений в формате:\n"
            '{"auto_response": "твой полный текст ответа"}'
        )
    
    @classmethod
    def _call_ollama_classification(cls, name, message):
        """
        ПЕРВЫЙ запрос к Ollama: классификация обращения.
        """
        import requests
        
        base_url = current_app.config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = current_app.config.get("OLLAMA_MODEL", "qwen2.5:3b")
        timeout = current_app.config.get("AI_TIMEOUT", 60)
        
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        if base_url.endswith("/v1/"):
            base_url = base_url[:-4]
        
        url = f"{base_url}/api/chat"
        prompt = cls._build_classification_prompt(name, message)
        
        logger.info("Запрос #1: Классификация обращения (модель: %s)", model)
        
        try:
            response = requests.post(
                url,
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ты полезный ассистент. Отвечай ТОЛЬКО валидным JSON объектом. Без markdown, без пояснений, без обёрток ```json."
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 100,
                    }
                },
                timeout=timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            content = data.get("message", {}).get("content", "").strip()
            
            # Убираем markdown
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            
            result = json.loads(content)
            
            total_duration = data.get("total_duration", 0) / 1_000_000_000
            eval_count = data.get("eval_count", 0)
            logger.info(
                "Классификация завершена (tokens: %s, время: %.2f сек)",
                eval_count, total_duration
            )
            
            if not content:
                raise ValueError("Ollama вернул пустой ответ")
            
            # Валидация полей
            valid_sentiments = {"positive", "neutral", "negative"}
            valid_categories = {"job_offer", "collaboration", "question", "feedback", "other"}
            valid_priorities = {"high", "medium", "low"}
            
            if result.get("sentiment") not in valid_sentiments:
                result["sentiment"] = "neutral"
            if result.get("category") not in valid_categories:
                result["category"] = "other"
            if result.get("priority") not in valid_priorities:
                result["priority"] = "medium"
            
            return result
            
        except requests.exceptions.Timeout:
            logger.error("Ollama таймаут (>%d сек)", timeout)
            raise
        except requests.exceptions.ConnectionError:
            logger.error("Не удалось подключиться к Ollama по адресу %s", url)
            raise
        except json.JSONDecodeError as e:
            logger.error("Ollama вернул не-JSON: %s", str(e))
            logger.error("Сырой ответ: %s", content[:500] if 'content' in locals() else "N/A")
            raise
        except Exception as e:
            logger.error("Ошибка Ollama API: %s", str(e))
            raise
    
    @classmethod
    def _call_ollama_response_generation(cls, name, message, classification_result):
        """
        ВТОРОЙ запрос к Ollama: генерация текста ответа.
        """
        import requests
        
        base_url = current_app.config.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = current_app.config.get("OLLAMA_MODEL", "qwen2.5:3b")
        timeout = current_app.config.get("AI_TIMEOUT", 60)
        
        if base_url.endswith("/v1"):
            base_url = base_url[:-3]
        if base_url.endswith("/v1/"):
            base_url = base_url[:-4]
        
        url = f"{base_url}/api/chat"
        prompt = cls._build_response_prompt(name, message, classification_result)
        
        logger.info("Запрос #2: Генерация ответа (категория: %s)", classification_result.get("category"))
        
        try:
            response = requests.post(
                url,
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Ты полезный ассистент. Отвечай ТОЛЬКО валидным JSON объектом. Без markdown, без пояснений, без обёрток ```json."
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.5,
                        "num_predict": 300,
                    }
                },
                timeout=timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            content = data.get("message", {}).get("content", "").strip()
            
            # Убираем markdown
            content = re.sub(r"^```json\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            content = re.sub(r"^```\s*", "", content)
            content = re.sub(r"\s*```$", "", content)
            
            result = json.loads(content)
            auto_response = result.get("auto_response", "").strip()
            
            total_duration = data.get("total_duration", 0) / 1_000_000_000
            eval_count = data.get("eval_count", 0)
            logger.info(
                "Генерация ответа завершена (tokens: %s, время: %.2f сек, длина: %d симв.)",
                eval_count, total_duration, len(auto_response)
            )
            
            if not auto_response:
                raise ValueError("Ollama вернул пустое поле auto_response")
            
            return auto_response
            
        except requests.exceptions.Timeout:
            logger.error("Ollama таймаут (>%d сек)", timeout)
            raise
        except requests.exceptions.ConnectionError:
            logger.error("Не удалось подключиться к Ollama по адресу %s", url)
            raise
        except json.JSONDecodeError as e:
            logger.error("Ollama вернул не-JSON: %s", str(e))
            logger.error("Сырой ответ: %s", content[:500] if 'content' in locals() else "N/A")
            raise
        except Exception as e:
            logger.error("Ошибка Ollama API: %s", str(e))
            raise
    
    # ===== ГЛАВНЫЙ МЕТОД =====
    
    @classmethod
    def analyze(cls, name, message):
        """
        Анализирует обращение пользователя.
        
        Алгоритм:
        1. Если AI_ENABLED=True, делаем ДВА запроса к Ollama:
           - Запрос #1: классификация (sentiment, category, priority)
           - Запрос #2: генерация текста ответа на основе классификации
        2. Если любой из запросов упал — fallback на rule-based
        3. Если AI_ENABLED=False — сразу используем fallback
        
        ВСЕГДА возвращает результат и не падает.
        """
        ai_enabled = current_app.config.get("AI_ENABLED", True)
        
        if ai_enabled:
            try:
                # ЗАПРОС #1: Классификация
                classification = cls._call_ollama_classification(name, message)
                logger.info(
                    "AI классификация завершена: sentiment=%s, category=%s, priority=%s",
                    classification.get("sentiment"), 
                    classification.get("category"), 
                    classification.get("priority")
                )
                
                # ЗАПРОС #2: Генерация ответа
                auto_response = cls._call_ollama_response_generation(
                    name, message, classification
                )
                
                # Формируем итоговый результат
                result = {
                    "sentiment": classification.get("sentiment"),
                    "category": classification.get("category"),
                    "priority": classification.get("priority"),
                    "auto_response": auto_response,
                    "ai_used": True,
                    "ai_fallback": False,
                    "ai_provider": "ollama",
                    "ai_model": current_app.config.get("OLLAMA_MODEL", "qwen2.5:3b")
                }
                
                logger.info("AI анализ полностью завершён успешно")
                return result
                
            except Exception as e:
                logger.warning(
                    "Ollama недоступен (%s), переключаемся на fallback", 
                    str(e)
                )
        
        # Fallback анализ
        logger.info("Используем fallback-анализ (rule-based)")
        result = cls._fallback_analysis(name, message)
        logger.info(
            "Fallback анализ завершён: sentiment=%s, category=%s, priority=%s",
            result.get("sentiment"), 
            result.get("category"), 
            result.get("priority")
        )
        return result