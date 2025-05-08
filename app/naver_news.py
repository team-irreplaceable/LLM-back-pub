import json
from app.config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import re
import time
from email.utils import parsedate_to_datetime


news_media_mapping = {
    "yonhapnews.co.kr": "연합뉴스",
    "yonhapnewstv.co.kr": "연합뉴스TV",
    "news1.kr": "뉴스1",
    "edu.donga.com": "동아일보",
    "biz.heraldcorp.com": "헤럴드경제",
    "daily.hankooki.com": "한국일보",
    "kmib.co.kr": "기독교일보",
    "kbs.co.kr": "KBS",
    "munhwa.com": "문화일보",
    "sports.naver.com": "네이버 스포츠",
    "newsis.com": "뉴시스",
    "segye.com": "세계일보",
    "hankooki.com": "한겨레",
    "chosun.com": "조선일보",
    "joongang.co.kr": "중앙일보",
    "khan.co.kr": "경향신문",
    "hani.co.kr": "한겨레",
    "sports.chosun.com": "스포츠조선",
    "sports.donga.com": "스포츠동아",
    "news.naver.com": "네이버 뉴스",
    "n.news.naver.com": "네이버 뉴스",
    "m.post.naver.com": "네이버 포스트",
    "seoul.co.kr": "서울신문",
    "etnews.com": "전자신문",
    "ytn.co.kr": "YTN",
    "tbs.seoul.kr": "TBS",
    "mbn.co.kr": "MBN 뉴스",
    "news.kmib.co.kr": "국민일보",
    "newdaily.co.kr": "뉴데일리",
    "yna.co.kr": "연합뉴스",
    "naeil.com": "내일신문",
    "kihoilbo.co.kr": "기호일보",
    "edaily.co.kr": "이데일리",
    "fnnews.com": "파이넨셜뉴스",
    "hankyung.com": "한경",
    "incheonnews.com": "인천뉴스",
    "bloter.net": "BROTER",
    "dt.co.kr": "디지털타임스",
    "sentv.co.kr": "서울경제TV" ,
    "econovill.com": "이코노믹 리뷰",
    "nytimes.com": "The New York Times",
    "digitaltoday.co.kr": "Digital Today",
    "koreajoongangdaily.joins.com": "Korea JoongAng Daily",
    "ddaily.co.kr": "디지털 데일리",
    "hankyung.com": "한국경제신문",
    "sedaily.com": "서울경제",
    "sportsseoul.com": "스포츠서울",
    "joongboo.com": "중부일보",
    "nocutnews.co.kr": "노컷뉴스",
    "imbc.com": "MBC 뉴스",
    "news.mt.co.kr": "머니투데이",
}

# URL에서 도메인 추출 함수
def extract_domain(url):
    parsed_url = urlparse(url)
    domain = parsed_url.hostname
    if domain.startswith("www."):
        domain = domain[4:]  # "www." 제거
    return domain

# 태그 제거
def clean_html_tags(text):
    return re.sub(r"<.*?>", "", text)

# 날짜 형식 지정
def format_date(pub_date_str):
    try:
        dt = parsedate_to_datetime(pub_date_str)
        return dt.strftime("%Y-%m-%d %H:%M")  # 예: 2025-05-06 10:59
    except Exception as e:
        print(f"날짜 파싱 오류: {e}")
        return pub_date_str


def get_article_content(url: str) -> str:
    """
    주어진 URL에서 기사 본문을 추출하는 함수.

    :param url: 뉴스 기사 페이지의 URL
    :return: 기사 본문 텍스트 (사진은 제외됨)
    """
    try:
        # 웹 페이지 요청 보내기
        response = requests.get(url)

        # 요청이 성공적일 때
        if response.status_code == 200:
            # BeautifulSoup을 사용해 HTML 파싱
            soup = BeautifulSoup(response.text, 'html.parser')

            # 기사 본문이 들어있는 <article> 태그 찾기
            article = soup.find('article', {'id': 'dic_area', 'class': 'go_trans _article_content'})

            # 기사 본문 추출
            if article:
                content = article.get_text(strip=True)
                return content
            else:
                return "기사 본문을 찾을 수 없습니다."
        else:
            return f"웹사이트 요청 실패: {response.status_code}"

    except Exception as e:
        return f"오류 발생: {str(e)}"
    
    
# 네이버 뉴스 검색 API로 뉴스 수집
def fetch_news(total, keywords):
    # 뉴스 데이터를 담을 리스트
    news_data = []
    start = 1
    
    # 요청 URL을 위한 기본 설정
    base_url = "https://openapi.naver.com/v1/search/news.json"

    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }

    total_news_count = total
    display_count = 100
    total_pages = total_news_count // display_count

    news_data = []

    for keyword in keywords:
        print(f"🔍 '{keyword}' 키워드 수집 시작, 현재까지 리스트 길이: {len(news_data)}")

        for start in range(1, total_pages + 1):
            params = {
                "query": keyword,
                "display": display_count,
                "start": (start - 1) * display_count + 1,
                "sort": "sim"
            }

            try:
                response = requests.get(base_url, headers=headers, params=params)
                data = response.json()

                for item in data["items"]:
                    if item["link"].startswith("https://n.news.naver.com/"):
                        news_item = {
                            "title": clean_html_tags(item["title"]),
                            "date": format_date(item["pubDate"]),
                            "link": item["link"],
                            "content": get_article_content(item["link"]),
                            "journal": news_media_mapping.get(extract_domain(item["originallink"]), "Unknown")
                        }
                        news_data.append(news_item)

                time.sleep(1)

            except Exception as e:
                print(f"❌ '{keyword}' 키워드의 {start}페이지에서 오류 발생: {e}")
                break
    # "journal" 값이 "Unknown"이 아닌 데이터만 남김
    filtered_data = [item for item in news_data if item['journal'] != 'Unknown']

    # 제목 기준 중복 제거
    seen_titles = set()
    deduplicated_data = []
    for item in filtered_data:
        if item['title'] not in seen_titles:
            seen_titles.add(item['title'])
            deduplicated_data.append(item)

    # deduplicated_data를 JSON 파일로 저장
    with open('data/news_data.json', 'w', encoding='utf-8') as f:
        json.dump(deduplicated_data, f, ensure_ascii=False, indent=4)

    print(f"✅ 전체 수집 완료! 총 저장된 기사 수: {len(deduplicated_data)}")
        
    return filtered_data 