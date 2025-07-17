import os
import feedparser
from datetime import datetime, timedelta
from anthropic import Anthropic
from anthropic._exceptions import OverloadedError, APIError
from dotenv import load_dotenv
from common_utils import get_gsheet, get_gspread_client, get_kst_now
from difflib import SequenceMatcher
import json
import re
from pathlib import Path
import time
import gspread
import pandas as pd
from newspaper import Article, Config  # newspaper3k 설치 필요: pip install newspaper3k
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Any, Dict, Optional
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# .env 파일의 절대 경로를 지정하여 로드
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path, verbose=True)

# Claude AI API 키
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
if not CLAUDE_API_KEY:
    raise ValueError("CLAUDE_API_KEY 환경 변수가 설정되지 않았습니다.")

# 스크립트 파일의 현재 위치를 기준으로 절대 경로 생성
SCRIPT_DIR = Path(__file__).resolve().parent

def parse_rawdata(file_path='asset/rawdata.txt') -> Dict[str, Any]:
    """rawdata.txt 파일을 파싱하여 설정값을 딕셔너리로 반환합니다."""
    config: Dict[str, Any] = {'rss_urls': []}
    current_section = None
    
    if not Path(file_path).exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {file_path}")
        return config
    
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
                    k = key.strip()
                    if k == 'rss_urls':
                        continue
                    config[k] = value.strip()
    except Exception as e:
        logger.error(f"설정 파일 파싱 중 오류 발생: {e}")
        return {}
    return config

# 구글 시트 설정
WRITE_SHEET_NAME = 'senior_ou_news_parody_v3'
DISCLAIMER = "면책조항 : 패러디/특정기관,개인과 무관/투자조언아님/재미목적"
# SOURCE_PREFIX = "https://gnews/" # 출처 URL 접두사  # 삭제

def get_article_content(url: str) -> Optional[Dict[str, Any]]:
    """주어진 URL의 뉴스 본문을 스크래핑합니다."""
    try:
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        config = Config()
        config.browser_user_agent = user_agent
        config.request_timeout = 10
        
        article = Article(url, config=config)
        article.download()
        article.parse()
        
        if not article.text or len(article.text.strip()) < 100:
            logger.warning(f"기사 본문이 너무 짧거나 비어있음: {url}")
            return None
            
        return {
            'url': url, 
            'title': article.title, 
            'text': article.text, 
            'publish_date': article.publish_date
        }
    except Exception as e:
        logger.warning(f"기사 다운로드 실패: {url}, 오류: {e}")
        return None

def fetch_news_from_rss(rss_urls: List[str]) -> List[Dict[str, Any]]:
    """여러 RSS 피드에서 최신 뉴스 목록을 가져옵니다."""
    all_entries = []
    for url in rss_urls:
        logger.info(f"RSS 피드 확인 중: {url}")
        try:
            feed = feedparser.parse(url)
            if hasattr(feed, 'status') and isinstance(feed.status, int) and feed.status >= 400:
                logger.warning(f"RSS 피드 오류 (HTTP {feed.status}): {url}")
                continue
                
            for entry in feed.entries:
                entry['source_rss'] = url
                all_entries.append(entry)
        except Exception as e:
            logger.error(f"RSS 피드 파싱 오류: {url}, {e}")
            continue
            
    # 중복 제거 (link 기준)
    unique_entries = list({entry.link: entry for entry in all_entries}.values())
    logger.info(f"총 {len(unique_entries)}개의 고유한 뉴스를 발견했습니다.")
    return unique_entries

