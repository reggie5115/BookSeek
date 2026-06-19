# 📚 BookSeek — 도서 추천 플랫폼

읽은 책에 점수를 매기면, 취향에 맞는 책을 추천해주는 데스크톱 프로그램.
오픈 라이브러리에서 책 정보를 가져오고, 추천된 책을 AI 사서가 소개해준다.

> ○○대학교 / ○○○ 과목 팀 프로젝트

## 팀 분업

| 담당 | 파일 |
|------|------|
| 데이터 (팀원 A) | `core/database.py`, `core/openlibrary.py` |
| 추천 알고리즘 (팀원 B) | `core/recommender.py` |
| UI / 챗봇 (팀원 C) | `gui/*`, `core/chatbot.py` |
| 공통 | `core/app_controller.py`, `main.py` |

## 실행

```
python main.py
```

- 파이썬 3.8 이상 (Tkinter 포함, 보통 기본 설치됨)
- 처음 실행하면 인터넷에서 책을 받아온다 (10~20초)
- 리눅스에서 Tkinter 오류 시: `sudo apt install python3-tk`

## 사용법

1. **서재** — 읽은 책을 찾아 평가(0~10점)
2. **내 평점** — 매긴 점수 확인
3. **추천** — '추천 받기' → AI 사서가 소개
4. **책 추가** — 없는 책은 제목으로 검색해 추가

평점을 몇 권 매기면 추천이 정확해진다. (싫어한 책도 낮은 점수로!)

## 추천 원리

책을 벡터로 바꾸고(장르·분위기), 평점으로 '취향 벡터'를 만든 뒤,
안 읽은 책과의 코사인 유사도로 가장 비슷한 책을 추천한다.

## 사용 기술

Python 표준 라이브러리(tkinter, sqlite3, urllib) + Open Library API(무료).
챗봇은 ANTHROPIC_API_KEY가 있으면 Claude, 없으면 내장 사서 사용.
