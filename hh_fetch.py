"""
Сбор вакансий с HeadHunter через официальный api.hh.ru.

Правило из CLAUDE.md: только api.hh.ru, никакого парсинга HTML, уважаем лимиты.

--- Быстрый старт ---

1. Зарегистрируй приложение на https://dev.hh.ru/
   - redirect_uri = http://localhost:8765
   - Запиши HH_CLIENT_ID и HH_CLIENT_SECRET в .env

2. Получи токен (без браузера — только скопируй URL):
   python hh_fetch.py --auth

3. Ищи вакансии:
   python hh_fetch.py
"""

from __future__ import annotations

import csv
import os
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv, set_key

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# --- Константы -----------------------------------------------------------------
HH_API = "https://api.hh.ru"
HH_AUTH_URL = "https://hh.ru/oauth/authorize"
HH_TOKEN_URL = "https://hh.ru/oauth/token"
REDIRECT_URI = "http://localhost:8765"
CALLBACK_PORT = 8765

DELAY_BETWEEN_PAGES = (3.0, 5.0)
MAX_PAGES = 5
PER_PAGE = 100

AREAS = {
    "0":  "Вся Россия (без фильтра)",
    "1":  "Москва",
    "2":  "Санкт-Петербург",
    "3":  "Екатеринбург",
    "54": "Новосибирск",
    "88": "Казань",
}

CSV_COLUMNS = ["id", "название", "зарплата_от", "зарплата_до", "валюта", "локация"]
OUTPUT_DIR = Path("results/csv")
ENV_FILE = Path(".env")


# --- OAuth: получение токена ---------------------------------------------------
def run_oauth_flow(client_id: str, client_secret: str) -> str:
    """
    Печатает URL авторизации HH, ждёт вставки redirect-URL от пользователя,
    извлекает code и обменивает на access_token. Браузер и локальный сервер
    не нужны — пользователь копирует URL из адресной строки.
    """
    auth_url = (
        f"{HH_AUTH_URL}?"
        + urlencode({"response_type": "code", "client_id": client_id,
                     "redirect_uri": REDIRECT_URI})
    )

    print("\nШаг 1. Открой в браузере эту ссылку и войди в HH:")
    print(f"\n  {auth_url}\n")
    print("Шаг 2. После авторизации браузер попробует открыть localhost")
    print("        и покажет ошибку соединения — это нормально.")
    print("Шаг 3. Скопируй полный URL из адресной строки браузера")
    print("        (он начинается с http://localhost:8765?code=...)\n")

    while True:
        raw = input("Вставь URL из адресной строки: ").strip()
        params = parse_qs(urlparse(raw).query)
        if "code" in params:
            code = params["code"][0]
            break
        print("  Не нашёл параметр code в URL. Попробуй ещё раз.")

    print("Обмениваю код на токен...")
    resp = requests.post(HH_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }, timeout=15)
    resp.raise_for_status()
    token_data = resp.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise RuntimeError(f"Токен не получен. Ответ HH: {token_data}")

    return access_token


def save_token_to_env(token: str) -> None:
    """Записывает HH_TOKEN в .env."""
    if not ENV_FILE.exists():
        ENV_FILE.write_text("", encoding="utf-8")
    set_key(str(ENV_FILE), "HH_TOKEN", token)
    print(f"Токен сохранён в {ENV_FILE}")


def cmd_auth() -> None:
    """Точка входа для --auth: регистрирует токен."""
    client_id = os.getenv("HH_CLIENT_ID", "").strip()
    client_secret = os.getenv("HH_CLIENT_SECRET", "").strip()

    if not client_id or not client_secret:
        print(
            "Для получения токена нужны HH_CLIENT_ID и HH_CLIENT_SECRET.\n\n"
            "Как получить:\n"
            "  1. Зайди на https://dev.hh.ru/ и войди через HH-аккаунт\n"
            "  2. Создай приложение (название — любое, тип — сайт или нативное)\n"
            f"     redirect_uri = {REDIRECT_URI}\n"
            "  3. Скопируй client_id и client_secret в .env:\n"
            "     HH_CLIENT_ID=...\n"
            "     HH_CLIENT_SECRET=...\n"
            "  4. Снова запусти: python hh_fetch.py --auth"
        )
        sys.exit(1)

    token = run_oauth_flow(client_id, client_secret)
    save_token_to_env(token)
    print("\nГотово! Теперь запускай: python hh_fetch.py")


