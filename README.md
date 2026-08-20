# ⏳ 틈틈 (TeumTeum) — Backend

**남는 공백시간을, 나를 챙기는 시간으로.**

2026 동국대학교 멋쟁이사자처럼 중앙해커톤 Team 3 (TeumTeum) Backend
|
---

## 💡 서비스 소개

사용자가 지금 남은 시간, 있는 장소, 원하는 회복 방식, 다음 일정, 현재 상태를 입력하면, AI가 실제 콘텐츠 길이(영상 재생 시간·활동 소요 시간)를 초 단위로 계산해서 그 시간 안에 정확히 끝나는 웰니스 코스를 구성해주는 서비스입니다.

- **시간 기반 코스 생성**: 정해진 길이의 콘텐츠에 사용자를 맞추는 게 아니라, 사용자의 남은 시간에 콘텐츠를 맞춰서 조합합니다.
- **상황 기반 추천**: 장소, 회복 방식 선호, 현재 상태, 다음 일정을 종합해 활동 모듈·아티클·유튜브 콘텐츠 중 우선순위를 정합니다.
- **콘텐츠 공유 학습**: 다른 앱에서 공유받은 유튜브 링크를 AI가 회복 방식으로 자동 분류해, 다음 코스 추천에 반영합니다.
- **틈 기록**: 완료한 코스와 이번 주/지난 주 사용 시간을 비교하고, 가장 자주 선택한 회복 방식과 완료율이 높은 시간대를 분석합니다.

---

## 🤖 AI 활용

틈틈의 AI는 콘텐츠를 추천하는 데서 끝나지 않습니다.

**① 시간 기반 콘텐츠 생성**

남은 시간을 기준으로, 실제 콘텐츠 길이를 초 단위까지 계산해서 그 시간에 최대한 가깝게 맞는 조합을 찾습니다.

```
사용자 입력
남은 시간: 15분 / 현재 상태: 피곤함 / 현재 장소: 지하철 / 다음 일정: 친구와 약속

AI 구성
2분 스트레칭 가이드 + 5분 편안한 읽기 + 8분 관련 유튜브 콘텐츠
= 총 15분
```

(다음 일정 준비 질문은 위처럼 딱 맞는 활동 모듈이 이미 배정된 경우에는 들어가지 않고, 그런 모듈이 없을 때만 대신 들어가는 별도 구성입니다.)

중간에 마음에 안 드는 콘텐츠는 건너뛸 수 있고, 건너뛴 만큼의 시간은 사용 기록에 포함하지 않습니다. 그렇게 마지막 콘텐츠까지 도달했다면, 설정한 시간이 다 지나지 않았더라도 완료 처리됩니다.

**② 상황 기반 코스 추천**

남은 시간, 회복 방식 선호, 현재 장소, 기분·피로도, 다음 일정을 종합해서 지금 가장 필요한 활동을 우선 추천합니다.

---

## 🔐 인증 방식

로그인·회원가입이 없는 게스트 UUID 기반 서비스입니다.

- 첫 접속 시 클라이언트가 UUID를 발급받아 보관하고, 이후 모든 요청에 `guest_uuid`를 실어 보냅니다.
- `teumteum` / `records` / `magazines` 계열 API는 body 또는 query parameter의 `guest_uuid`로 사용자를 식별하고, 모든 조회·수정은 해당 유저 소유 데이터로만 스코프됩니다.
- `/accounts/me`만 별도로 `X-Guest-ID` 헤더 기반 인증(`GuestAuthentication`)을 쓰며, 최초 접속 시 유저를 자동으로 생성합니다.

---

## ✨ 핵심 기능

| 기능 | 설명 |
|---|---|
| ⏱️ 공백시간 설정 | 5~30분 사이, 슬라이더로 남은 시간을 설정 |
| 🤖 AI 코스 생성 | 실제 콘텐츠 길이를 초 단위로 계산해 남은 시간에 최대한 가깝게 맞는 조합 선택 |
| 🧠 읽기 · 🎧 듣기 | AI가 재구성한 글, 호흡 오디오 가이드, 관련 유튜브 콘텐츠 |
| 🧘 스트레칭 | 부위별 스트레칭 가이드 및 관련 유튜브 콘텐츠 |
| 🪞 마음 정리 | 질문에 답하며 생각을 정리하는 콘텐츠 |
| ✨ 다음 준비-틈 | 딱 맞는 활동 모듈이 없을 때, 다음 일정에 맞춘 AI 준비 질문으로 대체 |
| ⏭️ 스킵 | 콘텐츠를 건너뛸 수 있고, 실제 사용한 시간만 기록. 마지막 콘텐츠까지 도달하면 시간이 남아도 완료 처리 |
| 🔗 콘텐츠 공유 학습 | PWA 공유 대상으로 받은 유튜브 링크를 AI가 회복 방식으로 자동 분류, 분류 실패 시 다음 코스 생성 때 재시도 |
| 📊 틈 기록 | 완료 코스, 이번 주·지난 주 비교, 자주 쓴 회복 방식·시간대 분석 |
| 📰 발견 탭 | 관심사 기반 AI 웰니스 아티클 추천 |

---

## 📡 API 엔드포인트

### teumteum (`/`)

