# HR Scoring

Внутренний инструмент отдела АБП. Две задачи:

1. **LLM-скоринг резюме** — ранжирование кандидатов под вакансию с обоснованием
2. **Сбор рыночных данных** — вакансии и зарплатные вилки с HH и SuperJob с историей

---

## Быстрый старт

```bash
cp .env.example .env   # заполнить ключи (см. раздел ниже)
docker compose up
```

- Интерфейс: [http://localhost:5173](http://localhost:5173)
- API: [http://localhost:8000/docs](http://localhost:8000/docs)
- Админ-панель: [http://localhost:8000/admin](http://localhost:8000/admin)

---

## Переменные окружения

Скопируй `.env.example` в `.env` и заполни:

| Переменная | Описание |
|---|---|
| `DEEPSEEK_API_KEY` | Ключ DeepSeek API (обязателен для скоринга) |
| `DEEPSEEK_BASE_URL` | URL API, по умолчанию `https://api.deepseek.com` |
| `SJ_API_KEY` | Ключ SuperJob API |
| `HH_CLIENT_ID` | Client ID приложения HH (см. примечание ниже) |
| `HH_CLIENT_SECRET` | Client Secret приложения HH |
| `HH_TOKEN` | OAuth-токен HH (заполняется через `--auth`) |
| `HH_USER_AGENT` | Идентификатор приложения для HH API |
| `POSTGRES_USER` | Пользователь БД (по умолчанию: `hr`) |
| `POSTGRES_PASSWORD` | Пароль БД |
| `POSTGRES_DB` | Имя БД (по умолчанию: `hr_scoring`) |
| `SECRET_KEY` | Секрет для подписи JWT и сессий |
| `ADMIN_USERNAME` | Логин первого администратора |
| `ADMIN_PASSWORD` | Пароль первого администратора |

`SECRET_KEY` можно сгенерировать:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Роли

| Роль | Скоринг | Просмотр результатов | Выгрузка вакансий | Просмотр вакансий | Админ-панель |
|---|:---:|:---:|:---:|:---:|:---:|
| `admin` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `hr` | ✓ | ✓ | ✓ | ✓ | — |
| `analyst` | — | ✓ | — | ✓ | — |

Пользователей создаёт администратор через [панель](http://localhost:8000/admin).

---

## Команды

```bash
docker compose up          # запустить всё
docker compose up --build  # пересобрать образы

# внутри контейнера backend:
alembic upgrade head       # применить миграции
python seed.py             # создать admin-пользователя
```

---

## Источники данных

### SuperJob

Работает. Для подключения нужен API-ключ от [api.superjob.ru](https://api.superjob.ru), укажи его в `SJ_API_KEY`.

### HeadHunter

> **Не работает.** Публичный API закрыт с декабря 2025 — теперь требуется OAuth через работодательский аккаунт. Заявка на [dev.hh.ru](https://dev.hh.ru) подана, ожидает одобрения. После одобрения нужно пройти авторизацию: `python hh_fetch.py --auth`.

---

## Добавление нового источника

Все источники реализуют единый интерфейс из `backend/app/sources/base.py`. Чтобы добавить новый:

**1. Создать модуль** `backend/app/sources/<название>.py`:

```python
from app.sources.base import BaseSource, VacancyRow

class MySource(BaseSource):
    def search(self, query: str, city: str | None, max_pages: int) -> list[VacancyRow]:
        # Запросы к API, возвращаем список VacancyRow
        ...
```

`VacancyRow` — датакласс с полями: `external_id`, `title`, `company`, `location`, `url`, `salary_from`, `salary_to`, `currency`, `description`.

**2. Зарегистрировать** в `backend/app/sources/registry.py`:

```python
from app.sources.mymodule import MySource

SOURCES: dict[str, BaseSource] = {
    "hh": HHSource(),
    "sj": SJSource(),
    "my": MySource(),   # добавить строку
}
```

**3. Добавить эндпоинт** в `backend/app/routers/vacancies.py` по аналогии с `/hh` и `/sj`.

После этого новый источник автоматически становится доступен в расписаниях Celery (поле `source` в `ScheduledSearch`).

---

## Скрипты (автономный режим)

CLI-скрипты лежат в `scripts/`, остаются для отладки и ручных прогонов.

| Скрипт | Описание |
|---|---|
| `python scripts/score.py` | Скоринг из командной строки |
| `python scripts/hh_fetch.py --auth` | Первичная авторизация HH (когда заработает) |
| `python scripts/sj_fetch.py` | Ручная выгрузка SuperJob в CSV |

---

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **LLM:** DeepSeek через OpenAI-совместимый SDK
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS
- **Инфра:** Docker Compose, Celery + Redis
