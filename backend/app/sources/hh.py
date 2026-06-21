import random
import time

import requests

from app.config import settings
from app.sources.base import BaseSource, VacancyRow

HH_API = "https://api.hh.ru"
PER_PAGE = 100
DELAY = (3.0, 5.0)

# Название города → код региона HH
AREA_MAP: dict[str, str] = {
    "москва": "1",
    "санкт-петербург": "2",
    "екатеринбург": "3",
    "новосибирск": "54",
    "казань": "88",
}


class HHSource(BaseSource):
    name = "hh"

    def _get(self, url: str, params: dict | None) -> dict:
        if not settings.hh_token:
            raise RuntimeError(
                "HH_TOKEN не задан. Получи токен: python hh_fetch.py --auth"
            )
        headers = {
            "User-Agent": settings.hh_user_agent,
            "Authorization": f"Bearer {settings.hh_token}",
            "Accept": "application/json",
            "Accept-Language": "ru-RU,ru;q=0.9",
        }
        for attempt in range(4):
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=15)
                if resp.status_code == 429:
                    time.sleep(15 * (2 ** attempt))
                    continue
                if resp.status_code == 403:
                    raise RuntimeError("HH: токен истёк. Обнови: python hh_fetch.py --auth")
                if resp.status_code == 401:
                    raise RuntimeError("HH: токен не найден или неверный.")
                resp.raise_for_status()
                return resp.json()
            except requests.Timeout:
                time.sleep(5 * (2 ** attempt))
            except requests.ConnectionError as e:
                if attempt == 3:
                    raise RuntimeError(f"Нет соединения с api.hh.ru: {e}") from e
                time.sleep(5)
        raise RuntimeError("HH: превышено число попыток.")

    def search(self, query: str, city: str | None, max_pages: int) -> list[VacancyRow]:
        area = AREA_MAP.get(city.lower(), None) if city else None
        rows: list[VacancyRow] = []

        for page in range(max_pages):
            params: dict = {"text": query, "per_page": PER_PAGE, "page": page}
            if area:
                params["area"] = area

            data = self._get(f"{HH_API}/vacancies", params)
            items = data.get("items", [])
            total_pages = data.get("pages", 1)

            for item in items:
                salary = item.get("salary") or {}
                rows.append(VacancyRow(
                    external_id=str(item.get("id", "")),
                    title=item.get("name", ""),
                    salary_from=salary.get("from"),
                    salary_to=salary.get("to"),
                    currency=salary.get("currency"),
                    location=(item.get("area") or {}).get("name", ""),
                    url=item.get("alternate_url"),
                ))

            if page >= total_pages - 1 or not items:
                break
            time.sleep(random.uniform(*DELAY))

        return rows
