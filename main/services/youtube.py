import requests
from django.conf import settings


def search_youtube(query, max_results=3):
    url = "https://www.googleapis.com/youtube/v3/search"

    params = {
        "key": settings.YOUTUBE_API_KEY,
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()

    videos = []

    for item in data.get("items", []):
        video_id = item["id"]["videoId"]

        videos.append({
            "video_id": video_id,
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
            "url": f"https://www.youtube.com/watch?v={video_id}",
        })

    return videos