def rank_and_select_news(news_list: List[Dict[str, Any]], num_to_select: int = 30) -> List[Dict[str, Any]]:
    """시니어층(50-70대) 관심도 기반 뉴스 선정"""
    # 50/60/70대 타겟으로 가중치 재조정
    SENIOR_CATEGORY_WEIGHTS = {
        'health': 2.5, 'welfare': 2.3, 'economy': 2.0, 'politics': 1.8,
        'opinion': 1.6, 'local': 1.5, 'market': 1.4, 'society': 1.3,
    }
    
    # 50/60/70대 핵심 관심사로 키워드 가중치 강화
    SENIOR_KEYWORD_WEIGHTS = {
        # 연금/복지 관련 (최고 우선순위)
        '연금': 15, '국민연금': 14, '기초연금': 13, '노령연금': 12,
        '의료비': 12, '건강보험': 12, '요양보험': 11, '장기요양': 10,
        
        # 건강 관련 (50/60/70대 핵심 관심사)
        '치매': 12, '건강검진': 10, '고혈압': 9, '당뇨': 9, '암': 9,
        '관절': 8, '무릎': 8, '허리': 8, '백내장': 7, '골다공증': 7,
        
        # 경제/생활 관련
        '물가': 11, '전기료': 10, '가스요금': 10, '수도요금': 9,
        '부동산': 8, '집값': 8, '아파트': 7, '전세': 7, '임대료': 7,
        '금리': 8, '예금': 7, '적금': 6, '펀드': 5, '주식': 6,
        
        # 정치/사회 관련
        '대통령': 9, '정부': 8, '국정감사': 7, '특검': 7, '국회': 6,
        '세금': 9, '소득세': 8, '재산세': 8, '상속세': 7,
        
        # 노인복지 관련
        '노인복지': 12, '독거노인': 10, '경로당': 8, '실버': 8,
        '요양원': 9, '요양시설': 8, '재가요양': 7,
        
        # 자녀/가족 관련
        '교육': 6, '대학': 6, '취업': 7, '결혼': 6, '육아': 5,
        '손자': 6, '손녀': 6, '며느리': 5, '사위': 5,
        
        # 기타
        'AI': 4, '스포츠': 4, '문화': 4, '여행': 5, '종교': 5
    }
    
    # 50/60/70대 특화 보너스 키워드
    SENIOR_BONUS_KEYWORDS = {
        '노인': 5, '시니어': 5, '50대': 4, '60대': 5, '70대': 6,
        '은퇴': 5, '정년': 5, '퇴직': 5, '중년': 4, '노년': 5,
        '베이비부머': 4, '실버': 4, '고령': 4, '장년': 3,
        '어르신': 4, '노인장': 3, '할머니': 3, '할아버지': 3
    }
    
    # MZ세대/젊은층 관련 제외 키워드 강화
    EXCLUDE_KEYWORDS = {
        'K-POP': -5, '아이돌': -5, '방탄소년단': -4, 'BTS': -4,
        '게임': -4, '온라인게임': -4, 'e스포츠': -4,
        '유튜버': -4, '인플루언서': -4, '크리에이터': -3,
        'SNS': -3, '틱톡': -4, '인스타그램': -3, '페이스북': -2,
        'MZ세대': -4, 'Z세대': -4, '밀레니얼': -3,
        '힙합': -3, '래퍼': -3, 'EDM': -3,
        '웹툰': -2, '만화': -2, '애니메이션': -2
    }

    for news in news_list:
        score = 0
        title = news.get('title', '')
        source_rss = news.get('source_rss', '')

        # 1. 카테고리 가중치
        for cat, weight in SENIOR_CATEGORY_WEIGHTS.items():
            if cat in source_rss:
                score += weight
                break

        # 2. 핵심 키워드 가중치
        for keyword, weight in SENIOR_KEYWORD_WEIGHTS.items():
            if keyword in title:
                score += weight

        # 3. 시니어 특별 관심 키워드 보너스
        for keyword, bonus in SENIOR_BONUS_KEYWORDS.items():
            if keyword in title:
                score += bonus

        # 4. 제외 키워드 페널티
        for keyword, penalty in EXCLUDE_KEYWORDS.items():
            if keyword in title:
                score += penalty

        # 5. 최신성 가중치
        published_time = news.get('published_parsed')
        if published_time:
            published_dt = datetime.fromtimestamp(time.mktime(published_time))
            if datetime.now() - published_dt < timedelta(days=1):
                score += 3  # 최신성 가중치 증가

            # 6. 시간대별 가중치 (50/60/70대 생활패턴 반영)
            hour = published_dt.hour
            if 6 <= hour <= 9:  # 아침 뉴스 시간
                score += 2
            elif 12 <= hour <= 14:  # 점심시간
                score += 1
            elif 18 <= hour <= 21:  # 저녁 뉴스 시간
                score += 1.5

        news['score'] = score

    sorted_news = sorted(news_list, key=lambda x: x.get('score', 0), reverse=True)

    logger.info("시니어(50/60/70대) 맞춤 뉴스 중요도 평가 및 상위 선정...")
    for i, news in enumerate(sorted_news[:10]):
        logger.info(f"  - {i+1}위 (점수: {news.get('score', 0):.1f}): {news.get('title', '')}")

    return sorted_news[:num_to_select]

