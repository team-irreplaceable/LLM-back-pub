import json
from pathlib import Path
from typing import List, Dict, Optional
from app.embedding_store import search_similar_news
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import httpx
from bs4 import BeautifulSoup

from langchain_community.chat_models import ChatOpenAI as CommunityChatOpenAI
from langchain_openai import ChatOpenAI as OpenAIChat
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.chains.summarize import load_summarize_chain
from langchain.schema import Document

from app import config

# ✅ HuggingFace 임베딩 모델
embedder = HuggingFaceEmbeddings(model_name="jhgan/ko-sbert-nli")

# ✅ 키워드 기반 뉴스 요약용 LLM 체인
llm_keyword = CommunityChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0,
    openai_api_key=config.openai_api_key
)
prompt = PromptTemplate(
    input_variables=["text"],
    template="다음 뉴스 기사 내용을 세 문장으로 요약해줘:\n\n{text}"
)
summary_chain = LLMChain(llm=llm_keyword, prompt=prompt)

# ✅ URL 기반 기사 요약용 LLM 체인
llm_url = OpenAIChat(temperature=0.7, openai_api_key=config.openai_api_key)
url_summary_chain = load_summarize_chain(llm_url, chain_type="stuff")

# 채팅 답변 템플릿 정의
expert_prompt = PromptTemplate(
    input_variables=["question", "summaries"],
    template="""
당신은 뉴스 분야의 전문가입니다. 사용자의 질문에 대해 아래 기사 요약들을 참고하여, 정중하고 신뢰감 있게 답변해 주세요.

질문: {question}

다음은 관련 뉴스 기사 요약입니다:
{summaries}

위 기사들을 참고해 질문에 답해주세요.
"""
)

expert_chain = LLMChain(llm=llm_url, prompt=expert_prompt)


# ✅ [1] 키워드로 관련 뉴스 추출 후 요약
def summarize_top_articles_by_keyword(keyword: str, top_k: int = 4, journal: Optional[str] = None) -> List[Dict]:
    data_path = Path("data/news_data_500.json")
    if not data_path.exists():
        raise FileNotFoundError("news.json 파일이 존재하지 않습니다.")

    with open(data_path, encoding="utf-8") as f:
        articles = json.load(f)

    # ✅ journal이 지정된 경우 필터링
    if journal:
        articles = [a for a in articles if a.get("journal") == journal]
        if not articles:
            print(f"[INFO] '{journal}'에 해당하는 기사가 없습니다.")
            return []

    article_texts = [a["title"] + " " + a.get("content", "") for a in articles]
    query_vec = embedder.embed_query(keyword)
    article_vecs = embedder.embed_documents(article_texts)

    sims = cosine_similarity([query_vec], article_vecs)[0]
    top_indices = np.argsort(sims)[::-1][:top_k]

    selected = []
    for idx in top_indices:
        a = articles[idx]
        text = a.get("content", "")
        if not text.strip():
            continue
        try:
            summary = summary_chain.run(text)
        except Exception as e:
            summary = "요약에 실패했습니다."
            print(f"[ERROR] 요약 실패: {e}")

        selected.append({
            "title": a["title"],
            "url": a["link"],
            "summary": summary
        })
    return selected


def summarize_top_articles_by_keyword2(keyword: str, top_k: int = 4, journal: Optional[str] = None) -> List[Dict]:
    try:
        # ✅ ChromaDB에서 유사 뉴스 검색
        docs: List[Document] = search_similar_news(keyword, journal=journal)

        selected = []
        for doc in docs[:top_k]:
            text = doc.page_content
            meta = doc.metadata
            if not text.strip():
                continue
            try:
                summary = summary_chain.run(text)
            except Exception as e:
                summary = "요약에 실패했습니다."
                print(f"[ERROR] 요약 실패: {e}")

            selected.append({
                "title": text.split("\n")[0],  # 타이틀은 page_content 첫 줄에서
                "url": meta.get("link", ""),
                "summary": summary
            })

        return selected
    except Exception as e:
        print(f"[ERROR] ChromaDB 기반 요약 실패: {e}")
        return []


def generate_news_expert_reply_with_llm(query: str, journal: Optional[str] = None) -> (str, List[Dict]):
    """
    기사 요약과 링크를 포함한 전문가 답변과, 원 기사 정보를 JSON으로 반환.
    """
    try:
        summaries = summarize_top_articles_by_keyword2(query, top_k=3, journal=journal)

        if not summaries:
            return "죄송합니다. 관련 뉴스를 찾을 수 없습니다.", []

        # 프롬프트용 요약 텍스트 구성
        formatted_summaries = ""
        for i, item in enumerate(summaries, 1):
            formatted_summaries += (
                f"{i}. 제목: {item['title']}\n"
                f"요약: {item['summary']}\n"
                f"링크: {item['url']}\n\n"
            )

        # 전문가 응답 생성
        response = expert_chain.run({
            "question": query,
            "summaries": formatted_summaries.strip()
        })

        # 참조 기사들 JSON 형태 구성 (요약 없이 title, content, link만 포함)
        references = []
        for item in summaries:
            references.append({
                "title": item["title"],
                "summary": item["summary"],  # 이 항목을 summarize 함수에서 받아야 함
                "url": item["url"]
            })

        return response, references

    except Exception as e:
        print("[ERROR] generate_news_expert_reply_with_llm:", e)
        return "답변 생성 중 오류가 발생했습니다.", []

# ✅ [2] 뉴스 URL 크롤링 후 본문 요약
def summarize_url_article(url: str) -> str:
    try:
        resp = httpx.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")

        article_text = " ".join([p.get_text(strip=True) for p in soup.find_all("p")])
        if not article_text.strip():
            return "본문을 가져올 수 없습니다."

        doc = Document(page_content=article_text)
        return url_summary_chain.run([doc])
    except Exception as e:
        print(f"[ERROR] URL 요약 실패: {e}")
        return "요약을 처리하는 중 문제가 발생했습니다."