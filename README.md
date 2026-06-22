# HR Scoring

Внутренний инструмент отдела АБП. Две задачи:

1. **LLM-скоринг резюме** — ранжирование кандидатов под вакансию с обоснованием
2. **Сбор рыночных данных** — вакансии и зарплатные вилки с HH и SuperJob с историей

---

## Локальная разработка

```bash
cp .env.example .env   # заполнить ключи
docker compose up
```

- Интерфейс: http://localhost:5173
- API docs: http://localhost:8000/docs
- Админ-панель: http://localhost:8000/admin

---

## Деплой на сервер

### Что нужно один раз

**1. Арендовать VPS**

Минимум: 1 CPU, 1 GB RAM + 2 GB swap, Ubuntu 22.04.
Подходит Hetzner CX11 (~4€/мес), Timeweb, Selectel, REG.RU.

**2. Настроить сервер**

Подключись по SSH и выполни:

```bash
# Установи Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER
newgrp docker

# Добавь своп 2 GB (если RAM = 1 GB)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

# Склонируй репозиторий
mkdir -p /srv && cd /srv
git clone https://github.com/funtiknax13/hr_scoring.git
cd hr_scoring

# Создай и заполни .env
cp .env.example .env
nano .env
```

**3. Первый запуск**

```bash
cd /srv/hr_scoring
docker compose -f docker-compose.prod.yml up --build -d
sleep 10
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head
```

Сервис доступен на `http://<IP сервера>`.

**4. Создать SSH-ключ для GitHub Actions**

На сервере:

```bash
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions -N ""
cat ~/.ssh/github_actions.pub >> ~/.ssh/authorized_keys
cat ~/.ssh/github_actions   # скопируй — понадобится на следующем шаге
```

**5. Добавить секреты в GitHub**

Открой репозиторий → **Settings → Secrets and variables → Actions → New repository secret**:

| Секрет | Значение |
|---|---|
| `SERVER_HOST` | IP-адрес сервера |
| `SERVER_USER` | Пользователь (обычно `root`) |
| `SSH_PRIVATE_KEY` | Содержимое файла `~/.ssh/github_actions` |
| `SERVER_PORT` | `22` |

### Автодеплой

После настройки каждый `git push` в ветку `main` автоматически:
1. Подключается к серверу по SSH
2. Делает `git pull`
3. Пересобирает и перезапускает контейнеры
4. Применяет новые миграции

Статус деплоя — во вкладке **Actions** на GitHub.

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

Пользователей создаёт администратор через панель `/admin`.

---

## Источники данных

### SuperJob

Работает. Нужен API-ключ от [api.superjob.ru](https://api.superjob.ru), указать в `SJ_API_KEY`.

### HeadHunter

> **Не работает.** Публичный API закрыт с декабря 2025 — требуется OAuth через работодательский аккаунт. Заявка на [dev.hh.ru](https://dev.hh.ru) подана, ожидает одобрения. После одобрения: `python scripts/hh_fetch.py --auth`.

---

## Добавление нового источника

Все источники реализуют единый интерфейс из `backend/app/sources/base.py`. Чтобы добавить новый:

**1. Создать модуль** `backend/app/sources/<название>.py`:

```python
from app.sources.base import BaseSource, VacancyRow

class MySource(BaseSource):
    def search(self, query: str, city: str | None, max_pages: int) -> list[VacancyRow]:
        ...
```

`VacancyRow` — датакласс с полями: `external_id`, `title`, `company`, `location`, `url`, `salary_from`, `salary_to`, `currency`, `description`.

**2. Зарегистрировать** в `backend/app/sources/registry.py`:

```python
SOURCES: dict[str, BaseSource] = {
    "hh": HHSource(),
    "sj": SJSource(),
    "my": MySource(),   # добавить строку
}
```

**3. Добавить эндпоинт** в `backend/app/routers/vacancies.py` по аналогии с `/hh` и `/sj`.

После этого новый источник доступен в расписаниях Celery (поле `source` в `ScheduledSearch`).

---

## Команды

```bash
# Разработка
docker compose up
docker compose up --build

# Продакшен
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# Скрипты
python scripts/score.py              # скоринг из CLI
python scripts/sj_fetch.py          # выгрузка SuperJob
python scripts/hh_fetch.py --auth   # авторизация HH (когда заработает)
```

---

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy, Alembic, PostgreSQL
- **LLM:** DeepSeek через OpenAI-совместимый SDK
- **Frontend:** React 18, Vite, TypeScript, Tailwind CSS; в продакшене — nginx со статической сборкой
- **Инфра:** Docker Compose, Celery + Redis, GitHub Actions (автодеплой)
