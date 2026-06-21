import random
import time

import requests

from app.config import settings
from app.sources.base import BaseSource, VacancyRow

SJ_API = "https://api.superjob.ru/2.0"
PER_PAGE = 100
DELAY = (2.0, 4.0)


class SJSource(BaseSource):
    name = "sj"

    def _get(self, url: str, params: dict | None) -> dict:
        if not settings.sj_api_key:
            raise RuntimeError("SJ_API_KEY не задан в .env")
        headers = {
            "X-Api-App-Id": settings.sj_api_key,
            "User-Agent": "HR-Scoring-Tool/1.0",
            "Accept": "application/json",
        }
        for attempt in range(4):
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=15)
                if resp.status_code == 429:
                    time.sleep(15 * (2 ** attempt))
                    continue
                if resp.status_code in {401, 403}:
                    raise RuntimeError("SuperJob: ключ недействителен. Проверь SJ_API_KEY в .env.")
                resp.raise_for_status()
                return resp.json()
            except requests.Timeout:
                time.sleep(5 * (2 ** attempt))
            except requests.ConnectionError as e:
                if attempt == 3:
                    raise RuntimeError(f"Нет соединения с api.superjob.ru: {e}") from e
                time.sleep(5)
        raise RuntimeError("SuperJob: превышено число попыток.")

    def search(self, query: str, city: str | None, max_pages: int) -> list[VacancyRow]:
        rows: list[VacancyRow] = []

        for page in range(max_pages):
            params: dict = {"keyword": query, "count": PER_PAGE, "page": page}
            if city:
                params["town"] = city

            data = self._get(f"{SJ_API}/vacancies/", params)
            items = data.get("objects", [])
            has_more = data.get("more", False)

            for item in items:
                rows.append(VacancyRow(
                    external_id=str(item.get("id", "")),
                    title=item.get("profession", ""),
                    salary_from=item.get("payment_from") or None,
                    salary_to=item.get("payment_to") or None,
                    currency=item.get("currency"),
                    location=(item.get("town") or {}).get("title", ""),
                    url=item.get("link"),
                ))

            if not has_more or not items:
                break
            time.sleep(random.uniform(*DELAY))

        return rows
