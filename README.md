# 📰 FastAPI 기반 뉴스 요약 RAG 서비스

## 🧩 사용 기술

| 구성 요소       | 역할                             |
|----------------|----------------------------------|
| **Flutter**     | 검색 UI / 결과 요약 표시           |
| **FastAPI**     | 백엔드 API / 벡터 검색 및 요약 수행 |
| **Langchain**   | 검색 질의에 따른 RAG 흐름 구성     |
| **ChromaDB**    | 뉴스 벡터 저장 및 유사도 검색       |
| **OpenAI GPT**  | 뉴스 기사 본문 요약 생성           |
| **Naver API**   | 뉴스 데이터 실시간 수집             |


---

## 🚀 실행 방법

### 1. 설정

```bash
# 필수 패키지 설치
pip install -r requirements.txt

# .env 파일 설정
NAVER_CLIENT_ID=네이버_API_클라이언트_ID
NAVER_CLIENT_SECRET=네이버_API_시크릿
OPENAI_API_KEY=OpenAI_API_키
```

### 2. 실행
```bash
# 서버 실행
uvicorn app.main:app --reload

# 뉴스 수집 및 저장
GET /collect-and-store?keyword=IT&total=100

# 키워드 기반 뉴스 검색 및 요약
GET /chat?query=AI 반도체&journal=연합뉴스

GET /keyword-summary?keyword=전지훈련
```