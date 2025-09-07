import os
import glob
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import sys
from utils.common_utils import get_gspread_client, get_kst_now
from pathlib import Path
import gspread
from datetime import datetime

# --- 기본 설정 ---
# 스크립트 파일의 현재 위치를 기준으로 절대 경로 생성
SCRIPT_DIR = Path(__file__).resolve().parent
WRITE_SHEET_NAME = 'senior_ou_news_parody_v3' # step1에서 저장한 시트 이름

def parse_rawdata(file_path):
    """rawdata.txt 파일을 파싱하여 설정값을 딕셔너리로 반환합니다."""
    config = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if ':' in line:
                    key, value = line.split(':', 1)
                    config[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"오류: 설정 파일({file_path})을 찾을 수 없습니다.", flush=True)
        return None
    return config

print("1. 초기화 및 설정 로드...", flush=True)

# --- 카드 디자인 상수 ---
CARD_WIDTH = 1920
CARD_HEIGHT = 1080
LEFT_MARGIN = 100
RIGHT_MARGIN = 15
TOP_MARGIN = 230
BOTTOM_MARGIN = 80 # 하단 여백 수정
LINE_SPACING_RATIO = 1.2
SECTION_GAP = 30

# --- 폰트 크기 ---
HEADER_FONT_SIZE = 35
SECTION_TITLE_FONT_SIZE = 32 # 소제목용 폰트 크기
OU_TITLE_FONT_SIZE = 60      # 키움
LATTE_FONT_SIZE = 40         # 키움
OU_THINK_FONT_SIZE = 50      # 키움
FOOTER_FONT_SIZE = 30

# --- 색상 ---
WHITE_COLOR = (255, 255, 255)  # 흰색으로 변경
YELLOW_COLOR = (255, 255, 0)   # 노란색 (오유타이틀, 오유생각용)
LIGHT_GRAY_COLOR = (200, 200, 200) # 소제목용 색상
SHADOW_COLOR = (0, 0, 0, 128) # 반투명 검정

print("2. 폰트 로드 시작...", flush=True)

# 폰트 경로 설정
FONT_REGULAR_PATH = SCRIPT_DIR / "asset" / "Pretendard-Regular.otf"
FONT_BOLD_PATH = SCRIPT_DIR / "asset" / "Pretendard-Bold.otf"

def load_font(path, size):
    try:
        font = ImageFont.truetype(str(path), size)
        print(f"✅ 폰트 로드 성공: {path.name} (크기: {size})", flush=True)
        return font
    except Exception as e:
        print(f"❌ 폰트 로드 실패 ({path.name}): {e}", flush=True)
        return ImageFont.load_default()

# 폰트 로드
header_font = load_font(FONT_REGULAR_PATH, HEADER_FONT_SIZE)
section_title_font = load_font(FONT_REGULAR_PATH, SECTION_TITLE_FONT_SIZE) # 소제목 폰트
ou_title_font = load_font(FONT_BOLD_PATH, OU_TITLE_FONT_SIZE)
latte_font = load_font(FONT_REGULAR_PATH, LATTE_FONT_SIZE)
ou_think_font = load_font(FONT_BOLD_PATH, OU_THINK_FONT_SIZE)
footer_font = load_font(FONT_REGULAR_PATH, FOOTER_FONT_SIZE)

# --- 텍스트 렌더링 함수 ---
def get_wrapped_lines(text, font, max_width):
    """텍스트를 주어진 너비에 맞게 줄바꿈하여 라인 리스트를 반환"""
    lines = []
    if not text or pd.isna(text):
        return lines
        
    words = str(text).split()
    if not words:
        return lines

    current_line = words[0]
    for word in words[1:]:
        test_line = current_line + ' ' + word
        # font.getlength 대신 대략적인 추정 사용
        try:
            if hasattr(font, 'getlength'):
                line_width = font.getlength(test_line)
            elif hasattr(font, 'getbbox'):
                bbox = font.getbbox(test_line)
                line_width = bbox[2] - bbox[0]
            else:
                # 대략적인 추정: 글자 수 * 20픽셀
                line_width = len(test_line) * 20
                
            if line_width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        except:
            # 오류 발생 시 단순히 단어 수로 추정
            if len(test_line) * 20 <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
                
    lines.append(current_line)
    return lines

def draw_text_with_shadow(draw, position, text, font, fill, max_width, align='left', line_spacing_ratio=1.3):
    """테두리 효과와 함께 텍스트를 그리는 함수 (기존 그림자 효과 대체)"""
    x, y = position
    lines = get_wrapped_lines(text, font, max_width)
    
    # font.size 대신 폰트 크기 추정 (대략적인 값 사용)
    estimated_font_size = 30  # 기본값
    if hasattr(font, 'size'):
        estimated_font_size = font.size
    elif hasattr(font, 'getbbox'):
        bbox = font.getbbox('A')
        estimated_font_size = bbox[3] - bbox[1]
    
    line_height = estimated_font_size * line_spacing_ratio

    for line in lines:
        draw_x = x # 모든 텍스트를 왼쪽 정렬 기준으로 그림
        
        # 테두리 효과 적용
        stroke_width = 2
        stroke_fill = (0, 0, 0) # 검은색 테두리
        draw.text((draw_x, y), line, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill, spacing=-3)
        y += line_height
    return y

