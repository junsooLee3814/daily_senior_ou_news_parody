import os
import glob
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
from common_utils import get_gspread_client
from pathlib import Path
import gspread

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
        print(f"오류: 설정 파일({file_path})을 찾을 수 없습니다.")
        return None
    return config

print("1. 초기화 및 설정 로드...")

# --- 카드 디자인 상수 ---
CARD_WIDTH = 1920
CARD_HEIGHT = 1080
LEFT_MARGIN = 100
RIGHT_MARGIN = 100
TOP_MARGIN = 150
BOTTOM_MARGIN = 80 # 하단 여백 수정
LINE_SPACING_RATIO = 1.3
SECTION_GAP = 30

# --- 폰트 크기 ---
HEADER_FONT_SIZE = 35
SECTION_TITLE_FONT_SIZE = 32 # 소제목용 폰트 크기
OU_TITLE_FONT_SIZE = 65      # 키움
LATTE_FONT_SIZE = 45         # 키움
OU_THINK_FONT_SIZE = 55      # 키움
FOOTER_FONT_SIZE = 30

# --- 색상 ---
WHITE_COLOR = (255, 255, 255)
LIGHT_GRAY_COLOR = (200, 200, 200) # 소제목용 색상
SHADOW_COLOR = (0, 0, 0, 128) # 반투명 검정

print("2. 폰트 로드 시작...")

# 폰트 경로 설정
FONT_REGULAR_PATH = SCRIPT_DIR / "asset" / "Pretendard-Regular.otf"
FONT_BOLD_PATH = SCRIPT_DIR / "asset" / "Pretendard-Bold.otf"

def load_font(path, size):
    try:
        font = ImageFont.truetype(str(path), size)
        print(f"✅ 폰트 로드 성공: {path.name} (크기: {size})")
        return font
    except Exception as e:
        print(f"❌ 폰트 로드 실패 ({path.name}): {e}")
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
        if font.getlength(current_line + ' ' + word) <= max_width:
            current_line += ' ' + word
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)
    return lines

def draw_text_with_shadow(draw, position, text, font, fill, max_width, align='left', line_spacing_ratio=1.3):
    """테두리 효과와 함께 텍스트를 그리는 함수 (기존 그림자 효과 대체)"""
    x, y = position
    lines = get_wrapped_lines(text, font, max_width)
    line_height = font.size * line_spacing_ratio

    for line in lines:
        draw_x = x # 모든 텍스트를 왼쪽 정렬 기준으로 그림
        
        # 테두리 효과 적용
        stroke_width = 2
        stroke_fill = (0, 0, 0) # 검은색 테두리
        draw.text((draw_x, y), line, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
        y += line_height
    return y

# --- 메인 로직 ---
print("3. 구글 시트 데이터 로드...")

# 설정 파일 로드
config = parse_rawdata(SCRIPT_DIR / 'asset' / 'rawdata.txt')
if not config or '패러디결과_스프레드시트_ID' not in config:
    print("❌ '패러디결과_스프레드시트_ID'를 설정 파일에서 찾을 수 없습니다.")
    exit()

# 구글 시트에서 데이터 가져오기
try:
    g_client = get_gspread_client()
    spreadsheet = g_client.open_by_key(config['패러디결과_스프레드시트_ID'])
    worksheet = spreadsheet.worksheet(WRITE_SHEET_NAME)
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    print(f"✅ 데이터 로드 완료. 총 {len(df)}개.")
except Exception as e:
    print(f"❌ 구글 시트 데이터 로드 실패: {e}")
    df = pd.DataFrame()

if df.empty:
    print("처리할 데이터가 없습니다. 프로그램을 종료합니다.")
    exit()

# 출력 폴더 생성 및 정리
output_dir = SCRIPT_DIR / 'parody_card'
output_dir.mkdir(exist_ok=True)
for f in glob.glob(str(output_dir / '*.png')):
    os.remove(f)
print("4. 출력 폴더 준비 완료.")


print("5. 카드 생성 시작...")

# 모든 카드 생성
for idx, row in df.iterrows():
    print(f"\n- [{idx+1}/{len(df)}] 카드 생성 중...")
    
    # 카드 번호에 따라 배경 이미지 선택
    card_num = idx + 1
    if 1 <= card_num <= 5:
        bg_image_name = "2.png"
    elif 6 <= card_num <= 10:
        bg_image_name = "3.png"
    elif 11 <= card_num <= 15:
        bg_image_name = "4.png"
    elif 16 <= card_num <= 20:
        bg_image_name = "5.png"
    elif 21 <= card_num <= 25:
        bg_image_name = "6.png"
    else:  # 26 ~ 30번 카드
        bg_image_name = "7.png"

    # 배경 이미지 로드
    background_path = SCRIPT_DIR / "asset" / bg_image_name
    if not background_path.exists():
        print(f"❌ 배경 이미지 없음: {background_path}, 다음 카드로 건너뜁니다.")
        continue
    
    card = Image.open(background_path).convert("RGBA")
    draw = ImageDraw.Draw(card)
    
    max_text_width = CARD_WIDTH - LEFT_MARGIN - RIGHT_MARGIN
    
    # --- 상단부터 순서대로 텍스트 그리기 ---
    y = TOP_MARGIN
    # 헤더
    header_text = f"[오늘의 유머_뉴스패러디 {idx+1}/{len(df)}]"
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), header_text, header_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += SECTION_GAP
    
    # ou_title
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), row.get('ou_title'), ou_title_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += SECTION_GAP
    
    # [라떼는 말이야] 소제목
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), "[라떼는 말이야]", section_title_font, LIGHT_GRAY_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += 15

    # latte
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), row.get('latte'), latte_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += SECTION_GAP
    
    # [아재 생각] 소제목
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), "[오유_생각]", section_title_font, LIGHT_GRAY_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    y += 15

    # ou_think
    y = draw_text_with_shadow(draw, (LEFT_MARGIN, y), row.get('ou_think'), ou_think_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)

    # --- 하단 텍스트 그리기 ---
    source_text = "출처: " + row.get('source_url', '')
    original_title_text = "원문: " + row.get('original_title', '')
    disclaimer_text = row.get('disclaimer', '')
    
    footer_line_height = footer_font.size * LINE_SPACING_RATIO
    source_height = len(get_wrapped_lines(source_text, footer_font, max_text_width)) * footer_line_height
    disclaimer_height = len(get_wrapped_lines(disclaimer_text, footer_font, max_text_width)) * footer_line_height
    original_title_height = len(get_wrapped_lines(original_title_text, footer_font, max_text_width)) * footer_line_height
    
    y_source_start = CARD_HEIGHT - BOTTOM_MARGIN - source_height
    y_disclaimer_start = y_source_start - disclaimer_height - 15
    y_original_title_start = y_disclaimer_start - original_title_height - 15

    draw_text_with_shadow(draw, (LEFT_MARGIN, y_original_title_start), original_title_text, footer_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    draw_text_with_shadow(draw, (LEFT_MARGIN, y_disclaimer_start), disclaimer_text, footer_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)
    draw_text_with_shadow(draw, (LEFT_MARGIN, y_source_start), source_text, footer_font, WHITE_COLOR, max_text_width, line_spacing_ratio=LINE_SPACING_RATIO)

    # 카드 저장
    out_path = output_dir / f'parody_card_{idx+1:02d}.png'
    card.save(out_path)
    print(f"✅ 카드 저장 완료: {out_path}")

print("\n6. 작업 완료!") 