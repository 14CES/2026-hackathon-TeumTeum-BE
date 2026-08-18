# 1. 파이썬 실행 환경 지정
FROM python:3.12-slim

# 2. 컨테이너 내부 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. 컨테이너 내부에서 코드가 작동할 폴더(작업 디렉토리) 생성 및 이동
WORKDIR /app

# 4. 필수 패키지 설치를 위해 requirements.txt 복사 및 설치
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 5. 배포용 WSGI 서버인 gunicorn 설치
RUN pip install gunicorn

# 6. 내 컴퓨터의 장고 프로젝트 소스코드를 컨테이너 내부로 전부 복사
COPY . /app/

# 7. 정적 파일을 한 곳에 모으기
RUN python main/manage.py collectstatic --noinput

# 8. DJango는 8000번 포트에서 실행되므로 8000으로 포트번호 맞추기
EXPOSE 8000

# 9. 컨테이너가 켜졌을 때 장고를 실행할 최종 명령어
# 현재 프로젝트 명이 project가 맞는지 반드시 확인!!!
CMD ["gunicorn", "--chdir", "main", "main.wsgi:application", "--bind", "0.0.0.0:8000"]