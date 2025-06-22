import os
import feedparser
from datetime import datetime, timedelta
from anthropic import Anthropic, OverloadedError
from dotenv import load_dotenv
from common_utils import get_gsheet, get_gspread_client
from difflib import SequenceMatcher
import json
import re
from pathlib import Path
import time
import gspread
import pandas as pd
from newspaper import Article, Config
from concurrent.futures import ThreadPoolExecutor, as_completed

# .env 파일의 절대 경로를 지정하여 로드
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, verbose=True)

# Claude AI API 키
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
if not CLAUDE_API_KEY:
    raise ValueError("CLAUDE_API_KEY 환경 변수가 설정되지 않았습니다.")

# 스크립트 파일의 현재 위치를 기준으로 절대 경로 생성
SCRIPT_DIR = Path(__file__).resolve().parent

def parse_rawdata(file_path='asset/rawdata.txt'):
    """rawdata.txt 파일을 파싱하여 설정값을 딕셔너리로 반환합니다."""
    config = {'rss_urls': []}
    current_section = None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('[') and line.endswith(']'):
                    current_section = line[1:-1]
                elif current_section == '연합뉴스RSS':
                    config['rss_urls'].append(line)
                elif ':' in line:
                    key, value = line.split(':', 1)
                    config[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"오류: 설정 파일({file_path})을 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"오류: 설정 파일({file_path}) 파싱 중 오류 발생: {e}")
        return None
    return config

# 구글 시트 설정
WRITE_SHEET_NAME = 'senior_ou_news_parody_v3'
DISCLAIMER = "면책조항 : 패러디/특정기관,개인과 무관/투자조언아님/재미목적"
SOURCE_PREFIX = "https://gnews/" # 출처 URL 접두사

def get_article_content(url):
    """주어진 URL의 뉴스 본문을 스크래핑합니다."""
    try:
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        config = Config()
        config.browser_user_agent = user_agent
        config.request_timeout = 10
        
        article = Article(url, config=config)
        article.download()
        article.parse()
        return {'url': url, 'title': article.title, 'text': article.text, 'publish_date': article.publish_date}
    except Exception as e:
        print(f"  - (경고) 기사 다운로드 실패: {url}, 오류: {e}")
        return None

def fetch_news_from_rss(rss_urls):
    """여러 RSS 피드에서 최신 뉴스 목록을 가져옵니다."""
    all_entries = []
    for url in rss_urls:
        print(f"  - RSS 피드 확인 중: {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            entry['source_rss'] = url
            all_entries.append(entry)
    # 중복 제거 (link 기준)
    unique_entries = list({entry.link: entry for entry in all_entries}.values())
    print(f"  -> 총 {len(unique_entries)}개의 고유한 뉴스를 발견했습니다.")
    return unique_entries

def rank_and_select_news(news_list, num_to_select=30):
    """뉴스 목록의 중요도를 평가하고 상위 N개를 선택합니다."""
    
    CATEGORY_WEIGHTS = {
        'opinion': 1.5, 'politics': 1.4, 'economy': 1.3, 'market': 1.2,
        'local': 1.0, 'health': 0.9
    }
    KEYWORD_WEIGHTS = {
        '금리': 5, '정부': 4, '특검': 4, '대통령': 4, 'AI': 3, '연금': 3,
        '부동산': 3, '물가': 2
    }

    for news in news_list:
        score = 0
        # 1. 카테고리 가중치
        for cat, weight in CATEGORY_WEIGHTS.items():
            if cat in news.get('source_rss', ''):
                score += weight
                break
        
        # 2. 키워드 가중치
        title = news.get('title', '')
        for keyword, weight in KEYWORD_WEIGHTS.items():
            if keyword in title:
                score += weight
        
        # 3. 최신성 가중치 (최근 24시간 내 기사에 가산점)
        published_time = news.get('published_parsed')
        if published_time:
            published_dt = datetime.fromtimestamp(time.mktime(published_time))
            if datetime.now() - published_dt < timedelta(days=1):
                score += 2

        news['score'] = score
    
    # 점수 기준으로 정렬
    sorted_news = sorted(news_list, key=lambda x: x.get('score', 0), reverse=True)
    
    print("\n[2/6] 뉴스 중요도 평가 및 상위 30개 선정...")
    for i, news in enumerate(sorted_news[:10]): # 상위 10개만 점수 표시
        print(f"  - {i+1}위 (점수: {news.get('score', 0):.1f}): {news.title}")
        
    return sorted_news[:num_to_select]

def create_senior_parody_with_claude(news_item, existing_titles):
    """Claude AI를 사용하여 시니어 뉴스 패러디 생성"""
    client = Anthropic(api_key=CLAUDE_API_KEY)

    news_title = news_item.get('title', '제목 없음')
    news_summary = news_item.get('text', '')[:5000]

    # f-string 내 백슬래시 문법 오류를 피하기 위해, 중복 방지 목록 문자열을 미리 생성합니다.
    if existing_titles:
        # 각 제목 앞에 "- "를 붙이고 줄바꿈으로 연결합니다.
        existing_titles_str = "- " + "\n- ".join(existing_titles)
    else:
        existing_titles_str = "없음"

    # 프롬프트 구성
    parody_prompt = f"""# 오늘의유머_뉴스패러디_시니어V 제작 지침

## 🎯 **미션**
당신은 시니어층을 위한 오늘의유머 스타일 뉴스 패러디 전문가입니다. 제공되는 **뉴스 본문 전체**를 깊이 있게 분석하여, 시니어들이 공감하고 즐길 수 있는 유머러스한 패러디를 제작해야 합니다.

## 📰 분석할 뉴스 원문
- **제목:** {news_title}
- **본문:**
{news_summary}

---
## 📝 **결과물 포맷 (엄수)**
- **(절대 규칙) 다른 설명 없이, 아래 JSON 형식으로만 응답해주세요.**
- **(절대 규칙) 절대로 이모지(emoji)는 사용하지 마세요.**
- **(절대 규칙) 각 항목의 글자수 제한을 반드시 지켜주세요.**

```json
{{
  "ou_title": "여기에 [오유_Title] 내용 (50자 이내)",
  "latte": "여기에 [라떼] 내용 (100자 이내)",
  "ou_think": "여기에 [오유_Think] 내용 (70자 이내)"
}}
```

## 🎨 **세부 제작 가이드라인**

### **[ou_title] 작성법 (50자 이내):**
- **강력한 후킹**: "경악", "속보", "충격", "깜놀", "대박", "헉!", "진짜?", "미쳤다", "세상에" 등 매번 다른 강력한 후킹 문구를 창의적으로 사용하세요. **"충격!!"만 반복하지 마세요.**
- **핵심 찌르기**: 뉴스 본문의 핵심 내용을 한 문장으로 꿰뚫는 질문이나 감탄사를 사용하세요. (예: "이걸 이제 와서 한다고??")

### **[라떼] 작성법 (100자 이내):**
- **"우리 때는..."**: 본문 내용과 관련된 과거 경험을 현재와 비교하며 세대 공감을 유도하세요. (예: "우리 때는 주판알 튀기던 게 AI 계산기가 됐네...")
- **친근한 말투**: "~다니", "~라니", "~구나" 등 자연스러운 경어체를 사용하세요.

### **[오유_Think] 작성법 (70자 이내):**
- **서민의 시각**: 뉴스 내용을 라면값, 기름값, 자식 걱정 등 서민의 삶과 연결하여 냉소적이고 현실적인 생각을 표현하세요. (예: "어차피 올라도 내 월급은 그대로... ㅠㅠㅠ")
- **직설적 표현**: "결국 ~", "또 ~", "진작에 ~" 같은 직설적인 어투를 사용하세요.

### **감정 표현 필수 사용:**
- 뉴스마다 ??, !!, ..., ㅋㅋㅋ, ㅠㅠㅠ 등을 2~3개 이상 자연스럽게 조합하여 감정을 풍부하게 표현해주세요.

## ✍️ **(매우 중요) 중복 패러디 방지**
- 아래는 이미 생성된 패러디 제목들입니다.
- **절대로 아래 목록과 유사한 내용이나 스타일의 `ou_title`을 만들지 마세요.**
- 완전히 새롭고, 창의적인 제목을 만들어야 합니다.

### 📜 이미 생성된 제목 목록:
{existing_titles_str}
"""

    messages = [{"role": "user", "content": parody_prompt}]

    max_retries = 3
    retry_delay = 5  # seconds
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=2000,
                temperature=0.8,
                messages=messages
            )
            return response.content[0].text if response.content else ""
        except OverloadedError as e:
            if attempt < max_retries - 1:
                print(f"  - (경고) Claude AI가 과부하 상태입니다. {retry_delay}초 후 재시도합니다... ({attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print(f"  - (오류) Claude AI 과부하로 패러디 생성에 실패했습니다: {e}")
                return ""
        except Exception as e:
            print(f"  - (오류) Claude AI 요청 중 예상치 못한 오류 발생: {e}")
            return ""
    return ""

def save_results_to_gsheet(client, parody_data_list, spreadsheet_id, worksheet_name):
    """생성된 패러디 결과를 구글 시트에 저장합니다."""
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
            worksheet.clear()
            print(f"  - 기존 워크시트 '{worksheet_name}'의 내용을 삭제했습니다.")
        except gspread.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=len(parody_data_list) + 10, cols=20)
            print(f"  - 새 워크시트 '{worksheet_name}'를 생성했습니다.")
        
        headers = ['today', 'ou_title', 'original_title', 'latte', 'ou_think', 'disclaimer', 'source_url']
        worksheet.append_row(headers)
        
        rows_to_upload = []
        today_str = datetime.now().strftime('%Y-%m-%d, %a').lower()

        for p_data in parody_data_list:
            row = [
                today_str,
                p_data.get('ou_title', ''),
                p_data.get('original_title', ''),
                p_data.get('latte', ''),
                p_data.get('ou_think', ''),
                DISCLAIMER,
                p_data.get('original_link', '')
            ]
            rows_to_upload.append(row)
            
        worksheet.append_rows(rows_to_upload)
        print(f"  -> 구글 시트 '{worksheet_name}'에 {len(rows_to_upload)}개 데이터 저장 완료!")

    except Exception as e:
        print(f"  ! 구글 시트 저장 중 오류 발생: {e}")

def main():
    start_time = time.time()
    print("="*50)
    print("시니어 뉴스 패러디 자동 생성을 시작합니다.")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    # 1. 설정 로드
    print("\n[1/6] 설정 파일(asset/rawdata.txt) 로드 중...")
    config = parse_rawdata(SCRIPT_DIR / 'asset/rawdata.txt')
    if not config or not config.get('rss_urls'):
        print("  ! 설정 파일에 [연합뉴스RSS] 정보가 없습니다. 프로그램을 종료합니다.")
        return
    
    if not config or '패러디결과_스프레드시트_ID' not in config:
        print("  ! 설정 파일에 '패러디결과_스프레드시트_ID' 정보가 없습니다. 프로그램을 종료합니다.")
        return

    # 2. RSS 피드에서 뉴스 가져오기
    print("\n[2/6] RSS 피드에서 뉴스 수집 중...")
    all_news_entries = fetch_news_from_rss(config['rss_urls'])
    
    # 3. 뉴스 중요도 평가 및 선택
    selected_news = rank_and_select_news(all_news_entries, int(config.get('카드뉴스_개수', 30)))
    
    # 4. 선택된 뉴스의 본문 스크래핑
    print("\n[3/6] 선택된 뉴스의 전체 본문 스크래핑 중...")
    scraped_articles = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(get_article_content, news.link): news for news in selected_news}
        for future in as_completed(future_to_url):
            result = future.result()
            if result and result['text']:
                original_news_item = future_to_url[future]
                result['source_rss'] = original_news_item.get('source_rss')
                result['original_link'] = original_news_item.link
                scraped_articles.append(result)
                print(f"  - 스크래핑 완료: {result['title'][:30]}...")
            time.sleep(0.1) # 서버 부하 방지를 위한 약간의 딜레이
    print(f"  -> 총 {len(scraped_articles)}개 기사의 본문을 성공적으로 가져왔습니다.")

    # 5. Claude AI를 사용하여 뉴스 패러디 생성
    print("\n[4/6] Claude AI를 사용하여 뉴스 패러디 생성 중...")
    parody_results = []
    existing_titles = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_article = {executor.submit(create_senior_parody_with_claude, article, existing_titles): article for article in scraped_articles}
        
        for i, future in enumerate(as_completed(future_to_article)):
            article = future_to_article[future]
            print(f"  - 패러디 생성 중 ({i+1}/{len(scraped_articles)}): {article['title'][:30]}...")
            
            try:
                parody_json_str = future.result()
                if not parody_json_str:
                    continue

                # Claude 응답에서 JSON 부분만 추출 (```json ... ``` 핸들링)
                clean_str = parody_json_str.strip()
                if clean_str.startswith("```json"):
                    clean_str = clean_str[7:].strip()
                if clean_str.endswith("```"):
                    clean_str = clean_str[:-3].strip()
                
                try:
                    parody_data = json.loads(clean_str)
                    
                    # 중복 및 유사도 검사
                    is_duplicate = False
                    if 'ou_title' in parody_data:
                        current_title = parody_data['ou_title']
                        for title in existing_titles:
                            if SequenceMatcher(None, current_title, title).ratio() > 0.85:
                                is_duplicate = True
                                print(f"  - (경고) 유사한 제목이 이미 존재하여 건너뜁니다: {current_title}")
                                break
                        
                        if not is_duplicate:
                            parody_data['original_title'] = article['title']
                            parody_data['original_link'] = article['url']
                            parody_results.append(parody_data)
                            existing_titles.append(current_title)
                    else:
                        print(f"  - (경고) 응답에 'ou_title'이 없어 건너뜁니다: {clean_str}")

                except json.JSONDecodeError:
                    print(f"  - (경고) Claude AI의 응답이 유효한 JSON이 아닙니다: {parody_json_str}")
                    continue

            except Exception as e:
                print(f"  - (오류) 패러디 생성 작업 중 오류 발생: {article['title']}, {e}")

    print(f"  -> 총 {len(parody_results)}개의 고유한 패러디를 생성했습니다.")

    # 6. 구글 시트에 결과 저장
    print("\n[5/6] 생성된 패러디 결과를 구글 시트에 저장 중...")
    try:
        g_client = get_gspread_client()
        save_results_to_gsheet(g_client, parody_results, config['패러디결과_스프레드시트_ID'], WRITE_SHEET_NAME)
    except Exception as e:
        print(f"  ! 구글 인증 또는 시트 저장에 실패했습니다: {e}")

    # 7. 종료
    end_time = time.time()
    print("\n[6/6] 모든 작업 완료!")
    print(f"총 소요 시간: {end_time - start_time:.2f}초")
    print("="*50)

if __name__ == "__main__":
    main() 