# --- HTTP с backoff ------------------------------------------------------------
def _get(url: str, params: dict | None, token: str, max_retries: int = 4) -> dict:
    user_agent = os.getenv("HH_USER_AGENT", "HR-Scoring-Tool/1.0 (user@example.com)")
    headers = {
        "User-Agent": user_agent,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Accept-Language": "ru-RU,ru;q=0.9",
    }
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 429:
                wait = 15 * (2 ** attempt)
                print(f"  ⚠ Rate limit (429), ждём {wait}с...")
                time.sleep(wait)
                continue
            if resp.status_code == 403:
                raise RuntimeError(
                    "403 Forbidden — токен недействителен или истёк.\n"
                    "Обнови токен: python hh_fetch.py --auth"
                )
            if resp.status_code == 401:
                raise RuntimeError(
                    "401 Unauthorized — токен не найден или неверный.\n"
                    "Получи токен: python hh_fetch.py --auth"
                )
            resp.raise_for_status()
            return resp.json()
        except requests.Timeout:
            wait = 5 * (2 ** attempt)
            print(f"  ⚠ Timeout, повтор через {wait}с...")
            time.sleep(wait)
        except requests.ConnectionError as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Нет соединения с api.hh.ru: {e}") from e
            time.sleep(5)
    raise RuntimeError(f"Не удалось получить {url} после {max_retries} попыток.")


# --- Поиск ---------------------------------------------------------------------
def search_all(query: str, area: str | None, max_pages: int, token: str) -> list[dict]:
    all_items: list[dict] = []
    for page in range(max_pages):
        params: dict = {"text": query, "per_page": PER_PAGE, "page": page}
        if area:
            params["area"] = area

        print(f"  Страница {page + 1}...", end=" ", flush=True)
        data = _get(f"{HH_API}/vacancies", params, token)

        items = data.get("items", [])
        total_pages = data.get("pages", 1)
        total_found = data.get("found", 0)

        all_items.extend(items)
        print(f"{len(items)} вакансий (всего на HH: {total_found})")

        if page >= total_pages - 1 or not items:
            break

        time.sleep(random.uniform(*DELAY_BETWEEN_PAGES))

    return all_items


# --- Извлечение полей и сохранение ---------------------------------------------
def extract_row(item: dict) -> dict:
    salary = item.get("salary") or {}
    return {
        "id":           item.get("id", ""),
        "название":     item.get("name", ""),
        "зарплата_от":  salary.get("from", ""),
        "зарплата_до":  salary.get("to", ""),
        "валюта":       salary.get("currency", ""),
        "локация":      (item.get("area") or {}).get("name", ""),
    }


def save_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


# --- Интерактивный ввод --------------------------------------------------------
def ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    return (input(f"{prompt}{hint}: ").strip()) or default


def ask_int(prompt: str, default: int, min_val: int, max_val: int) -> int:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            val = int(raw)
            if min_val <= val <= max_val:
                return val
            print(f"  Введи число от {min_val} до {max_val}.")
        except ValueError:
            print("  Нужно целое число.")


def choose_area() -> str | None:
    print("\nРегион:")
    for code, name in AREAS.items():
        print(f"  {code} — {name}")
    while True:
        raw = input("Код [0]: ").strip() or "0"
        if raw in AREAS:
            return None if raw == "0" else raw
        print(f"  Неизвестный код. Варианты: {', '.join(AREAS)}")


# --- main ----------------------------------------------------------------------
def main() -> None:
    load_dotenv()

    if "--auth" in sys.argv:
        cmd_auth()
        return

    token = os.getenv("HH_TOKEN", "").strip()
    if not token:
        sys.exit(
            "Токен HH не найден. Получи его:\n"
            "  1. Добавь HH_CLIENT_ID и HH_CLIENT_SECRET в .env\n"
            "  2. Запусти: python hh_fetch.py --auth\n\n"
            "Как зарегистрировать приложение: https://dev.hh.ru/"
        )

    print("=" * 55)
    print("  Поиск вакансий на HeadHunter (api.hh.ru)")
    print("=" * 55)

    query = ask("\nНазвание вакансии").strip()
    if not query:
        sys.exit("Запрос не может быть пустым.")

    area = choose_area()
    max_pages = ask_int(f"Страниц (по {PER_PAGE} вак.)", 2, 1, MAX_PAGES)

    safe_query = re.sub(r"[^\w\s-]", "_", query).strip().replace(" ", "_")[:40]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = OUTPUT_DIR / f"{safe_query}_{timestamp}.csv"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nЗапрос: «{query}» | Страниц: {max_pages}")
    print("-" * 55)

    items = search_all(query, area, max_pages, token)

    if not items:
        sys.exit("Вакансии не найдены. Попробуй другой запрос или регион.")

    rows = [extract_row(item) for item in items]
    save_csv(rows, csv_path)

    with_salary = sum(1 for r in rows if r["зарплата_от"] or r["зарплата_до"])
    print(f"\nИтого: {len(rows)} вакансий, из них с зарплатой: {with_salary}")
    print(f"Сохранено: {csv_path.resolve()}")


if __name__ == "__main__":
    main()
