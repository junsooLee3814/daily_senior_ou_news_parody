#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
시니어(50/60/70대) 뉴스 패러디 자동 생성 스크립트
독자 호응도 향상 버전 - 다양한 어미와 감정 표현 강화
아나콘다 환경 최적화 버전
"""

import sys
import os
from pathlib import Path
import logging
from typing import List, Any, Dict, Optional
import time
import json
import re
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import random

# 아나콘다 환경 체크 및 설정
def check_anaconda_environment():
    """아나콘다 환경을 확인하고 필요한 설정을 수행합니다."""
    print("="*60)
    print("아나콘다 환경 확인 중...")
    
    # 현재 파이썬 경로 확인
    python_path = sys.executable
    print(f"현재 Python 경로: {python_path}")
    
    # 아나콘다 환경인지 확인
    if 'anaconda' in python_path.lower() or 'conda' in python_path.lower():
        print("✅ 아나콘다 환경에서 실행 중입니다.")
    else:
        print("⚠️  아나콘다 환경이 아닙니다. 아나콘다 환경을 활성화하세요.")
        print("   conda activate [환경이름] 명령어를 사용하세요.")
    
    # 현재 작업 디렉토리 확인
    current_dir = Path.cwd()
    print(f"현재 작업 디렉토리: {current_dir}")
    
    # 스크립트 디렉토리 확인
    script_dir = Path(__file__).resolve().parent
    print(f"스크립트 디렉토리: {script_dir}")
    
    print("="*60)

# 아나콘다 환경 체크 실행
check_anaconda_environment()

# 로깅 설정 (import 전에 설정)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('senior_ou_news_parody.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# 필수 패키지 import (아나콘다 환경 최적화)
try:
    import feedparser
    from anthropic import Anthropic
    from anthropic import APIError
    from dotenv import load_dotenv
    import gspread
    import pandas as pd
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # newspaper3k 패키지 import (아나콘다 환경 대응)
    try:
        from newspaper import Article, Config
        NEWSPAPER_AVAILABLE = True
        print("✅ newspaper3k 패키지 import 성공")
    except ImportError as e:
        print(f"⚠️  newspaper3k 패키지 import 실패: {e}")
        print("   다음 명령어로 설치하세요:")
        print("   pip install newspaper3k")
        print("   또는")
        print("   conda install -c conda-forge newspaper3k")
        print("   또는")
        print("   python utils/check_newspaper.py")
        NEWSPAPER_AVAILABLE = False
        
        # 대체 방법: requests와 BeautifulSoup 사용
        try:
            import requests
            from bs4 import BeautifulSoup
            import urllib.parse
            print("✅ 대체 스크래핑 라이브러리 (requests + BeautifulSoup) 사용")
        except ImportError:
            print("❌ 대체 라이브러리도 설치되지 않았습니다.")
            print("   pip install requests beautifulsoup4 명령어로 설치하세요.")
            sys.exit(1)
    
    print("✅ 모든 필수 패키지가 정상적으로 import되었습니다.")
    
except ImportError as e:
    print(f"❌ 필수 패키지 import 실패: {e}")
    print("\n아나콘다에서 다음 명령어로 패키지를 설치하세요:")
    print("conda install -c conda-forge feedparser python-dotenv gspread pandas")
    print("pip install newspaper3k")
    print("pip install anthropic")
    print("pip install google-auth google-auth-oauthlib google-auth-httplib2")
    print("pip install requests beautifulsoup4")
    sys.exit(1)

# 로컬 모듈 import
try:
    from utils.common_utils import get_gsheet, get_gspread_client, get_kst_now
    print("✅ 로컬 모듈 import 성공")
except ImportError as e:
    print(f"❌ 로컬 모듈 import 실패: {e}")
    print("utils/common_utils.py 파일이 있는지 확인하세요.")
    sys.exit(1)

# .env 파일의 절대 경로를 지정하여 로드
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path, verbose=True)

# Claude AI API 키 (보안 강화)
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
if not CLAUDE_API_KEY:
    print("❌ CLAUDE_API_KEY 환경 변수가 설정되지 않았습니다.")
    print("아나콘다 환경에서 환경변수를 설정하려면:")
    print("conda env config vars set CLAUDE_API_KEY=your_api_key_here")
    print("또는 .env 파일에 CLAUDE_API_KEY=your_api_key_here를 추가하세요.")
    raise ValueError("CLAUDE_API_KEY 환경 변수가 설정되지 않았습니다.")

# 스크립트 파일의 현재 위치를 기준으로 절대 경로 생성
SCRIPT_DIR = Path(__file__).resolve().parent

print(f"✅ 환경 설정 완료 - 스크립트 디렉토리: {SCRIPT_DIR}")
print(f"✅ Claude API 키 확인됨: {CLAUDE_API_KEY[:10]}...")

# 전역 설정
WRITE_SHEET_NAME = 'senior_ou_news_parody_v3'
DISCLAIMER = "면책조항 : 패러디/특정기관,개인과 무관/투자조언아님/재미목적"

# 캐시를 위한 전역 변수
_article_cache = {}
_cache_hits = 0
_cache_misses = 0

def parse_rawdata(file_path='asset/rawdata.txt') -> Dict[str, Any]:
    """rawdata.txt 파일을 파싱하여 설정값을 딕셔너리로 반환합니다."""
    config: Dict[str, Any] = {'rss_urls': []}
    current_section = None
    
    file_path = Path(file_path)
    if not file_path.exists():
        logger.error(f"설정 파일을 찾을 수 없습니다: {file_path}")
        return config
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
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
        logger.error(f"설정 파일 파싱 중 오류 발생 (라인 {line_num}): {e}")
        return {}
    
    logger.info(f"설정 파일 로드 완료: RSS URL {len(config['rss_urls'])}개")
    return config

def get_article_content(url: str) -> Optional[Dict[str, Any]]:
    """주어진 URL의 뉴스 본문을 스크래핑합니다. (캐시 기능 포함)"""
    global _article_cache, _cache_hits, _cache_misses
    
    # 캐시 확인
    if url in _article_cache:
        _cache_hits += 1
        logger.debug(f"캐시 히트: {url}")
        return _article_cache[url]
    
    _cache_misses += 1
    
    try:
        if NEWSPAPER_AVAILABLE:
            # newspaper3k 사용
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
                
            result = {
                'url': url, 
                'title': article.title, 
                'text': article.text, 
                'publish_date': article.publish_date
            }
            
            # 캐시에 저장 (메모리 제한: 최대 100개)
            if len(_article_cache) >= 100:
                # 가장 오래된 항목 제거
                oldest_key = next(iter(_article_cache))
                del _article_cache[oldest_key]
            
            _article_cache[url] = result
            return result
        else:
            # 대체 방법: requests + BeautifulSoup 사용
            return get_article_content_alternative(url)
            
    except Exception as e:
        logger.warning(f"기사 다운로드 실패: {url}, 오류: {e}")
        return None

def get_article_content_alternative(url: str) -> Optional[Dict[str, Any]]:
    """requests와 BeautifulSoup을 사용한 대체 스크래핑 방법"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 제목 추출
        title = ""
        title_selectors = ['h1', '.title', '.headline', 'title', '[class*="title"]', '[class*="headline"]']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text().strip()
                break
        
        if not title:
            title_elem = soup.find('title')
            title = title_elem.get_text().strip() if title_elem else "제목 없음"
        
        # 본문 추출
        text = ""
        content_selectors = [
            '[class*="content"]', '[class*="article"]', '[class*="body"]',
            '.article-body', '.content-body', '.post-content',
            'article', 'main', '.main-content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                # 불필요한 요소 제거
                for elem in content_elem(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                    elem.decompose()
                text = content_elem.get_text().strip()
                break
        
        if not text:
            # 기본적인 텍스트 추출
            paragraphs = soup.find_all('p')
            text = ' '.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50])
        
        if len(text.strip()) < 100:
            logger.warning(f"기사 본문이 너무 짧거나 비어있음: {url}")
            return None
            
        return {
            'url': url,
            'title': title,
            'text': text,
            'publish_date': None  # 날짜 추출은 복잡하므로 None으로 설정
        }
        
    except Exception as e:
        logger.warning(f"대체 스크래핑 실패: {url}, 오류: {e}")
        return None

