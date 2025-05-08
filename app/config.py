import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

openai_api_key = os.getenv("OPENAI_API_KEY")