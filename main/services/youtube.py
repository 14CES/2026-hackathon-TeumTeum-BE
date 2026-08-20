import math
import re
import requests
from urllib.parse import urlparse, parse_qs
from django.conf import settings


def parse_duration(duration):
    # 초 단위 정확한 길이를 반환한다 (분 단위 올림은 호출하는 쪽에서 표시용으로 따로 계산한다)

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

    return max(1, total_seconds)


def search_youtube(query, max_results=5):

    # 1. 영상 검색
    search_url = "https://www.googleapis.com/youtube/v3/search"

    search_params = {
        "key": settings.YOUTUBE_API_KEY,
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        # 필터가 아니라 순위 가산점이라, 한글+영어 섞인 국내 채널도 그대로 잡힌다.
        # 이게 없으면 일본어 등 관련 없는 나라 영상이 섞여 나오는 경우가 있었다.
        "regionCode": "KR",
        "relevanceLanguage": "ko",
    }

    try:
        response = requests.get(
            search_url,
            params=search_params,
            timeout=5
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"유튜브 검색 실패 (검색어: {query}):", e)
        return []

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

    duration_map = {}

    try:
        response = requests.get(
            videos_url,
            params=videos_params,
            timeout=5
        )
        response.raise_for_status()
        duration_data = response.json()

        duration_map = {
            item["id"]: parse_duration(
                item["contentDetails"]["duration"]
            )
            for item in duration_data.get("items", [])
        }
    except requests.exceptions.RequestException as e:
        # 길이 조회만 실패한 경우 -> 검색 결과는 살리고 기본 1분으로 처리
        print(f"유튜브 영상 길이 조회 실패 (검색어: {query}):", e)

    # 3. 검색 결과 + 영상 길이 합치기
    videos = []

    for item in data.get("items", []):

        video_id = item["id"]["videoId"]

        # 실제 초 단위 길이 (6분 14초처럼 정확한 값) -> 코스 조합 매칭에서 정밀도를 위해 그대로 들고 다닌다
        duration_seconds = duration_map.get(
            video_id,
            60
        )

        # 화면 표시/시간 배분용 분 단위 (올림 처리)
        original_estimated_minutes = math.ceil(duration_seconds / 60)

        videos.append({
            "video_id": video_id,
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "thumbnail": item["snippet"]["thumbnails"]["medium"]["url"],
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "duration_seconds": duration_seconds,
            "original_estimated_minutes": original_estimated_minutes,
            "estimated_minutes": original_estimated_minutes,
        })

    return videos


def extract_youtube_video_id(url):
    """
    유튜브 URL 여러 형태(youtu.be/ID?si=..., youtube.com/watch?v=ID,
    youtube.com/shorts/ID, m.youtube.com/watch?v=ID, youtube.com/embed/ID)에서
    video_id만 뽑아낸다. 유튜브 URL이 아니거나 못 찾으면 None을 반환한다.
    """

    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    host = (parsed.hostname or "").lower()

    if "youtube.com" in host:
        if parsed.path == "/watch":
            video_ids = parse_qs(parsed.query).get("v")
            return video_ids[0] if video_ids else None

        for prefix in ("/shorts/", "/embed/"):
            if parsed.path.startswith(prefix):
                candidate = parsed.path[len(prefix):].split("/")[0]
                return candidate or None

        return None

    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
        return candidate or None

    return None


def get_youtube_video_info(video_id):
    """
    이미 알고 있는 video_id 하나의 메타데이터(제목/채널/썸네일/길이)를 조회한다.
    비공개/삭제된 영상 등으로 못 찾으면 None을 반환한다.
    """

    videos_url = "https://www.googleapis.com/youtube/v3/videos"

    params = {
        "key": settings.YOUTUBE_API_KEY,
        "part": "snippet,contentDetails",
        "id": video_id,
    }

    try:
        response = requests.get(videos_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"유튜브 영상 정보 조회 실패 (video_id: {video_id}):", e)
        return None

    items = data.get("items", [])

    if not items:
        return None

    item = items[0]
    duration_seconds = parse_duration(item["contentDetails"]["duration"])

    return {
        "video_id": video_id,
        "title": item["snippet"]["title"],
        "channel_name": item["snippet"]["channelTitle"],
        "thumbnail_url": item["snippet"]["thumbnails"]["medium"]["url"],
        "duration_seconds": duration_seconds,
        "estimated_minutes": math.ceil(duration_seconds / 60),
    }