def fetch_news_from_rss(rss_urls: List[str]) -> List[Dict[str, Any]]:
    """여러 RSS 피드에서 최신 뉴스 목록을 가져옵니다."""
    all_entries = []
    
    def fetch_single_rss(url: str) -> List[Dict[str, Any]]:
        """단일 RSS 피드를 가져오는 함수"""
        try:
            logger.info(f"RSS 피드 확인 중: {url}")
            feed = feedparser.parse(url)
            
            if hasattr(feed, 'status') and isinstance(feed.status, int) and feed.status >= 400:
                logger.warning(f"RSS 피드 오류 (HTTP {feed.status}): {url}")
                return []
                
            entries = []
            for entry in feed.entries:
                entry['source_rss'] = url
                entries.append(entry)
            
            logger.info(f"RSS 피드 {url}에서 {len(entries)}개 뉴스 수집")
            return entries
            
        except Exception as e:
            logger.error(f"RSS 피드 파싱 오류: {url}, {e}")
            return []
    
    # 병렬 처리로 RSS 피드 가져오기
    with ThreadPoolExecutor(max_workers=min(len(rss_urls), 5)) as executor:
        future_to_url = {executor.submit(fetch_single_rss, url): url for url in rss_urls}
        
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                entries = future.result()
                all_entries.extend(entries)
            except Exception as e:
                logger.error(f"RSS 피드 처리 중 오류: {url}, {e}")
    
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

    # 성능 최적화: 키워드 검색을 위한 집합 생성
    keyword_weights = {**SENIOR_KEYWORD_WEIGHTS, **SENIOR_BONUS_KEYWORDS, **EXCLUDE_KEYWORDS}
    
    for news in news_list:
        score = 0
        title = news.get('title', '')
        source_rss = news.get('source_rss', '')

        # 1. 카테고리 가중치
        for cat, weight in SENIOR_CATEGORY_WEIGHTS.items():
            if cat in source_rss:
                score += weight
                break

        # 2. 키워드 가중치 (최적화된 검색)
        for keyword, weight in keyword_weights.items():
            if keyword in title:
                score += weight

        # 3. 최신성 가중치
        published_time = news.get('published_parsed')
        if published_time:
            try:
                published_dt = datetime.fromtimestamp(time.mktime(published_time))
                if datetime.now() - published_dt < timedelta(days=1):
                    score += 3  # 최신성 가중치 증가

                # 4. 시간대별 가중치 (50/60/70대 생활패턴 반영)
                hour = published_dt.hour
                if 6 <= hour <= 9:  # 아침 뉴스 시간
                    score += 2
                elif 12 <= hour <= 14:  # 점심시간
                    score += 1
                elif 18 <= hour <= 21:  # 저녁 뉴스 시간
                    score += 1.5
            except (ValueError, OSError) as e:
                logger.debug(f"날짜 파싱 오류: {e}")

        news['score'] = score

    sorted_news = sorted(news_list, key=lambda x: x.get('score', 0), reverse=True)

    logger.info("시니어(50/60/70대) 맞춤 뉴스 중요도 평가 및 상위 선정...")
    for i, news in enumerate(sorted_news[:10]):
        logger.info(f"  - {i+1}위 (점수: {news.get('score', 0):.1f}): {news.get('title', '')}")

    return sorted_news[:num_to_select]

