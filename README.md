# GitLab MR AI Reviewer

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-containerized-blue.svg)](https://www.docker.com/)
[![CI/CD](https://github.com/shpyntov/gitlab_mr_ai_reviewer/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/shpyntov/gitlab_mr_ai_reviewer/actions/workflows/docker-publish.yml)
[![Powered by Cloud.ru](https://img.shields.io/badge/Powered%20by-Cloud.ru-4A90E2?style=flat)](https://cloud.ru)

**Автоматический анализ кода с помощью ИИ для Merge Request в GitLab.**

Готовое к продакшену решение, которое интегрируется с GitLab CI и анализирует изменения в merge request с использованием больших языковых моделей (LLM).

---

## Возможности

- 🤖 **Анализ на основе ИИ** — LLM для понимания контекста и содержательной обратной связи
- 📝 **Summary-рецензирование** — единое комплексное резюме по всем изменениям
- 🔄 **Обновление комментариев** — автоматическое обновление при повторном запуске
- 🔧 **GitLab CI интеграция** — запуск в пайплайнах merge request
- 🐳 **Docker** — готово к развёртыванию в контейнерах
- ⚙️ **Гибкая настройка** — конфигурация через переменные окружения
- 🛡️ **Retry logic** — обработка ошибок API с повторными попытками

---

## Быстрый старт

### 1. Получить образ

```bash
# Готовый образ из GHCR
docker pull ghcr.io/shpyntov/gitlab_mr_ai_reviewer:latest
```

Или собрать локально:

```bash
docker build -t reviewbot:latest .
```

### 2. Запустить

```bash
docker run --rm \
  -e LLM_API_KEY=<your_key> \
  -e GITLAB_TOKEN=<your_token> \
  -e GITLAB_PROJECT_ID=12345 \
  -e GITLAB_MERGE_REQUEST_ID=67 \
  -e GITLAB_BASE_URL=https://gitlab.com \
  ghcr.io/shpyntov/gitlab_mr_ai_reviewer:latest
```

### 3. Интегрировать с GitLab CI

Скопируйте `.gitlab-ci.yml.example` в `.gitlab-ci.yml`:

```yaml
ai_code_review:
  image: ghcr.io/shpyntov/gitlab_mr_ai_reviewer:latest
  stage: test
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  variables:
    LLM_API_KEY: $LLM_API_KEY_SECRET
    GITLAB_TOKEN: $GITLAB_TOKEN_SECRET
    GITLAB_PROJECT_ID: $CI_PROJECT_ID
    GITLAB_MERGE_REQUEST_ID: $CI_MERGE_REQUEST_IID
    GITLAB_BASE_URL: $CI_SERVER_URL
  script:
    - python -m reviewbot.main
  allow_failure: true
```

> **Примечание:** Добавьте `LLM_API_KEY_SECRET` и `GITLAB_TOKEN_SECRET` в **Settings → CI/CD → Variables** вашего проекта.

---

## Конфигурация

### Переменные окружения

| Переменная | Обязательна | По умолчанию | Описание |
|------------|:-----------:|--------------|----------|
| `LLM_API_KEY` | **Да** | — | Ключ API для LLM провайдера |
| `GITLAB_TOKEN` | **Да** | — | Токен GitLab |
| `GITLAB_PROJECT_ID` | **Да** | — | ID проекта GitLab |
| `GITLAB_MERGE_REQUEST_ID` | **Да** | — | ID merge request |
| `GITLAB_BASE_URL` | **Да** | — | URL GitLab (например, `https://gitlab.com`) |
| `LLM_BASE_URL` | Нет | `https://foundation-models.api.cloud.ru/v1` | URL **OpenAI-compatible API**. Поддерживаются любые провайдеры с совместимым API: Cloud.ru, YandexGPT, Together AI, Groq, Ollama (локально) и др. |
| `LLM_MODEL` | Нет | `Qwen/Qwen3-Coder-480B-A35B-Instruct` | Имя модели LLM |
| `LLM_TEMPERATURE` | Нет | `0.3` | Температура генерации (0.0–1.0) |
| `LLM_MAX_TOKENS` | Нет | `2000` | Максимум токенов в ответе |
| `REVIEW_LANGUAGE` | Нет | `ru` | Язык рецензии (`en` или `ru`) |

---

## Использование

### Локальный запуск

```bash
# Установка переменных окружения
export LLM_API_KEY=<your_key>
export GITLAB_TOKEN=<your_token>
export GITLAB_PROJECT_ID=12345
export GITLAB_MERGE_REQUEST_ID=67
export GITLAB_BASE_URL=https://gitlab.com

# Запуск
python -m reviewbot.main
```

### Docker Compose

Создайте `.env` файл:

```bash
LLM_API_KEY=<your_key>
GITLAB_TOKEN=<your_token>
GITLAB_PROJECT_ID=12345
GITLAB_MERGE_REQUEST_ID=67
GITLAB_BASE_URL=https://gitlab.com
```

Запустите:

```bash
docker-compose up reviewbot
```

---

## Альтернативные LLM провайдеры

Проект поддерживает любые API с **OpenAI-compatible** интерфейсом.

### Популярные провайдеры

| Провайдер | LLM_BASE_URL | Пример модели | Цена за 1M токенов |
|-----------|--------------|---------------|-------------------|
| **OpenAI (ChatGPT)** | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo` | от $0.15 |
| **Anthropic (Claude)** | `https://api.anthropic.com/v1` | `claude-sonnet-4-20250514`, `claude-3-5-sonnet-latest` | от $3 |
| **Google (Gemini)** | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.5-flash`, `gemini-2.5-pro` | от $0.075 |
| **Azure OpenAI** | `https://{resource}.openai.azure.com/openai/deployments/{deployment}` | `gpt-4o`, `gpt-4-turbo` | от $2 |

### Бюджетные альтернативы

| Провайдер | LLM_BASE_URL | Пример модели | Цена за 1M токенов |
|-----------|--------------|---------------|-------------------|
| **Cloud.ru** (по умолчанию) | `https://foundation-models.api.cloud.ru/v1` | `Qwen/Qwen3-Coder-480B-A35B-Instruct` | ~$0.20 |
| **Together AI** | `https://api.together.xyz/v1` | `Qwen/Qwen2.5-Coder-32B-Instruct` | ~$0.18 |
| **DeepInfra** | `https://api.deepinfra.com/v1/openai` | `Qwen/Qwen2.5-Coder-32B-Instruct` | ~$0.09 |
| **Groq** | `https://api.groq.com/openai/v1` | `llama-3.1-70b-versatile` | ~$0.40 |

### Локальные решения

| Провайдер | LLM_BASE_URL | Пример модели | Цена |
|-----------|--------------|---------------|------|
| **Ollama** | `http://localhost:11434/v1` | `qwen2.5-coder:32b`, `llama3.1:8b` | Бесплатно |
| **LM Studio** | `http://localhost:1234/v1` | Любые GGUF модели | Бесплатно |
| **vLLM** | `http://localhost:8000/v1` | Любые модели с HuggingFace | Бесплатно |

### Пример для OpenAI (ChatGPT)

```bash
docker run --rm \
  -e LLM_API_KEY=sk-your_openai_api_key \
  -e LLM_BASE_URL=https://api.openai.com/v1 \
  -e LLM_MODEL=gpt-4o \
  -e GITLAB_TOKEN=your_gitlab_token \
  -e GITLAB_PROJECT_ID=8321 \
  -e GITLAB_MERGE_REQUEST_ID=874 \
  -e GITLAB_BASE_URL=https://gitlab.com \
  -e REVIEW_LANGUAGE=ru \
  ghcr.io/shpyntov/gitlab_mr_ai_reviewer:1.0.2
```

### Пример для Ollama (локально)

```bash
docker run --rm \
  --network host \
  -e LLM_API_KEY=ollama \
  -e LLM_BASE_URL=http://localhost:11434/v1 \
  -e LLM_MODEL=qwen2.5-coder:32b \
  -e GITLAB_TOKEN=your_gitlab_token \
  -e GITLAB_PROJECT_ID=8321 \
  -e GITLAB_MERGE_REQUEST_ID=874 \
  -e GITLAB_BASE_URL=https://gitlab.com \
  -e REVIEW_LANGUAGE=ru \
  ghcr.io/shpyntov/gitlab_mr_ai_reviewer:1.0.2
```

---

## Пример вывода

Бот публикует комментарий в формате Markdown:

```markdown
## ИИ код-ревью

### Возможные проблемы
- Возможный NullPointerException в сервисе пользователей
- Отсутствует валидация входных данных в API endpoint

### Рекомендации
- Рассмотрите использование dependency injection
- Добавьте unit tests для граничных значений

### Положительные моменты
- Хорошая обработка ошибок в слое доступа к данным
- Чёткое разделение ответственности между компонентами
```

---

## Поддерживаемые языки

| Язык | Расширения |
|------|------------|
| Python | `.py` |
| Go | `.go` |
| JavaScript / TypeScript | `.js`, `.jsx`, `.ts`, `.tsx` |
| Java | `.java` |
| C / C++ | `.c`, `.cpp`, `.h`, `.hpp` |
| Rust | `.rs` |

---

## Разработка

### Требования

- Python 3.11+
- Docker (опционально)

### Установка

```bash
# Виртуальное окружение
python -m venv venv
source venv/bin/activate

# Зависимости
pip install -r requirements.txt
```

### Линтинг и форматирование

Проект использует [ruff](https://github.com/astral-sh/ruff):

```bash
# Проверка
ruff check reviewbot/

# Автофикс
ruff check --fix reviewbot/

# Форматирование
ruff format reviewbot/
```

Конфигурация в `ruff.toml`:
- Длина строки: 120 символов
- Проверки: E, F, I, W, N, B, C4, UP
- Стиль docstring: Google

---

## Решение проблем

### Missing required environment variables

Убедитесь, что все обязательные переменные установлены:

```bash
export LLM_API_KEY=xxx
export GITLAB_TOKEN=xxx
export GITLAB_PROJECT_ID=xxx
export GITLAB_MERGE_REQUEST_ID=xxx
export GITLAB_BASE_URL=xxx
```

### Комментарии не публикуются

Проверьте:
1. Файлы соответствуют поддерживаемым языкам
2. Пути не в списке игнорируемых (`vendor/`, `node_modules/`, и т.д.)
3. Summary-комментарий уже существует (бот обновляет его, а не создаёт дубликат)

### Rate limiting

Бот автоматически повторяет запросы с задержкой. При частых ограничениях:
- Увеличьте задержку между попытками
- Используйте выделенный токен GitLab

---

## Лицензия

[MIT License](LICENSE) — свободное использование с сохранением уведомления об авторских правах.

---

## Вклад в проект

Приветствуются issue и merge request!

1. Форкните репозиторий
2. Создайте ветку (`git checkout -b feature/amazing-feature`)
3. Внесите изменения
4. Запустите линтер (`ruff check reviewbot/`)
5. Отправьте MR
