from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from app import config

# OpenAI 임베딩 모델 사용
embedding = OpenAIEmbeddings(openai_api_key=config.openai_api_key)
CHROMA_PATH = "./chroma_news_db"

# 뉴스 데이터를 벡터화하여 ChromaDB에 저장
def store_to_chroma(news_items: list):
    documents = []
    for item in news_items:
        content = f"{item['title']}\n{item['content']}"  # 벡터화할 텍스트
        metadata = {
            "date": item["date"],
            "journal": item["journal"],
            "link": item["link"]
        }
        documents.append(Document(page_content=content, metadata=metadata))

    # Chroma 벡터 DB에 저장
    vectorstore = Chroma.from_documents(documents, embedding=embedding, persist_directory=CHROMA_PATH)
    vectorstore.persist()
    print("✅ ChromaDB에 저장 완료")

# 쿼리를 받아 유사한 뉴스 5개 검색
def search_similar_news(query: str, journal: str = None):
    vectorstore = Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding)

    if journal:
        retriever = vectorstore.as_retriever(
            search_kwargs={"k": 5, "filter": {"journal": journal}}
        )
    else:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    return retriever.get_relevant_documents(query)
