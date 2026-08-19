# 1. 파이썬 실행 환경 지정
FROM python:3.12-slim

# 2. 컨테이너 시스템 시계를 한국 시간으로 맞추기
# (settings.py의 USE_TZ=False는 컨테이너 OS 시계를 그대로 쓰기 때문에,
#  이 설정이 없으면 기본 UTC로 떠서 실제 시각보다 9시간 느리게 찍힘)
RUN apt-get update && apt-get install -y tzdata && \
    ln -sf /usr/share/zoneinfo/Asia/Seoul /etc/localtime && \
    rm -rf /var/lib/apt/lists/*
ENV TZ=Asia/Seoul

# 3. 컨테이너 내부 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 4. 컨테이너 내부에서 코드가 작동할 폴더(작업 디렉토리) 생성 및 이동
WORKDIR /app

# 5. 필수 패키지 설치를 위해 requirements.txt 복사 및 설치
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 6. 배포용 WSGI 서버인 gunicorn 설치
RUN pip install gunicorn

# 7. 내 컴퓨터의 장고 프로젝트 소스코드를 컨테이너 내부로 전부 복사
COPY . /app/

# 8. DJango는 8000번 포트에서 실행되므로 8000으로 포트번호 맞추기
EXPOSE 8000

# 9. 컨테이너가 켜졌을 때 장고를 실행할 최종 명령어
# collectstatic/migrate는 SECRET_KEY 등 실제 환경변수가 필요해서 빌드 시점이 아니라
# 컨테이너 실행 시점(런타임 env가 주입된 후)에 돌려야 한다.
# migrate를 먼저 돌려야 마이그레이션에 들어있는 시드 데이터(웰니스 원문, 활동모듈,
# 유튜브 더미풀, 질문 등)가 배포 DB에도 채워진다. 이미 적용된 마이그레이션은
# 다시 실행해도 아무 일도 안 하므로 매번 실행해도 안전하다.
# 현재 프로젝트 명이 project가 맞는지 반드시 확인!!!
# 코스 생성 API가 OpenAI/YouTube를 여러 번 호출해서 30초를 넘길 수 있는데,
# gunicorn 워커 기본 타임아웃이 30초라 그보다 오래 걸리면 워커가 강제 종료되고
# nginx에는 502로 보임 -> 타임아웃을 넉넉하게 늘려준다.
CMD ["sh", "-c", "python main/manage.py migrate --noinput && python main/manage.py collectstatic --noinput && gunicorn --chdir main main.wsgi:application --bind 0.0.0.0:8000 --timeout 120"]