def create_senior_parody_with_claude(news_item: Dict[str, Any], existing_titles: List[str]) -> str:
    """Claude AI를 사용하여 시니어 뉴스 패러디 생성"""
    client = Anthropic(api_key=CLAUDE_API_KEY)

    news_title = news_item.get('title', '제목 없음')
    news_summary = news_item.get('text', '')[:3000]  # 5000에서 3000으로 단축

    # 중복 방지 목록 문자열 생성
    if existing_titles:
        existing_titles_str = "- " + "\n- ".join(existing_titles[-10:])  # 최근 10개만 표시
    else:
        existing_titles_str = "없음"

    # 프롬프트 생성
    parody_prompt = f"""
당신은 50~70대 시니어 세대를 위한 뉴스 패러디 콘텐츠 크리에이터입니다. 제공된 뉴스 기사로 시니어들이 공감할 수 있는 패러디를 만드세요.

반드시 아래 JSON 형식으로만 응답하세요. (다른 텍스트 금지)
{{
  "ou_title": "후킹 있는 패러디 제목(30자 이내)",
  "latte": "우리 때는... 형식의 과거 회상 + 현재 상황 비교(100자 이내)",
  "ou_think": "시니어 관점의 현실적 걱정과 공감 + 약간의 위트(80자 이내)"
}}

[작성 가이드라인]
- ou_title: 감탄사/궁금증/감정 표현 활용, 3초 내 클릭 유도, 짧고 임팩트 있게
- latte: "우리 때는/시절엔..."으로 시작, 구체적 과거 경험+현재 대비, 50~100자
- ou_think: 현실적 걱정, 자녀 세대 우려, 위트/체념 섞인 자연스러운 어미, 60~100자
- 감정 톤: 70% 공감/현실, 20% 위트, 10% 희망, 과도한 부정/정치성/세대갈등/미화 금지

[예시]
뉴스: "국고채 금리 2.4% 기록"
{{
  "ou_title": "은행 이자 2.4%... 물가 7% 어쩌나",
  "latte": "우리 때는 정기예금 이자가 20%였는데 지금은 고작 2%대라니. 평생 모은 돈이 물가 때문에 반토막 나겠어",
  "ou_think": "물가는 천정부지로 오르는데 이자는 바닥... 노후자금 다 녹겠네. 저축해봤자 손해라니 이게 무슨 세상이야"
}}

[중복 방지]
- 이미 생성된 제목들과 중복되지 않게 새롭고 창의적으로 만드세요.
- 최근 생성된 제목 목록:
{existing_titles_str}

[금지사항]
- 이모지, 젊은 세대 용어, 과도한 정치성, 30자 이상 제목, JSON 외 텍스트, 가짜뉴스/선동 금지

[뉴스 기사]
- 제목: {news_title}
- 내용: {news_summary[:800]}
"""

    from anthropic.types import MessageParam
    messages: List[MessageParam] = [
        {"role": "user", "content": parody_prompt}
    ]

    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,  # 1500에서 2000으로 증가
                temperature=0.8,
                messages=messages
            )

            response_text = ""
            if response.content:
                first_content = response.content[0]
                if hasattr(first_content, 'text') and hasattr(first_content, 'type') and first_content.type == 'text':
                    response_text = first_content.text
                elif isinstance(first_content, dict) and 'text' in first_content:
                    response_text = first_content['text']
                else:
                    response_text = str(first_content)

            if not response_text:
                logger.warning("Claude 응답이 비어있습니다. 재시도합니다.")
                continue

            return response_text

        except (APIError, OverloadedError) as e:
            error_message = str(e)
            if 'credit balance is too low' in error_message:
                logger.error("🚨 Claude API 크레딧 부족! Anthropic Console에서 크레딧을 충전해주세요.")
                logger.error("🔗 https://console.anthropic.com/")
                return ""
            elif 'rate limit' in error_message.lower():
                logger.warning(f"API 속도 제한에 걸렸습니다. {retry_delay}초 후 재시도... ({attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2
            elif isinstance(e, OverloadedError):
                if attempt < max_retries - 1:
                    logger.warning(f"Claude AI가 과부하 상태입니다. {retry_delay}초 후 재시도... ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Claude AI 과부하로 패러디 생성에 실패했습니다: {e}")
                    return ""
            else:
                logger.error(f"Claude API 오류: {e}")
                return ""
        except Exception as e:
            logger.error(f"Claude AI 요청 중 예상치 못한 오류 발생: {e}")
            return ""
    return ""

def save_results_to_gsheet(client, parody_data_list: List[Dict[str, Any]], spreadsheet_id: str, worksheet_name: str):
    """생성된 패러디 결과를 구글 시트에 저장합니다. (이전 기록 삭제 후 새로 기록)"""
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        try:
            worksheet = spreadsheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            # 워크시트가 없으면 새로 만듭니다.
            worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows=1, cols=20)
            logger.info(f"새 워크시트 '{worksheet_name}'를 생성했습니다.")

        # 헤더 정의
        headers = ['today', 'ou_title', 'original_title', 'latte', 'ou_think', 'disclaimer', 'source_url']
        
        if not parody_data_list:
            logger.info("구글 시트에 추가할 데이터가 없습니다.")
            # 데이터가 없어도 헤더만 남기고 기존 데이터 삭제
            worksheet.clear()
            worksheet.append_row(headers)
            logger.info("기존 데이터를 삭제하고 헤더만 남겼습니다.")
            return
            
        # 새로운 데이터 준비
        rows_to_upload = [headers]  # 헤더를 첫 번째 행으로 추가
        today_str = get_kst_now().strftime('%Y-%m-%d, %a').lower()

        for p_data in parody_data_list:
            # original_link가 없으면 url 필드도 백업으로 저장
            source_url = p_data.get('original_link', p_data.get('url', ''))
            row = [
                today_str,
                p_data.get('ou_title', ''),
                p_data.get('original_title', ''),
                p_data.get('latte', ''),
                p_data.get('ou_think', ''),
                DISCLAIMER,
                source_url
            ]
            rows_to_upload.append(row)
        
        # 기존 데이터 모두 삭제 후 새로운 데이터로 교체
        worksheet.clear()
        worksheet.update('A1', rows_to_upload)
        logger.info(f"구글 시트 '{worksheet_name}'의 기존 데이터를 삭제하고 {len(parody_data_list)}개 새로운 데이터로 교체 완료!")

    except Exception as e:
        logger.error(f"구글 시트 저장 중 오류 발생: {e}")

