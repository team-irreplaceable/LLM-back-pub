from fastapi import FastAPI, Query, HTTPException
from app.summarizer import summarize_top_articles_by_keyword2, summarize_top_articles_by_keyword, summarize_url_article, generate_news_expert_reply_with_llm
from app.embedding_store import store_to_chroma, search_similar_news
from apscheduler.schedulers.background import BackgroundScheduler
from app.naver_news import fetch_news
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Union
from dotenv import load_dotenv
import os
import traceback

# .env 파일 로드
load_dotenv()

app = FastAPI()
# .env 파일 로드
load_dotenv()

app = FastAPI()


@app.get("/keyword-summary")
def keyword_summary(keywords: Union[List[str], str] = Query(..., description="키워드 목록")):
    """
    여러 키워드에 대해 각각 유사 기사 4개를 요약해 반환합니다. (병렬 처리 적용)
    """

    def process_keyword(keyword: str):
        try:
            articles = summarize_top_articles_by_keyword2(keyword, top_k=4)
            return {"keyword": keyword, "articles": articles}
        except Exception as e:
            print(f"[ERROR] 키워드 '{keyword}' 처리 실패: {e}")
            return {"keyword": keyword, "error": "요약 실패"}

    try:
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(process_keyword, keywords))

        return {"results": results}

    except Exception as e:
        print("[ERROR]", traceback.format_exc())
        raise HTTPException(status_code=500, detail="요약 처리 중 오류 발생")

# 기사 수집 스케줄러
def scheduled_job():
    keywords = ["경제", "IT"]
    try:
        news = fetch_news(100, keywords)
        store_to_chroma(news)
        print(f"[✅ 스케줄링 완료] {len(news)}개의 뉴스 저장 완료")
    except Exception:
        print("[ERROR - SCHEDULED JOB]", traceback.format_exc())


# 스케줄러 인스턴스 생성 및 시작
scheduler = BackgroundScheduler()
# 매일 오전 9시에 실행
scheduler.add_job(scheduled_job, 'cron', hour=9, minute=0)
scheduler.start()

# 기사 수집 api 
@app.get("/collect-and-store")
def collect_and_store_news(total: int = 100):
    """
    네이버 뉴스 API로 뉴스 수집 후 ChromaDB에 저장합니다.
    """
    keywords = [
       "경제", "IT"
    ]
    try:
        news = fetch_news(total, keywords)
        store_to_chroma(news)
        return {
            "stored_count": len(news),
            "message": f"{len(news)}개의 기사를 저장했습니다."
        }
    except Exception as e:
        print("[ERROR]", traceback.format_exc())
        raise HTTPException(status_code=500, detail="뉴스 수집 또는 저장 중 오류 발생")


@app.get("/search")
def search_news(query: str = Query(..., min_length=2)):
    """
    사용자의 질문에 대해 유사한 뉴스 5개를 RAG 방식으로 검색하고 요약 결과를 반환합니다.
    """
    try:
        docs = search_similar_news(query)
        results = []

        for doc in docs:
            title = doc.metadata.get("title", "제목 없음")
            link = doc.metadata.get("link", "")
            summary = summarize_url_article(link)
            results.append({
                "title": title,
                "url": link,
                "summary": summary
            })

        return {
            "query": query,
            "results": results  # [{ title, url, summary }, ...]
        }

    except Exception as e:
        print("[ERROR]", traceback.format_exc())
        raise HTTPException(status_code=500, detail="유사 뉴스 검색 또는 요약 중 오류 발생")


@app.get("/chat")
def chat(query: str = Query(..., min_length=2, description="질문 내용"),
         journal: Optional[str] = Query(None, description="특정 언론사만 필터링 (예: 중앙일보)")):
    """
    뉴스 전문가로서 질문에 대해 LLM 기반 답변과 함께 참조 기사들을 JSON 형태로 반환합니다.
    """
    try:
        answer, references = generate_news_expert_reply_with_llm(query, journal=journal)
        return {
            "query": query,
            "answer": answer,
            "references": references
        }
    except Exception as e:
        print("[ERROR]", traceback.format_exc())
        raise HTTPException(status_code=500, detail="뉴스 전문가 답변 생성 중 오류 발생")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)