| Method | URL | 설명 |
|---|---|---|
| GET / POST | `/main` | 게스트 유저 조회 / 공백시간(`target_minutes`) 설정 |
| GET / POST | `/main/questions` | 메인 질문 목록 조회 / 답변 제출(장소·회복방식·다음일정·현재상태) |
| POST | `/main/teumteum` | 코스 생성 |
| POST | `/main/teumteum/refresh` | 코스 새로고침(재추천) |
| POST | `/main/teumteum/{course_id}` | 코스 실행 시작 |
| POST | `/main/teumteum/{execution_id}/pause` | 일시정지 |
| POST | `/main/teumteum/{execution_id}/resume` | 재개 |
| POST | `/main/teumteum/{execution_id}/skip` | 현재 콘텐츠 건너뛰기 |
| POST | `/main/teumteum/{execution_id}/stop` | 중단 |
| POST | `/main/teumteum/{execution_id}/complete` | 완료 처리(기록 저장) |
| POST | `/main/teumteum/{execution_id}/rate` | 만족도 평가 |
| POST | `/main/share` | 유튜브 링크 공유 → AI 회복방식 분류 |
| GET | `/mypage/weekly-usage` | 주간 누적 사용 시간 |

### accounts / mypage

| Method | URL | 설명 |
|---|---|---|
| GET | `/accounts/me` | 게스트 유저 확인(자동 생성), 헤더 인증 |
| GET | `/mypage` | 마이페이지 AI 개인화 분석(이번 주/지난 주 비교, 자주 쓴 회복 방식·장소·시간대) |

### onboarding (`/onboarding/`)

| Method | URL | 설명 |
|---|---|---|
| GET | `/onboarding/questions` | 온보딩 질문 목록 |
| POST | `/onboarding/` | 온보딩 답변 제출 |

### records (`/records/`)

| Method | URL | 설명 |
|---|---|---|
| GET | `/records/` | 완료 기록 목록 |
| GET | `/records/{record_id}` | 기록 상세(다시 실행) |

### magazines (`/magazines/`)

| Method | URL | 설명 |
|---|---|---|
| GET | `/magazines/` | 발견 탭 추천(관심사 기반) |
| GET | `/magazines/discovery/{article_id}` | 아티클 상세 + AI 추천 이유·한 줄 정리 |

---

## 📁 프로젝트 구조

| 앱 / 모듈 | 역할 |
|---|---|
| `teumteum` | 메인 질문, 코스 생성/실행, 활동 모듈·유튜브 더미 풀, 영상 공유 |
| `accounts` | 게스트 유저 식별, 마이페이지 통계 |
| `onboarding` | 최초 관심사·상황 온보딩 |
| `records` | 완료 기록 저장/조회 |
| `magazines` | 발견 탭 웰니스 아티클 추천 |
| `services` | OpenAI/YouTube 연동, 콘텐츠 조합 알고리즘 (앱이 아닌 공용 로직 모듈) |

---

## 🛠️ 로컬 개발 환경 실행

### 1. 프로젝트 클론 및 가상환경 설정

```bash
git clone https://github.com/LikeLion-at-DGU/2026-hackathon-TeumTeum-BE.git
cd 2026-hackathon-TeumTeum-BE

python -m venv venv
source venv\Scripts\activate   # Mac: venv/bin/activate

pip install -r requirements.txt
```

### 2. 환경 변수 설정

`main/.env` 파일을 생성한 후 아래 값을 채웁니다.

```env
SECRET_KEY=...
DEBUG=True
OPENAI_API_KEY=...
YOUTUBE_API_KEY=...
```

### 3. 마이그레이션 및 서버 실행

```bash
cd main

python manage.py migrate
# 마이그레이션에 포함된 시드 데이터
# 활동 모듈, 웰니스 원문, 유튜브 더미 풀, 질문도 같이 채워짐

python manage.py runserver
```

---

## 🧪 테스트

```bash
cd main

python manage.py check
pytest
```

현재 핵심 플로우(온보딩, 기록 접근 권한 등) 위주로 최소한의 테스트만 구성돼 있습니다. 커버리지 확대가 필요합니다.

---

## 🌐 배포

`main` 브랜치에 push되면 GitHub Actions가 Docker 이미지를 빌드해 GHCR(GitHub Container Registry)에 push하고, SSH로 Gabia 서버에 접속해 컨테이너를 재기동합니다.

`db.sqlite3`와 `media/`는 호스트 볼륨에 마운트되어 재배포해도 데이터가 유지됩니다.

- **CI/CD**: GitHub Actions
- **컨테이너**: Docker
- **이미지 레지스트리**: GHCR (GitHub Container Registry)
- **서버**: Gabia Ubuntu
- **웹 서버 / 리버스 프록시**: Nginx
- **애플리케이션 서버**: Gunicorn
- **데이터베이스**: SQLite

---
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.1-092E20?style=flat-square&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.18.0-A30000?style=flat-square)
![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat-square&logo=sqlite&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--5--mini-412991?style=flat-square&logo=openai&logoColor=white)
![YouTube](https://img.shields.io/badge/YouTube-Data%20API%20v3-FF0000?style=flat-square&logo=youtube&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Container-2496ED?style=flat-square&logo=docker&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-Reverse%20Proxy-009639?style=flat-square&logo=nginx&logoColor=white)

---
##무의식적인 숏폼 소비를 줄이고 공백시간을 실제 휴식 시간으로 바꾸는 것, 하루 10분이라도 자신을 챙기는 행동을 반복하며 웰니스에 대한 진입장벽을 낮추는 것, "오늘도 시간을 버렸다"가 아니라 "오늘 15분은 나를 위해 썼다"는 경험을 주는 것이 틈틈이 만들고 싶은 변화입니다.