def analyze_title_patterns(existing_titles: List[str]) -> Dict[str, int]:
    """기존 제목들의 어미 패턴을 분석하여 다양성 확보"""
    patterns = {
        'exclamation': 0,  # ~네, ~구나, ~어, ~야
        'question': 0,     # ~까?, ~나?, ~을까?
        'statement': 0,    # ~다, ~네, ~군
        'concern': 0       # ~겠네, ~것 같아, ~듯해
    }
    
    for title in existing_titles[-10:]:  # 최근 10개만 분석
        if any(ending in title for ending in ['까?', '나?', '을까?', '는가?', '다니?', '라니?']):
            patterns['question'] += 1
        elif any(ending in title for ending in ['네', '구나', '어', '야', '지']):
            patterns['exclamation'] += 1
        elif any(ending in title for ending in ['다', '군', '겠어']):
            patterns['statement'] += 1
        elif any(ending in title for ending in ['겠네', '것 같아', '듯해', '려나']):
            patterns['concern'] += 1
    
    return patterns

def create_senior_parody_with_claude(news_item: Dict[str, Any], existing_titles: List[str]) -> str:
    """Claude AI를 사용하여 시니어 뉴스 패러디 생성 - 다양성 강화 버전"""
    client = Anthropic(api_key=CLAUDE_API_KEY)

    news_title = news_item.get('title', '제목 없음')
    news_summary = news_item.get('text', '')[:3000]  # 5000에서 3000으로 단축

    # 중복 방지 목록 문자열 생성
    if existing_titles:
        existing_titles_str = "- " + "\n- ".join(existing_titles[-10:])  # 최근 10개만 표시
    else:
        existing_titles_str = "없음"

    # 현재 패턴 분석
    current_patterns = analyze_title_patterns(existing_titles)
    
    # 가장 적게 사용된 패턴 찾기
    min_count = min(current_patterns.values()) if current_patterns.values() else 0
    underused_patterns = [k for k, v in current_patterns.items() if v == min_count]
    
    # 패턴 가이드 생성
    if underused_patterns:
        priority_pattern = random.choice(underused_patterns)
        pattern_guide = f"우선적으로 '{priority_pattern}' 패턴 사용을 권장합니다."
    else:
        pattern_guide = "모든 패턴을 골고루 사용해주세요."

    # 개선된 프롬프트 - 다양한 어미와 감정 표현 강화
    parody_prompt = f"""
당신은 50~70대 시니어 세대를 위한 뉴스 패러디 콘텐츠 크리에이터입니다. 독자들의 호응을 받을 수 있는 다양하고 매력적인 패러디를 만드세요.

반드시 아래 JSON 형식으로만 응답하세요:
{{
  "ou_title": "다양한 어미의 매력적인 제목(30자 이내)",
  "latte": "우리 때는... 형식의 과거 회상 + 현재 상황 비교(100자 이내)",
  "ou_think": "시니어 관점의 현실적 걱정과 공감 + 약간의 위트(80자 이내)"
}}

[제목 작성 핵심 원칙 - 다양성 극대화]

🎯 **어미 다양화 필수** (각 패턴별로 골고루 분배):

1️⃣ **감탄/놀라움형 (exclamation)** - 임팩트 강함
- "~네", "~구나", "~어", "~야", "~지"
- 예: "요즘 세상 정말 빨라", "젊은이들 대단하구나", "기술이 이 정도였어?"

2️⃣ **의문/궁금증형 (question)** - 관심 유발  
- "~까?", "~나?", "~을까?", "~는가?"
- 예: "이게 정말 가능할까?", "우리도 할 수 있을까?", "언제까지 계속될까?"

3️⃣ **단정/확신형 (statement)** - 신뢰감 조성
- "~다", "~네", "~군", "~겠어"  
- 예: "확실히 달라졌다", "이젠 시대가 변했네", "정말 놀랍군"

4️⃣ **걱정/우려형 (concern)** - 공감대 형성
- "~겠네", "~것 같아", "~듯해", "~려나"
- 예: "걱정이 앞서겠네", "힘들 것 같아", "복잡해 보여"

[감정별 제목 템플릿 예시]

💰 **경제 뉴스**:
- 놀라움: "월급 1억도 가난하구나" 
- 걱정: "집값이 너무 올랐겠네"
- 확신: "요즘 돈 모으기 정말 어렵다"
- 의문: "언제까지 이럴까?"

🏛️ **정치 뉴스**:
- 감탄: "정치인들 참 바쁘네"
- 우려: "나라 걱정이 앞서"
- 단정: "세상 많이 복잡해졌다"
- 의문: "언제 조용해질까?"

🏥 **건강 뉴스**:
- 놀라움: "의학이 이렇게 발전했어?"
- 확신: "건강이 최고인게 맞다"
- 걱정: "치료비가 너무 부담스럽겠네"
- 의문: "보험 적용될까?"

📱 **기술 뉴스**:
- 감탄: "요즘 기술 정말 신기해"
- 우려: "따라가기 힘들겠어"
- 확신: "세상 정말 빨리 변한다"
- 의문: "우리도 배울 수 있을까?"

[latte (과거 회상) 작성 가이드]

✅ **구체적 비교 포인트**:
- 가격: "우리 때 집값 vs 지금 집값"
- 기술: "그땐 없던 vs 지금은 당연한"
- 사회: "예전 예의 vs 지금 문화"
- 경제: "그때 물가 vs 요즘 물가"

예시:
- "우리 때는 은행 이자가 10%넘어서 예금만 해도 용돈벌었는데, 요즘은 2%도 안되니 어디 투자해야 할지 모르겠어"
- "예전엔 대학만 나오면 취업 걱정 없었는데, 지금 젊은이들은 스펙 쌓느라 대학원까지 가야 하네"

[ou_think (현재 관점) 작성 가이드]

✅ **감정 표현 다양화**:
- 걱정: "우리 자식들은 어떻게 살아갈까"
- 공감: "정말 힘든 세상이야"
- 호기심: "우리도 한번 배워볼까?"
- 위트: "그래도 재미있긴 하네"

✅ **현실적 관점**:
- 가족 걱정 (자식, 손자)
- 경제적 불안감
- 건강 관련 우려
- 기술 적응 걱정

[톤앤매너 강화]
- 감정: 60% 현실적 공감, 25% 궁금증, 15% 건전한 위트
- 표현: 자연스럽고 친근하며 솔직한 시니어의 목소리
- 금지: 과도한 부정성, 정치적 편향, 세대갈등 조장

[후킹 강화 기법]
1. 구체적 숫자로 충격 주기: "3억 아파트 vs 300만원 월급"
2. 극명한 대조 보여주기: "옛날 20% vs 요즘 2%"
3. 질문으로 궁금증 유발: "이게 정말 가능한 일인가?"
4. 시니어 공감 포인트: "우리 자식들은 어떻게 살아가나"

[중복 방지 및 다양성]
- 같은 패턴 연속 사용 금지
- 기존 제목과 80% 이상 유사성 금지
- 최근 생성 제목: {existing_titles_str}

[절대 준수사항]

🚫 **금지사항**:
- 연속 3개 이상 같은 어미 사용 금지
- "아이고", "어이구", "헉" 등 과도한 감탄사
- 정치적 편향성
- 세대갈등 조장 표현
- 30자 초과

✅ **필수사항**:
- 4가지 어미 패턴을 골고루 사용
- 자연스럽고 친근한 톤
- 클릭 욕구 자극하는 호기심
- 시니어 공감 포인트 포함

[다양성 보장을 위한 현재 상황]
현재 패턴 분포: {current_patterns}
{pattern_guide}
최근 생성된 제목들: {existing_titles_str}

[뉴스 기사]
제목: {news_title}
내용: {news_summary[:800]}

※ 중요: 반드시 기존 제목들과 다른 어미 패턴을 사용하여 다양성을 확보하세요. 같은 패턴의 연속 사용을 피하고, 독자들이 지루해하지 않도록 매번 새로운 느낌을 주세요.
"""

    messages = [
        {"role": "user", "content": parody_prompt}
    ]

    max_retries = 3
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,  # 1500에서 2000으로 증가
                temperature=0.9,  # 0.8에서 0.9로 증가 - 더 다양한 표현 유도
                messages=messages  # type: ignore
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

        except APIError as e:
            error_message = str(e)
            if 'credit balance is too low' in error_message:
                logger.error("🚨 Claude API 크레딧 부족! Anthropic Console에서 크레딧을 충전해주세요.")
                logger.error("🔗 https://console.anthropic.com/")
                return ""
            elif 'rate limit' in error_message.lower():
                logger.warning(f"API 속도 제한에 걸렸습니다. {retry_delay}초 후 재시도... ({attempt + 1}/{max_retries})")
                time.sleep(retry_delay)
                retry_delay *= 2
            elif 'overloaded' in error_message.lower():
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
        headers = ['today', 'ou_title', 'original_title', 'latte', 'ou_think', 'disclaimer', 'source_url', 'article_content']
        
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
            # 기사 원문 (최대 1000자로 제한)
            article_content = p_data.get('text', '')[:1000] if p_data.get('text') else ''
            row = [
                today_str,
                p_data.get('ou_title', ''),
                p_data.get('original_title', ''),
                p_data.get('latte', ''),
                p_data.get('ou_think', ''),
                DISCLAIMER,
                source_url,
                article_content
            ]
            rows_to_upload.append(row)
        
        # 기존 데이터 모두 삭제 후 새로운 데이터로 교체
        worksheet.clear()
        worksheet.update(values=rows_to_upload, range_name='A1')
        logger.info(f"구글 시트 '{worksheet_name}'의 기존 데이터를 삭제하고 {len(parody_data_list)}개 새로운 데이터로 교체 완료!")

    except Exception as e:
        logger.error(f"구글 시트 저장 중 오류 발생: {e}")

