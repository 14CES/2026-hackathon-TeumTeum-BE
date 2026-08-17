from itertools import combinations
import random


YOUTUBE_CONTENT_TYPES = {
    "듣기",
    "스트레칭",
    "마음 정리",
}


def select_best_contents(
    article_contents,
    youtube_contents,
    content_types,
    target_minutes,
    total_count=3
):
    """
    사용자가 선택한 회복 방식(읽기/듣기/스트레칭/마음 정리)에 따라
    최종 콘텐츠 total_count개의 구성 비율을 결정하고,
    target_minutes에 가장 가까운 조합을 선택한다.

    total_count는 기본 3이지만, 활동 모듈(오디오가이드 등)이 이미
    한 자리를 차지한 경우 호출하는 쪽에서 2로 줄여서 넘긴다.

    읽기만
    -> 기사 total_count개 + 유튜브 0개

    읽기 + 유튜브 계열 1개
    -> 기사 (total_count-1)개 + 유튜브 1개

    읽기 + 유튜브 계열 2개 이상
    -> 기사 1개 + 유튜브 (total_count-1)개

    읽기 없이 유튜브 계열만
    -> 기사 0개 + 유튜브 total_count개
    """

    has_reading = "읽기" in content_types

    youtube_type_count = sum(
        content_type in YOUTUBE_CONTENT_TYPES
        for content_type in content_types
    )

    # 콘텐츠 비율 결정
    if has_reading:
        if youtube_type_count == 0:
            # 읽기만
            article_count = total_count
            youtube_count = 0

        elif youtube_type_count == 1:
            # 읽기 + 듣기 / 스트레칭 / 마음 정리 중 1개
            article_count = max(total_count - 1, 1)
            youtube_count = total_count - article_count

        else:
            # 읽기 + 유튜브 계열 2개 이상
            article_count = 1
            youtube_count = total_count - 1

    else:
        # 읽기 없이 듣기 / 스트레칭 / 마음 정리
        article_count = 0
        youtube_count = total_count

    # 후보 수 확인
    if len(article_contents) < article_count:
        return None

    if len(youtube_contents) < youtube_count:
        return None

    # 읽기 콘텐츠 조합
    if article_count == 0:
        article_combinations = [()]
    else:
        article_combinations = combinations(
            article_contents,
            article_count
        )

    # 유튜브 콘텐츠 조합
    if youtube_count == 0:
        youtube_combinations = [()]
    else:
        youtube_combinations = combinations(
            youtube_contents,
            youtube_count
        )

    best_combinations = []
    best_difference = None
    best_article_length = None

    # 가능한 모든 조합 비교
    for article_combination in article_combinations:
        for youtube_combination in youtube_combinations:

            contents = (
                list(article_combination)
                + list(youtube_combination)
            )

            # 최종 시간 배분이 가능한 조합인지 확인
            youtube_minutes = sum(
                content.get("original_estimated_minutes", 0)
                for content in youtube_combination
            )

            combination_article_count = len(article_combination)

            # 유튜브만으로 목표 시간을 초과하면 제외
            if youtube_minutes > target_minutes:
                continue

            # 기사마다 최소 1분을 배정할 수 있어야 함
            remaining_minutes = target_minutes - youtube_minutes

            if remaining_minutes < combination_article_count:
                continue

            total_minutes = sum(
                content.get("original_estimated_minutes", 0)
                for content in contents
            )

            difference = abs(
                total_minutes - target_minutes
            )

            # 선택된 기사들의 전체 원문 길이 (AI가 새로 쓸 자리는 원문이 없으므로 0으로 취급)
            article_length = sum(
                len(content.get("content") or "")
                for content in article_combination
            )

            if (
                best_difference is None
                or difference < best_difference
                or (
                    difference == best_difference
                    and article_length > best_article_length
                )
            ):
                best_difference = difference
                best_article_length = article_length
                best_combinations = [contents]

            elif (
                difference == best_difference
                and article_length == best_article_length
            ):
                best_combinations.append(contents)

    return random.choice(best_combinations) if best_combinations else None


# 전체 목표 시간(target_minutes)에 따른 추천 모듈 개수 범위 (최소, 최대)
# 오디오가이드/다음준비 같은 활동 모듈도 이 개수에 포함된다.
MODULE_COUNT_TABLE = [
    (5, 7, 1, 2),
    (8, 12, 2, 2),
    (13, 17, 2, 3),
    (18, 22, 3, 3),
    (23, 26, 3, 4),
    (27, 30, 4, 4),
]


