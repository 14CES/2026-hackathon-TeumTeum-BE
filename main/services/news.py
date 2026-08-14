import math
import requests
from django.conf import settings


def get_news(query, max_results=5):
    url = "https://newsdata.io/api/1/latest"

    params = {
        "apikey": settings.NEWSDATA_API_KEY,
        "country": "kr",
        "language": "ko",
        "q": query,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    news_list = []


    for item in data.get("results", [])[:max_results]:
        description = item.get("description") or ""
        content = item.get("content") or ""

        # content가 있으면 content 기준, 없으면 description 기준
        if content == "ONLY AVAILABLE IN PAID PLANS":
            text = description
        else:
            text = content if content else description

        # 1분당 400자 기준, 최소 1분
        estimated_minutes = max(
            1,
            math.ceil(len(text) / 400)
        )

        news_list.append({
            "title": item.get("title"),
            "description": description,
            "content": text,
            "source": item.get("source_name"),
            "url": item.get("link"),
            "image_url": item.get("image_url"),
            "estimated_minutes": estimated_minutes,
        })

    return news_list