def main():
    """메인 실행 함수 - 다양성 강화 로직 포함"""
    start_time = time.time()
    print("="*50)
    print("시니어 뉴스 패러디 자동 생성을 시작합니다. (다양성 강화 버전)", flush=True)
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("="*50)

    try:
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
        
        # 4. 개선된 패러디 생성 로직 - 다양성 강화
        logger.info("최소 30개 패러디가 나올 때까지 반복 생성... (다양성 강화)")
        parody_results = []
        existing_titles = []
        max_needed = 30
        api_failures = 0
        max_failures = 5
        
        # 다양성 추적을 위한 카운터
        pattern_counter = {
            'exclamation': 0, 'question': 0, 'statement': 0, 'concern': 0
        }
        
        for news in sorted_news:
            # 본문 스크래핑
            article = get_article_content(news.get('link', ''))
            if not article or not article.get('text'):
                continue
            article['source_rss'] = news.get('source_rss')
            article['original_link'] = news.get('link', '')
            
            # 패턴 다양성 확인 후 생성
            current_patterns = analyze_title_patterns(existing_titles)
            logger.info(f"현재 패턴 분포: {current_patterns}")
            
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
                        parody_data['text'] = article.get('text', '')  # 원문 추가
                        
                        parody_results.append(parody_data)
                        existing_titles.append(current_title)
                        
                        # 패턴 추적 및 카운터 업데이트
                        if any(ending in current_title for ending in ['까?', '나?', '을까?', '는가?', '다니?', '라니?']):
                            pattern_counter['question'] += 1
                        elif any(ending in current_title for ending in ['네', '구나', '어', '야', '지']):
                            pattern_counter['exclamation'] += 1
                        elif any(ending in current_title for ending in ['다', '군', '겠어']):
                            pattern_counter['statement'] += 1
                        elif any(ending in current_title for ending in ['겠네', '것 같아', '듯해', '려나']):
                            pattern_counter['concern'] += 1
                            
                        logger.info(f"✅ 패러디 생성 성공 ({len(parody_results)}/{max_needed}): {current_title}")
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
        # 최종 패턴 분포 출력
        logger.info(f"최종 제목 패턴 분포: {pattern_counter}")
        logger.info(f"총 {len(parody_results)}개의 다양한 패러디를 생성했습니다.")

        # 5. 구글 시트에 결과 저장
        logger.info("생성된 패러디 결과를 구글 시트에 저장 중...")
        try:
            g_client = get_gspread_client()
            save_results_to_gsheet(g_client, parody_results, config['패러디결과_스프레드시트_ID'], WRITE_SHEET_NAME)
        except Exception as e:
            logger.error(f"구글 인증 또는 시트 저장에 실패했습니다: {e}")

        # 6. 캐시 통계 출력
        logger.info(f"캐시 통계: 히트 {_cache_hits}회, 미스 {_cache_misses}회")

    except KeyboardInterrupt:
        logger.info("사용자에 의해 프로그램이 중단되었습니다.")
    except Exception as e:
        logger.error(f"프로그램 실행 중 예상치 못한 오류 발생: {e}")
        raise

    # 7. 종료
    end_time = time.time()
    print("\n" + "="*50)
    print("모든 작업 완료! (다양성 강화 버전)", flush=True)
    print(f"총 소요 시간: {end_time - start_time:.2f}초", flush=True)
    print(f"성공적으로 생성된 패러디: {len(parody_results)}개", flush=True)
    print(f"제목 패턴 다양성: {pattern_counter}", flush=True)
    total_patterns = sum(pattern_counter.values())
    if total_patterns > 0:
        print("패턴별 비율:")
        for pattern, count in pattern_counter.items():
            percentage = (count / total_patterns) * 100
            print(f"  - {pattern}: {count}개 ({percentage:.1f}%)")
    print("="*50)

if __name__ == "__main__":
    main() 