def main():
    start_time = time.time()
    print("="*50)
    print("시니어(50/60/70대) 뉴스 패러디 자동 생성을 시작합니다.", flush=True)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("="*50)

    # 1. 설정 로드
    logger.info("설정 파일(asset/rawdata.txt) 로드 중...")
    config = parse_rawdata(str(SCRIPT_DIR / 'asset/rawdata.txt'))
    if not config or not config.get('rss_urls'):
        logger.error("설정 파일에 [연합뉴스RSS] 정보가 없습니다. 프로그램을 종료합니다.")
        return
    
    if '패러디결과_스프레드시트_ID' not in config:
        logger.error("설정 파일에 '패러디결과_스프레드시트_ID' 정보가 없습니다. 프로그램을 종료합니다.")
        return

    # 2. RSS 피드에서 뉴스 가져오기
    logger.info("RSS 피드에서 뉴스 수집 중...")
    all_news_entries = fetch_news_from_rss(config['rss_urls'])
    
    if not all_news_entries:
        logger.error("수집된 뉴스가 없습니다. RSS 피드를 확인해주세요.")
        return
    
    # 3. 뉴스 중요도 평가 및 선택
    # 충분히 많은 후보군 확보 (예: 100개)
    candidate_count = 100
    sorted_news = rank_and_select_news(all_news_entries, candidate_count)
    
    # 4. 최소 30개 패러디가 나올 때까지 반복
    logger.info("최소 30개 패러디가 나올 때까지 반복 생성...")
    parody_results = []
    existing_titles = []
    max_needed = 30
    api_failures = 0
    max_failures = 5
    
    for news in sorted_news:
        # 본문 스크래핑
        article = get_article_content(news.get('link', ''))
        if not article or not article.get('text'):
            continue
        article['source_rss'] = news.get('source_rss')
        article['original_link'] = news.get('link', '')
        
        # Claude 패러디 생성
        try:
            parody_response = create_senior_parody_with_claude(article, existing_titles)
            if not parody_response:
                api_failures += 1
                logger.warning(f"Claude 응답이 없어 건너뜁니다. (실패 횟수: {api_failures})")
                if api_failures >= max_failures:
                    logger.error(f"연속 {max_failures}회 API 호출 실패로 중단합니다.")
                    break
                continue

            clean_str = parody_response.strip()
            if clean_str.startswith("```json"):
                clean_str = clean_str[7:].strip()
            elif clean_str.startswith("```"):
                clean_str = clean_str[3:].strip()
            if clean_str.endswith("```"):
                clean_str = clean_str[:-3].strip()
            json_start = clean_str.find('{')
            json_end = clean_str.rfind('}')
            if json_start != -1 and json_end != -1 and json_end > json_start:
                clean_str = clean_str[json_start:json_end+1]
            clean_str = re.sub(r'\s+', ' ', clean_str).strip()
            try:
                parody_data = json.loads(clean_str)
                if 'ou_title' not in parody_data:
                    logger.warning("'ou_title' 키가 없어 건너뜁니다.")
                    continue
                current_title = parody_data['ou_title']
                is_duplicate = False
                for title in existing_titles:
                    if SequenceMatcher(None, current_title, title).ratio() > 0.85:
                        is_duplicate = True
                        logger.warning(f"유사한 제목이 이미 존재하여 건너뜁니다: {current_title}")
                        break
                if not is_duplicate:
                    parody_data['original_title'] = article['title']
                    parody_data['original_link'] = article['url']
                    parody_results.append(parody_data)
                    existing_titles.append(current_title)
                    logger.info(f"✅ 패러디 생성 성공: {current_title}")
                    api_failures = 0
            except json.JSONDecodeError as e:
                logger.warning(f"JSON 파싱 실패: {e}")
                logger.warning(f"정리된 응답: {clean_str[:100]}...")
                continue
        except Exception as e:
            logger.error(f"패러디 생성 중 오류 발생: {e}")
            continue
        if len(parody_results) >= max_needed:
            break
    logger.info(f"총 {len(parody_results)}개의 고유한 패러디를 생성했습니다.")

    # 6. 구글 시트에 결과 저장
    logger.info("생성된 패러디 결과를 구글 시트에 저장 중...")
    try:
        g_client = get_gspread_client()
        save_results_to_gsheet(g_client, parody_results, config['패러디결과_스프레드시트_ID'], WRITE_SHEET_NAME)
    except Exception as e:
        logger.error(f"구글 인증 또는 시트 저장에 실패했습니다: {e}")

    # 7. 종료
    end_time = time.time()
    print("\n" + "="*50)
    print("모든 작업 완료!", flush=True)
    print(f"총 소요 시간: {end_time - start_time:.2f}초", flush=True)
    print(f"성공적으로 생성된 패러디: {len(parody_results)}개", flush=True)
    print("="*50)

if __name__ == "__main__":
    main() 