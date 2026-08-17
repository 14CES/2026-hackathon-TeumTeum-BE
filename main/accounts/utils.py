from collections import Counter
from records.models import Record

# 5가지 DNA 유형 메타데이터
DNA_TYPES = {
    "NEWS": {
        "type": "인간 레이더",
        "description": "세상 돌아가는 일 다 꿰뚫는 정보통 DNA",
        "lines": [
            "공백시간 10분 만에 시사 상식 섭취 완료!",
            "친구들 사이에서 걸어 다니는 백과사전",
            "숏폼 끊고 알짜 뉴스만 쏙쏙 골라 먹는 효율파"
        ]
    },
    "ASMR": {
        "type": "유리멘탈 보호구역",
        "description": "작은 소음도 빗소리로 지워내는 고요 DNA",
        "lines": [
            "장작 타는 소리면 세상 피로 1초 컷!",
            "에어팟 꽂는 순간 나만의 고요한 요새 완성",
            "도파민 과부하? 무소음 힐링으로 가볍게 리셋!"
        ]
    },
    "MUSIC": {
        "type": "방구석 디제이",
        "description": "내 삶의 BGM은 내가 직접 정하는 감성 DNA",
        "lines": [
            "길거리 걷는 5분도 영화 속 한 장면으로 변신!",
            "뇌 휴식 사운드로 머릿속 감성 충전 100%",
            "비트와 멜로디 없인 일상 리셋이 안 되는 사람"
        ]
    },
    "MAGAZINE": {
        "type": "감성 수집가",
        "description": "자투리 시간도 화보처럼 읽어내는 매거진 DNA",
        "lines": [
            "숏폼 스크롤 대신 깊이 있는 한 줄 에세이 탐독!",
            "남들 멍때릴 때 취향과 영감을 차곡차곡 수집",
            "자투리 시간에 감각부터 챙기는 진짜 힙스터"
        ]
    },
    "STRETCH": {
        "type": "연체동물",
        "description": "유연함이 남다른 연체동물 DNA",
        "lines": [
            "어디에서든 유연함을 뽐내는 사람!",
            "건강전도사가 바로 당신?",
            "거북목이 뭐야? 당장 고쳐줄게!"
        ]
    }
}

def calculate_user_dna(user):
    """
    유저의 Record 이력을 분석하여 가장 많이 이용한 DNA 유형을 반환합니다.
    """
    # 사용자가 완료한 코스 기록 카테고리 조회
    records = Record.objects.filter(user=user)
    
    if not records.exists():
        dna_info = DNA_TYPES["STRETCH"]
    else:
        # 카테고리별 수행 횟수 카운트
        categories = [r.category for r in records if r.category]
        if categories:
            most_common_cat = Counter(categories).most_common(1)[0][0]
            cat_map = {
                'NEWS': 'NEWS',
                'ASMR': 'ASMR',
                'MUSIC': 'MUSIC',
                'MAGAZINE': 'MAGAZINE',
                'BODY': 'STRETCH',
                'STRETCH': 'STRETCH',
                'MIND': 'ASMR'
            }
            target_key = cat_map.get(most_common_cat, "STRETCH")
            dna_info = DNA_TYPES.get(target_key, DNA_TYPES["STRETCH"])
        else:
            dna_info = DNA_TYPES["STRETCH"]

    return {
        "type": dna_info["type"],
        "description": dna_info["description"]
    }