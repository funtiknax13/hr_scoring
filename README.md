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
| `HH_CLIENT_ID` | Client ID приложения HH |
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

pytest                     # тесты
ruff check . && ruff format .  # линт и форматирование

# внутри контейнера backend:
alembic upgrade head       # применить миграции
python seed.py             # создать admin-пользователя
python -m eval.run         # прогон eval скоринга
```

---

## Скрипты (автономный режим)

До появления веб-интерфейса скоринг и выгрузка работали через CLI-скрипты.
Они остаются для отладки и ручных прогонов.

### `score.py`
```bash
python score.py [--data-dir data] [--vacancy <файл>] [--resumes-dir data/resumes]
                [--model deepseek-chat] [--no-cache] [--out results.json]
```
Результат — таблица в консоли и `results.json`.

### `hh_fetch.py`

> Требует одобрения заявки на [dev.hh.ru](https://dev.hh.ru). Публичный API закрыт с декабря 2025.

```bash
python hh_fetch.py --auth   # первичная авторизация (один раз)
python hh_fetch.py          # выгрузка вакансий в CSV
```

### `sj_fetch.py`
```bash
python sj_fetch.py          # выгрузка вакансий SuperJob в CSV
```

---

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **LLM:** DeepSeek через OpenAI-совместимый SDK
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS
- **Инфра:** Docker Compose, Celery + Redis (планируется)
