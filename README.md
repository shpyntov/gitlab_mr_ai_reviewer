# GitLab MR AI Reviewer

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-containerized-blue.svg)](https://www.docker.com/)

**Автоматический анализ кода с помощью ИИ для Merge Request в GitLab.**

Готовое к продакшену Python-решение, которое интегрируется с GitLab CI и анализирует изменения в merge request с использованием больших языковых моделей (LLM). Предоставляет интеллектуальную обратную связь об ошибках, проблемах безопасности, производительности и качестве кода.

## Возможности

- 🤖 **Анализ на основе ИИ** — использует продвинутые языковые модели для понимания контекста кода и предоставления содержательной обратной связи
- 📝 **Обзорное рецензирование** — предоставляет единое комплексное резюме рецензии
- 🔧 **Интеграция с GitLab CI** — автоматически запускается в пайплайнах merge request
- 🐳 **Контейнеризация** — готово к развёртыванию в Docker
- ⚙️ **Настраиваемость** — настройка поведения рецензирования через переменные окружения
- 🛡️ **Умная дедупликация** — избегает публикации дублирующихся комментариев
- 🔄 **Повторные попытки** — корректно обрабатывает ошибки API

## Быстрый старт

### 1. Сборка Docker-образа

```bash
docker build -t reviewbot:latest .
```

### 2. Локальный запуск для тестирования

```bash
docker run \
  -e LLM_API_KEY=your_llm_api_key \
  -e GITLAB_TOKEN=your_gitlab_token \
  -e GITLAB_PROJECT_ID=12345 \
  -e GITLAB_MERGE_REQUEST_ID=67 \
  -e GITLAB_BASE_URL=https://gitlab.com \
  -e LLM_MODEL=Qwen/Qwen3-Coder-480B-A35B-Instruct \
  -e LLM_TEMPERATURE=0.3 \
  -e LLM_MAX_TOKENS=2000 \
  reviewbot:latest
```

### 3. Интеграция с GitLab CI

Скопируйте `.gitlab-ci.yml.example` в `.gitlab-ci.yml` в вашем проекте:

```yaml
ai_code_review:
  image: reviewbot:latest
  stage: test
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - python -m reviewbot.main
  allow_failure: true
```

## Конфигурация

### Переменные окружения

| Переменная | Обязательна | Описание |
|------------|-------------|----------|
| `LLM_API_KEY` | Да | Ключ API для LLM |
| `GITLAB_TOKEN` | Да | Персональный токен GitLab (scope: api) |
| `GITLAB_PROJECT_ID` | Да | ID проекта GitLab |
| `GITLAB_MERGE_REQUEST_ID` | Да | ID merge request |
| `GITLAB_BASE_URL` | Да | Базовый URL GitLab (например, `https://gitlab.com`) |
| `REVIEW_LANGUAGE` | Нет | Язык комментариев рецензии (по умолчанию: `ru`). Доступные значения: `en`, `ru` |
| `LLM_MODEL` | Нет | Имя модели LLM (по умолчанию: `Qwen/Qwen3-Coder-480B-A35B-Instruct`) |
| `LLM_BASE_URL` | Нет | Базовый URL API LLM (по умолчанию: `https://foundation-models.api.cloud.ru/v1`) |
| `LLM_TEMPERATURE` | Нет | Параметр temperature для LLM (по умолчанию: `0.3`) |
| `LLM_MAX_TOKENS` | Нет | Максимальное количество токенов в ответе LLM (по умолчанию: `2000`) |

## Формат рецензии

Бот публикует единое комплексное резюме рецензии:

```markdown
## AI Code Review Summary

### Potential Issues
- Possible null pointer in user service
- Missing input validation in API endpoint

### Improvements
- Consider using dependency injection
- Add unit tests for edge cases

### Positive Notes
- Good error handling in database layer
- Clean separation of concerns
```

## Поддерживаемые языки

- Python
- Go
- JavaScript / TypeScript
- Java
- C / C++
- Rust

## Получение токена GitLab

1. Перейдите в **User Settings** → **Access Tokens**
2. Создайте новый токен с scope `api`
3. Скопируйте токен и установите в переменную окружения `GITLAB_TOKEN`

## Локальная разработка

### Требования

- Python 3.11+
- Docker (опционально)

### Настройка

```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Установка переменных окружения
export LLM_API_KEY=your_key
export GITLAB_TOKEN=your_token
export GITLAB_PROJECT_ID=12345
export GITLAB_MERGE_REQUEST_ID=67
export GITLAB_BASE_URL=https://gitlab.com
export LLM_MODEL=Qwen/Qwen3-Coder-480B-A35B-Instruct
export LLM_TEMPERATURE=0.3
export LLM_MAX_TOKENS=2000

# Запуск рецензента
python -m reviewbot.main
```

### Тестирование с Docker Compose

```bash
# Создание файла .env
cat > .env << EOF
LLM_API_KEY=your_key
GITLAB_TOKEN=your_token
GITLAB_PROJECT_ID=12345
GITLAB_MERGE_REQUEST_ID=67
GITLAB_BASE_URL=https://gitlab.com
LLM_MODEL=Qwen/Qwen3-Coder-480B-A35B-Instruct
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000
EOF

# Запуск через docker-compose
docker-compose up reviewbot
```

## Структура проекта

```
gitlab_mr_ai_reviwer/
├── reviewbot/
│   ├── __init__.py          # Инициализация пакета
│   ├── main.py              # Точка входа
│   ├── config_loader.py     # Управление конфигурацией
│   ├── diff_parser.py       # Логика парсинга diff
│   ├── gitlab_client.py     # GitLab API клиент
│   ├── llm_client.py        # LLM API клиент
│   └── review_engine.py     # Основная оркестрация рецензии
├── prompts/
│   └── summary_review_prompt.md # Промпт для обзорной рецензии
├── .gitlab-ci.yml.example   # Пример CI конфигурации
├── Dockerfile               # Описание контейнера
├── docker-compose.yml       # Локальное тестирование
├── requirements.txt         # Python зависимости
├── README.md                # Этот файл
└── LICENSE                  # MIT License
```

## Логирование

Бот использует структурированное логирование:

```
[INFO] Fetching MR changes
[INFO] Found 5 changed files
[INFO] Sending diff to LLM for app/service.py
[INFO] Posting comment to app/service.py:42
[INFO] Review completed successfully
```

## Обработка ошибок

- **Повторные попытки API**: автоматические повторные попытки с экспоненциальной задержкой для GitLab и LLM API
- **Ограничение частоты**: соблюдение ограничений частоты GitLab с соответствующим временем ожидания
- **Валидация JSON**: проверка ответов LLM и обработка ошибок парсинга
- **Обнаружение дубликатов**: предотвращение публикации дублирующихся комментариев

## Вопросы безопасности

- Ключи API передаются только через переменные окружения
- Конфиденциальные данные не логируются
- Токены GitLab должны иметь минимально необходимый scope (`api`)
- Рассмотрите использование CI/CD variables для секретов в GitLab

## Решение проблем

### "Missing required environment variables"

Убедитесь, что все обязательные переменные окружения установлены:
```bash
export LLM_API_KEY=xxx
export GITLAB_TOKEN=xxx
export GITLAB_PROJECT_ID=xxx
export GITLAB_MERGE_REQUEST_ID=xxx
export GITLAB_BASE_URL=xxx
```

### "LLM_API_KEY is required"

Ключ LLM API должен быть установлен. Проверьте [интеграцию LLM клиента](reviewbot/llm_client.py) для ожидаемого формата.

### Комментарии не публикуются

Проверьте:
1. Файлы соответствуют настроенным языкам
2. Пути не находятся в списке игнорируемых
3. Комментарии не являются дубликатами (бот не публикует повторяющиеся резюме)

### Ограничение частоты (Rate limiting)

Бот реализует автоматические повторные попытки с задержкой. Если вы часто сталкиваетесь с ограничениями, рассмотрите:
- Увеличение задержки между повторными попытками в конфигурации
- Уменьшение частоты рецензий
- Использование выделенного токена GitLab

## Лицензия

MIT License — подробности в файле [LICENSE](LICENSE).

## Вклад в проект

Вклад приветствуется! Не стесняйтесь отправлять Merge Request.

1. Форкните репозиторий
2. Создайте ветку для новой функциональности
3. Внесите изменения
4. Запустите тесты (если применимо)
5. Отправьте Merge Request
