import requests
from django.conf import settings

def get_news():
    url = "https://newsdata.io/api/1/latest"

    params = {
        "apikey": settings.NEWSDATA_API_KEY,
        "country": "kr",
        "language": "ko",
    }

    response = requests.get(url, params=params)

    return response.json()