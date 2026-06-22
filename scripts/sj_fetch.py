"""
Сбор вакансий с SuperJob через официальный api.superjob.ru.

Авторизация: API-ключ в заголовке X-Api-App-Id (OAuth не нужен для поиска).

Запуск:
  python sj_fetch.py

Добавь в .env:
  SJ_API_KEY=v3.r.1...
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

import requests
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# --- Константы -----------------------------------------------------------------
SJ_API = "https://api.superjob.ru/2.0"

DELAY_BETWEEN_PAGES = (2.0, 4.0)
MAX_PAGES = 5
PER_PAGE = 100  # максимум по документации

CITIES = {
    "0":  "Вся Россия (без фильтра)",
    "1":  "Москва",
    "2":  "Санкт-Петербург",
    "3":  "Новосибирск",
    "4":  "Екатеринбург",
    "5":  "Казань",
}

# SuperJob принимает название города строкой
CITY_NAMES = {
    "1": "Москва",
    "2": "Санкт-Петербург",
    "3": "Новосибирск",
    "4": "Екатеринбург",
    "5": "Казань",
}

CSV_COLUMNS = ["id", "название", "зарплата_от", "зарплата_до", "валюта", "локация"]
OUTPUT_DIR = Path("results/csv")


# --- HTTP с backoff ------------------------------------------------------------
def _get(url: str, params: dict | None, api_key: str, max_retries: int = 4) -> dict:
    headers = {
        "X-Api-App-Id": api_key,
        "User-Agent": os.getenv("SJ_USER_AGENT", "HR-Scoring-Tool/1.0"),
        "Accept": "application/json",
    }
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 429:
                wait = 15 * (2 ** attempt)
                print(f"  ⚠ Rate limit (429), ждём {wait}с...")
                time.sleep(wait)
                continue
            if resp.status_code in {401, 403}:
                raise RuntimeError(
                    f"{resp.status_code} — ключ недействителен или не передан.\n"
                    "Проверь SJ_API_KEY в .env."
                )
            resp.raise_for_status()
            return resp.json()
        except requests.Timeout:
            wait = 5 * (2 ** attempt)
            print(f"  ⚠ Timeout, повтор через {wait}с...")
            time.sleep(wait)
        except requests.ConnectionError as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Нет соединения с api.superjob.ru: {e}") from e
            time.sleep(5)
    raise RuntimeError(f"Не удалось получить {url} после {max_retries} попыток.")


# --- Поиск ---------------------------------------------------------------------
def search_all(keyword: str, city: str | None, max_pages: int, api_key: str) -> list[dict]:
    all_items: list[dict] = []

    for page in range(max_pages):
        params: dict = {"keyword": keyword, "count": PER_PAGE, "page": page}
        if city:
            params["town"] = city

        print(f"  Страница {page + 1}...", end=" ", flush=True)
        data = _get(f"{SJ_API}/vacancies/", params, api_key)

        items = data.get("objects", [])
        total = data.get("total", 0)
        has_more = data.get("more", False)

        all_items.extend(items)
        print(f"{len(items)} вакансий (всего на SJ: {total})")

        if not has_more or not items:
            break

        time.sleep(random.uniform(*DELAY_BETWEEN_PAGES))

    return all_items


# --- Извлечение полей ----------------------------------------------------------
def extract_row(item: dict) -> dict:
    return {
        "id":           item.get("id", ""),
        "название":     item.get("profession", ""),
        "зарплата_от":  item.get("payment_from") or "",
        "зарплата_до":  item.get("payment_to") or "",
        "валюта":       item.get("currency", ""),
        "локация":      (item.get("town") or {}).get("title", ""),
    }


# --- Сохранение ----------------------------------------------------------------
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


def choose_city() -> str | None:
    print("\nГород:")
    for code, name in CITIES.items():
        print(f"  {code} — {name}")
    while True:
        raw = input("Код [0]: ").strip() or "0"
        if raw in CITIES:
            return CITY_NAMES.get(raw)  # None если "0" (вся Россия)
        print(f"  Неизвестный код. Варианты: {', '.join(CITIES)}")


# --- main ----------------------------------------------------------------------
def main() -> None:
    load_dotenv()

    api_key = os.getenv("SJ_API_KEY", "").strip()
    if not api_key:
        sys.exit(
            "Ключ SuperJob не найден.\n"
            "Добавь в .env:\n  SJ_API_KEY=v3.r.1..."
        )

    print("=" * 55)
    print("  Поиск вакансий на SuperJob (api.superjob.ru)")
    print("=" * 55)

    keyword = ask("\nНазвание вакансии").strip()
    if not keyword:
        sys.exit("Запрос не может быть пустым.")

    city = choose_city()
    max_pages = ask_int(f"Страниц (по {PER_PAGE} вак.)", 2, 1, MAX_PAGES)

    safe_keyword = re.sub(r"[^\w\s-]", "_", keyword).strip().replace(" ", "_")[:40]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    csv_path = OUTPUT_DIR / f"sj_{safe_keyword}_{timestamp}.csv"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    city_label = city or "вся Россия"
    print(f"\nЗапрос: «{keyword}» | Город: {city_label} | Страниц: {max_pages}")
    print("-" * 55)

    items = search_all(keyword, city, max_pages, api_key)

    if not items:
        sys.exit("Вакансии не найдены. Попробуй другой запрос или город.")

    rows = [extract_row(item) for item in items]
    save_csv(rows, csv_path)

    with_salary = sum(1 for r in rows if r["зарплата_от"] or r["зарплата_до"])
    print(f"\nИтого: {len(rows)} вакансий, из них с зарплатой: {with_salary}")
    print(f"Сохранено: {csv_path.resolve()}")


if __name__ == "__main__":
    main()