def get_module_count_range(target_minutes):
    """
    target_minutes가 표의 어느 구간에 속하는지 찾아 (최소 개수, 최대 개수)를 반환한다.
    표 범위를 벗어나면 가장 가까운 쪽 경계값을 그대로 쓴다.
    """

    for min_minutes, max_minutes, min_count, max_count in MODULE_COUNT_TABLE:
        if min_minutes <= target_minutes <= max_minutes:
            return min_count, max_count

    if target_minutes < MODULE_COUNT_TABLE[0][0]:
        return MODULE_COUNT_TABLE[0][2], MODULE_COUNT_TABLE[0][3]

    return MODULE_COUNT_TABLE[-1][2], MODULE_COUNT_TABLE[-1][3]


def select_best_contents_in_range(
    article_contents,
    youtube_contents,
    content_types,
    target_minutes,
    min_count,
    max_count,
):
    """
    min_count~max_count 범위의 개수를 각각 select_best_contents로 시도해보고,
    target_minutes에 가장 가깝게 맞는 조합을 고른다. 시간 차이가 같으면 개수가 더 많은 쪽을 고른다.
    """

    best_contents = None
    best_diff = None

    for count in range(min_count, max_count + 1):
        contents = select_best_contents(
            article_contents=article_contents,
            youtube_contents=youtube_contents,
            content_types=content_types,
            target_minutes=target_minutes,
            total_count=count,
        )

        if contents is None:
            continue

        total_minutes = sum(
            content.get("original_estimated_minutes", 0)
            for content in contents
        )
        diff = abs(total_minutes - target_minutes)

        if (
            best_diff is None
            or diff < best_diff
            or (diff == best_diff and len(contents) > len(best_contents))
        ):
            best_diff = diff
            best_contents = contents

    return best_contents


def allocate_content_minutes(contents, target_minutes):
        """
        선택된 콘텐츠에 최종 시간을 배분한다.

        - YouTube: 실제 영상 길이를 유지
        - 기사: YouTube를 제외한 남은 시간을 균등 배분
        - 기사끼리 나누어 떨어지지 않으면 앞쪽 기사에 1분씩 추가
        """

        youtube_contents = []
        article_contents = []

        for content in contents:
            if "source" in content:
                article_contents.append(content)
            else:
                youtube_contents.append(content)

        # YouTube 실제 영상 시간 합계
        youtube_minutes = sum(
            content.get("estimated_minutes", 0)
            for content in youtube_contents
        )

        # YouTube만으로 이미 목표 시간을 초과하면 배분 불가능
        if youtube_minutes > target_minutes:
            return None

        # 기사에 배분할 시간
        remaining_minutes = target_minutes - youtube_minutes

        # 기사 없이 YouTube만 있는 경우
        if not article_contents:
            return contents

        # 기사 수보다 남은 시간이 적으면
        # 각 기사에 최소 1분을 줄 수 없으므로 실패
        if remaining_minutes < len(article_contents):
            return None

        # 기사별 기본 시간
        base_minutes = remaining_minutes // len(article_contents)

        # 나머지 1분
        remainder = remaining_minutes % len(article_contents)

        # 기사 시간 배분
        for index, content in enumerate(article_contents):
            allocated_minutes = base_minutes

            if index < remainder:
                allocated_minutes += 1

            content["estimated_minutes"] = allocated_minutes

        return contents


def select_activity_module(current_state, situation, remaining_minutes, exclude_ids=None):
    """
    현재 상태·장소·남은 시간에 맞는 활동 모듈 템플릿(호흡/스트레칭/마음정리/피부체크)을
    하나 선택한다. current_state와 겹치는 태그가 많은 템플릿을 우선하고,
    동점이면 무작위로 고른다. 맞는 템플릿이 없으면 None을 반환한다.
    """

    from teumteum.models import ActivityModuleTemplate

    exclude_ids = exclude_ids or []

    candidates = ActivityModuleTemplate.objects.filter(
        is_active=True,
        estimated_minutes__lte=remaining_minutes,
    ).exclude(id__in=exclude_ids)

    scored = []

    for template in candidates:

        # 장소 제한이 있는데 현재 장소가 해당되지 않으면 제외
        if template.allowed_contexts and situation not in template.allowed_contexts:
            continue

        tag_matches = len(set(template.tags) & set(current_state))
        scored.append((tag_matches, template))

    if not scored:
        return None

    best_score = max(score for score, _ in scored)
    best_templates = [
        template for score, template in scored
        if score == best_score
    ]

    return random.choice(best_templates)
