from itertools import combinations


YOUTUBE_CONTENT_TYPES = {
    "듣기",
    "스트레칭",
    "마인드컨트롤",
}


def select_best_contents(
    news_contents,
    youtube_contents,
    content_types,
    target_minutes
):
    """
    사용자가 선택한 콘텐츠 유형에 따라
    최종 콘텐츠 3개의 구성 비율을 결정하고,
    target_minutes에 가장 가까운 조합을 선택한다.

    독서만
    -> 읽기 3개 + 유튜브 0개

    독서 + 유튜브 1개
    -> 읽기 2개 + 유튜브 1개

    독서 + 유튜브 2개 이상
    -> 읽기 1개 + 유튜브 2개

    독서 없이 유튜브만
    -> 읽기 0개 + 유튜브 3개
    """

    has_reading = "독서" in content_types

    youtube_type_count = sum(
        content_type in YOUTUBE_CONTENT_TYPES
        for content_type in content_types
    )

    # 콘텐츠 비율 결정
    if has_reading:
        if youtube_type_count == 0:
            # 독서만
            news_count = 3
            youtube_count = 0

        elif youtube_type_count == 1:
            # 독서 + 듣기 / 스트레칭 / 마인드컨트롤 중 1개
            news_count = 2
            youtube_count = 1

        else:
            # 독서 + 유튜브 계열 2개 이상
            news_count = 1
            youtube_count = 2

    else:
        # 독서 없이 듣기 / 스트레칭 / 마인드컨트롤
        news_count = 0
        youtube_count = 3

    # 후보 수 확인
    if len(news_contents) < news_count:
        return None

    if len(youtube_contents) < youtube_count:
        return None

    # 읽기 콘텐츠 조합
    if news_count == 0:
        news_combinations = [()]
    else:
        news_combinations = combinations(
            news_contents,
            news_count
        )

    # 유튜브 콘텐츠 조합
    if youtube_count == 0:
        youtube_combinations = [()]
    else:
        youtube_combinations = combinations(
            youtube_contents,
            youtube_count
        )

    best_combination = None
    best_difference = None

    # 가능한 모든 조합 비교
    for news_combination in news_combinations:
        for youtube_combination in youtube_combinations:

            contents = (
                list(news_combination)
                + list(youtube_combination)
            )

            total_minutes = sum(
                content.get("estimated_minutes", 0)
                for content in contents
            )

            difference = abs(
                total_minutes - target_minutes
            )

            # 가장 가까운 조합 선택
            if (
                best_difference is None
                or difference < best_difference
            ):
                best_difference = difference
                best_combination = contents

                # 정확히 목표 시간과 같으면 즉시 종료
                if difference == 0:
                    return best_combination

    return best_combination


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