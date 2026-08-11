# Git Convention

## Branch

- main : 최종 배포
- develop : 개발 통합
- feature : 기능 개발

### Branch Naming

feature/기능명

예시:
- feature/login
- feature/signup
- feature/mypage

---

## Commit

### Commit Message

type: 작업 내용

### Type

- feat : 새로운 기능 추가
- fix : 코드 수정 및 개선
- docs : 문서 수정
- test : 테스트 코드
- chore : 기타 작업

### Example

feat: 로그인 기능 구현
fix: 회원가입 오류 수정
docs: README 수정

---

## Pull Request

- 각자 Repository를 Fork하여 작업
- feature 브랜치에서 작업
- 작업 완료 후 원본 Repository의 develop 브랜치로 Pull Request
- 코드 리뷰 후 Merge

### PR Title

[Type] 작업 내용

예시:
[feat] 로그인 기능 구현
[fix] 회원가입 오류 수정

---

## Rule

- main 직접 Push 금지
- develop 직접 Push 금지
- 모든 기능은 Pull Request를 통해 Merge