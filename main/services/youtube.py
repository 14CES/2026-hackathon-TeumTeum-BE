import re
import requests
from django.conf import settings


def parse_duration(duration):

    hours = 0
    minutes = 0
    seconds = 0

    hour_match = re.search(r"(\d+)H", duration)
    minute_match = re.search(r"(\d+)M", duration)
    second_match = re.search(r"(\d+)S", duration)

    if hour_match:
        hours = int(hour_match.group(1))

    if minute_match:
        minutes = int(minute_match.group(1))

    if second_match:
        seconds = int(second_match.group(1))

    total_seconds = (
        hours * 3600
        + minutes * 60
        + seconds
    )

    # 초가 있으면 올림
    return max(1, (total_seconds + 59) // 60)


def search_youtube(query, max_results=5):

    # 1. 영상 검색
    search_url = "https://www.googleapis.com/youtube/v3/search"

    search_params = {
        "key": settings.YOUTUBE_API_KEY,
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
    }

    response = requests.get(
        search_url,
        params=search_params
    )
    response.raise_for_status()

    data = response.json()

    video_ids = [
        item["id"]["videoId"]
        for item in data.get("items", [])
    ]

    if not video_ids:
        return []

    # 2. 실제 영상 길이 조회
    videos_url = "https://www.googleapis.com/youtube/v3/videos"

    videos_params = {
        "key": settings.YOUTUBE_API_KEY,
        "part": "contentDetails",
        "id": ",".join(video_ids),
    }

    response = requests.get(
        videos_url,
        params=videos_params
    )
    response.raise_for_status()

    duration_data = response.json()

    # video_id별 영상 길이 저장
    duration_map = {
        item["id"]: parse_duration(
            item["contentDetails"]["duration"]
        )
        for item in duration_data.get("items", [])
    }

    # 3. 검색 결과 + 영상 길이 합치기
    videos = []

    for item in data.get("items", []):
        video_id = item["id"]["videoId"]

        videos.append({
            "video_id": video_id,
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "estimated_minutes": duration_map.get(video_id, 1),
        })

    return videos