# --- 메인 로직 ---
print("3. 구글 시트 데이터 로드...", flush=True)

# 설정 파일 로드
config = parse_rawdata(str(SCRIPT_DIR / 'asset' / 'rawdata.txt'))
if not config or '패러디결과_스프레드시트_ID' not in config:
    print("❌ '패러디결과_스프레드시트_ID'를 설정 파일에서 찾을 수 없습니다.", flush=True)
    exit()

# 구글 시트에서 데이터 가져오기
try:
    g_client = get_gspread_client()
    spreadsheet = g_client.open_by_key(config['패러디결과_스프레드시트_ID'])
    worksheet = spreadsheet.worksheet(WRITE_SHEET_NAME)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    print(f"✅ 구글 시트에서 전체 데이터 로드 완료. 총 {len(df)}개.", flush=True)
except Exception as e:
    print(f"❌ 구글 시트 데이터 로드 실패: {e}", flush=True)
    df = pd.DataFrame()

if df.empty:
    print("처리할 데이터가 없습니다. 프로그램을 종료합니다.", flush=True)
    exit()

# --- 오늘 날짜 데이터만 필터링 ---
today_str = get_kst_now().strftime('%Y-%m-%d, %a').lower()
print(f"-> 오늘 날짜({today_str})에 해당하는 데이터만 필터링합니다...", flush=True)
df = df[df['today'] == today_str].copy()

if df.empty:
    print("   - 오늘 생성된 새 패러디가 없습니다. 카드 생성을 건너뜁니다.", flush=True)
    exit()

# 인덱스를 리셋하여 0부터 시작하도록 함
df.reset_index(drop=True, inplace=True)

# 최신 30개만 선택 (설정 파일의 카드뉴스_개수와 일치)
max_cards = 30
if len(df) > max_cards:
    df = df.tail(max_cards).copy()
    df.reset_index(drop=True, inplace=True)
    print(f"   -> 오늘 생성할 카드 뉴스 {len(df)}개를 찾았습니다. (최신 {max_cards}개만 선택)", flush=True)
else:
    print(f"   -> 오늘 생성할 카드 뉴스 {len(df)}개를 찾았습니다.", flush=True)

# 출력 폴더 생성 및 정리
output_dir = SCRIPT_DIR / 'parody_card'
output_dir.mkdir(exist_ok=True)
for f in glob.glob(str(output_dir / '*.png')):
    os.remove(f)
print("4. 출력 폴더 준비 완료.", flush=True)


print("5. 카드 생성 시작...", flush=True)

# 모든 카드 생성
for i, (idx, row) in enumerate(df.iterrows()):
    card_index = i  # enumerate를 사용하여 안전한 정수 인덱스 사용
    print(f"\n- [{card_index+1}/{len(df)}] 카드 생성 중...", flush=True)
    
    # 카드 번호에 관계없이 항상 5.png 사용
    bg_image_name = "1.png"

    # 배경 이미지 로드
    background_path = SCRIPT_DIR / "asset" / bg_image_name
    if not background_path.exists():
        print(f"❌ 배경 이미지 없음: {background_path}, 다음 카드로 건너뜁니다.", flush=True)
        continue
    
    card = Image.open(background_path).convert("RGBA")
    draw = ImageDraw.Draw(card)
    
    max_text_width = CARD_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
    
    # --- 상단부터 순서대로 텍스트 그리기 ---
    y = TOP_MARGIN
    # 1. 헤더
    header_text = f"[오늘의 유머_뉴스패러디 {card_index+1}/{len(df)}]"
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), header_text, header_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += SECTION_GAP

    # 2. original_title만 표시 (소제목 없이)
    original_title = str(row.get('original_title', ''))
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), original_title, latte_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += SECTION_GAP

    # 3. [라떼는 말이야] latte
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), "[라떼는 말이야]", section_title_font, LIGHT_GRAY_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += 10
    latte = str(row.get('latte', ''))
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), latte, latte_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += SECTION_GAP

    # 4. [오유_title] ou_title
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), "[오유_title]", section_title_font, LIGHT_GRAY_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += 10
    ou_title = str(row.get('ou_title', ''))
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), ou_title, ou_title_font, YELLOW_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += SECTION_GAP

    # 5. [오유_생각] ou_think
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), "[오유_생각]", section_title_font, LIGHT_GRAY_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += 10
    ou_think = str(row.get('ou_think', ''))
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), ou_think, ou_think_font, YELLOW_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += SECTION_GAP
    y += SECTION_GAP  # 오유생각 후 추가 줄간격

    # 6. 면책조항
    disclaimer = str(row.get('disclaimer', ''))
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), f"면책조항 : {disclaimer}", footer_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += 10

    # 7. 출처
    source_url = str(row.get('source_url', ''))
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), f"출처 : {source_url}", footer_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)

    # 카드 저장
    out_path = output_dir / f'parody_card_{card_index+1:02d}.png'
    card.save(out_path)
    print(f"✅ 카드 저장 완료: {out_path}", flush=True)

print("\n6. 작업 완료!", flush=True) 