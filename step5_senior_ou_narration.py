import os
import pandas as pd
from common_utils import get_gspread_client, get_kst_now
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv
import time
from difflib import SequenceMatcher

# 환경 변수 로드
load_dotenv()

# 설정
SCRIPT_DIR = Path(__file__).resolve().parent
RAW_CONFIG_PATH = SCRIPT_DIR / 'asset' / 'rawdata.txt'
NARRATION_OUT_PATH = SCRIPT_DIR / 'parody_narration' / 'narration.txt'
WRITE_SHEET_NAME = 'senior_ou_news_parody_v3'

# Claude API 키
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
if not CLAUDE_API_KEY:
    raise ValueError('CLAUDE_API_KEY 환경 변수가 설정되지 않았습니다.')

# rawdata.txt 파싱
def parse_rawdata(file_path):
    config = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('['):
                    continue
                if ':' in line:
                    key, value = line.split(':', 1)
                    config[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"설정 파일({file_path})을 찾을 수 없습니다.")
    return config

# 오늘 날짜 전체 뉴스 데이터 추출
def get_today_news_rows():
    config = parse_rawdata(RAW_CONFIG_PATH)
    spreadsheet_id = config.get('패러디결과_스프레드시트_ID')
    if not spreadsheet_id:
        raise ValueError('패러디결과_스프레드시트_ID가 설정 파일에 없습니다.')
    g_client = get_gspread_client()
    spreadsheet = g_client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(WRITE_SHEET_NAME)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    today_str = get_kst_now().strftime('%Y-%m-%d, %a').lower()
    df_today = df[df['today'] == today_str].copy()
    if df_today.empty:
        raise ValueError('오늘 날짜에 해당하는 뉴스 데이터가 없습니다.')
    return df_today.reset_index(drop=True)

# 중복 뉴스 필터링 (유사도 0.85 이상이면 중복)
def is_duplicate(row, prev_rows):
    for prev in prev_rows:
        for field in ['ou_title', 'original_title', 'latte', 'ou_think']:
            if SequenceMatcher(None, str(row[field]), str(prev[field])).ratio() >= 0.85:
                return True
    return False

# 압축형 프롬프트 생성 (번호, 마무리 지시 포함, 라떼는말이죠)
def make_compact_prompt(news, idx, total):
    news_num = f"첫번째뉴스패러디" if idx == 0 else f"{idx+1}번째뉴스패러디"
    ending_guide = (
        "마무리는 '여러분은 어떻게 생각하세요?'등 시니어가 공감할 수 있는 여운, 생각할 거리, 여백을 주는 멘트로 끝내줘."
        if idx < total-1 else
        "마무리는 '이상 오늘의 유머 뉴스패러디를 모두 전해드렸습니다. 끝까지 들어 주셔서 감사합니다. 다음에 뵐때까지 즐거운 마음으로 건강히 지내세요!' 등 전체 종료 멘트로 마무리해줘."
    )
    return f"""
아래 4개 필드를 활용해서, 50초 내외로 아주 간결하고 임팩트 있게 시니어를 위한 오늘의 유머 뉴스패러디 내레이션 스크립트를 만들어줘.
- 각 뉴스는 반드시 '오늘의 유머 {news_num} 입니다.'로 시작해줘.
- 각 파트(제목, 원제목, 라떼, 생각)는 핵심만 1문장씩, 전체 5~7문장 이내로 압축.
- 라떼 필드는 반드시 '라떼는말이죠'로 시작해줘.
- {ending_guide}
- 전체 종료 멘트는 마지막 뉴스에만 넣어줘.
- 시니어가 공감할 수 있는 유머와 현실감은 유지.

ou_title: {news['ou_title']}
original_title: {news['original_title']}
latte: {news['latte']}
ou_think: {news['ou_think']}"""

# Claude 3.5 Sonnet 호출
def call_claude(prompt):
    client = Anthropic(api_key=CLAUDE_API_KEY)
    for _ in range(3):
        try:
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1200,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            if response.content:
                first = response.content[0]
                # dict이고 'text' 키가 있으면 반환, 아니면 str로 변환
                if isinstance(first, dict) and 'text' in first:
                    return first['text']
                else:
                    return str(first)
            return ""
        except Exception as e:
            print(f"Claude API 오류, 재시도: {e}")
            time.sleep(3)
    return ""

# 메인 실행
def main():
    df_today = get_today_news_rows()
    narrations = []
    prev_rows = []
    total = 0
    for idx, row in df_today.iterrows():
        if total >= 20:
            break
        if is_duplicate(row, prev_rows):
            continue
        print(f"[{total+1}/20] 뉴스 내레이션 생성 중...")
        prompt = make_compact_prompt(row, total, 20)
        narration = call_claude(prompt)
        narrations.append(narration.strip())
        prev_rows.append(row)
        total += 1
    full_narration = "\n\n".join(narrations)
    with open(NARRATION_OUT_PATH, 'w', encoding='utf-8') as f:
        f.write(full_narration)
    print(f"전체 내레이션 결과가 {NARRATION_OUT_PATH}에 저장되었습니다.")

if __name__ == '__main__':
    main() 