import os
import sys
import glob
import random
import gspread
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import time
import httplib2
from googleapiclient.errors import HttpError

# get_gsheet 함수를 직접 정의 (utils 폴더 의존성 제거)
import gspread
from google.oauth2.service_account import Credentials
import traceback

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]

def get_gspread_client():
    """gspread 클라이언트를 인증하고 반환합니다."""
    try:
        # GitHub Actions 환경에서는 환경변수에서 인증 정보 가져오기
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            print("[GitHub] GitHub Actions 환경에서 Google Sheets 인증 중...")
            creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
            if not creds_json:
                raise ValueError("GOOGLE_CREDENTIALS_JSON 환경변수가 설정되지 않았습니다.")
            
            import json
            creds_data = json.loads(creds_json)
            creds = Credentials.from_service_account_info(creds_data, scopes=SCOPE)
        else:
            # 로컬 환경에서는 service_account.json 파일 사용
            print("[로컬] 로컬 환경에서 Google Sheets 인증 중...")
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            creds_file = os.path.join(parent_dir, 'config', 'service_account.json')
            
            print(f"[검색] 인증 파일 경로 확인: {creds_file}")
            print(f"   - 현재 디렉토리: {current_dir}")
            print(f"   - 상위 디렉토리: {parent_dir}")
            print(f"   - 인증 파일 존재: {os.path.exists(creds_file)}")
            
            if not os.path.exists(creds_file):
                raise FileNotFoundError(f"인증 파일 '{creds_file}'을(를) 찾을 수 없습니다.")
            
            creds = Credentials.from_service_account_file(creds_file, scopes=SCOPE)
        
        client = gspread.authorize(creds)
        print("[OK] Google Sheets 인증 성공!")
        return client
    except Exception as e:
        print(f"[ERROR] Google Sheets 인증 실패: {e}")
        raise

def get_gsheet(spreadsheet_id, worksheet_name=None):
    """주어진 ID와 워크시트 이름으로 gspread 워크시트 객체를 반환합니다."""
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        if worksheet_name:
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                print(f"  - 워크시트 '{worksheet_name}'을(를) 찾을 수 없어 새로 생성합니다.")
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
        else:
            worksheet = spreadsheet.sheet1
        return worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"  ! 스프레드시트 ID '{spreadsheet_id}'을(를) 찾을 수 없습니다.")
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"  ! 구글 시트 워크시트를 가져오는 중 오류 발생: {e}")
        traceback.print_exc()
        raise

print("[OK] get_gsheet 함수가 직접 정의되었습니다 (utils 폴더 의존성 없음)")

# 유튜브 업로드를 위한 권한 범위
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]

# 쿠팡파트너스 공지사항 (법적 의무)
COUPANG_NOTICE = "이 포스팅은 쿠팡파트너스 활동으로 일정보수를 지급받습니다."

# [핫] 시니어 SEO 최적화 키워드 (50-70대 타겟)
SENIOR_SEARCH_KEYWORDS = [
    "시니어뉴스", "라떼는말이야", "50대현실", "60대공감", "70대걱정",
    "시니어유머", "실버세대", "현실직시", "세대공감", "베이비부머"
]

VIRAL_SENIOR_HOOKS = [
    "실화냐??", "이게맞나??", "세상에나!!!", "아이고참!!!", "말도안돼!!!", 
    "어이없네!!", "답답해!!", "화나네!!", "억울해!!"
]

def get_today_parody_title_and_keyword():
    """구글 시트에서 오늘의 패러디 제목과 키워드를 간단하게 가져옵니다."""
    try:
        # 기존 스프레드시트 ID와 시트명 유지
        SHEET_ID = '1yZeYdyGZpR6yrRn5JNa1-JdQtO9vKLX6NPWhqpmT6kw'
        SHEET_NAME = 'senior_ou_news_parody_v3'
        
        print(f"[검색] 구글 시트에서 패러디 데이터 가져오는 중...")
        print(f"   - 시트 ID: {SHEET_ID}")
        print(f"   - 시트명: {SHEET_NAME}")
        
        worksheet = get_gsheet(SHEET_ID, SHEET_NAME)
        all_values = worksheet.get_all_values()
        
        print(f"[통계] 총 {len(all_values)}개 행 발견")
        
        # 한국 시간대 사용
        import pytz
        seoul_tz = pytz.timezone('Asia/Seoul')
        kst_now = datetime.now(seoul_tz)
        today_str = kst_now.strftime('%Y-%m-%d, %a').lower()
        
        print(f"[날짜] 한국 시간 기준 오늘 날짜: {today_str}")
        
        # 오늘 데이터 검색 (첫 번째 행은 헤더)
        for i, row in enumerate(all_values[1:], 1):
            if len(row) >= 4 and row[0] == today_str:
                parody_title = row[1] if len(row) > 1 else ''  # ou_title 컬럼
                keyword = row[3] if len(row) > 3 else ''       # keyword 컬럼
                
                print(f"[OK] 오늘 데이터 발견 (행 {i}):")
                print(f"   - 패러디 제목: {parody_title[:50]}...")
                print(f"   - 키워드: {keyword}")
                
                return parody_title, keyword
        
        # 오늘 데이터가 없으면 최근 데이터 사용
        print(f"[경고] 오늘({today_str}) 데이터를 찾을 수 없습니다.")
        print(f"[팁] 최근 데이터 확인 중...")
        
        for days_back in range(1, 8):
            check_date = (kst_now - timedelta(days=days_back)).strftime('%Y-%m-%d, %a').lower()
            for i, row in enumerate(all_values[1:], 1):
                if len(row) >= 4 and row[0] == check_date:
                    parody_title = row[1] if len(row) > 1 else ''
                    keyword = row[3] if len(row) > 3 else ''
                    
                    print(f"[OK] {days_back}일 전 데이터 사용: {check_date}")
                    print(f"   - 패러디 제목: {parody_title[:50]}...")
                    print(f"   - 키워드: {keyword}")
                    
                    return parody_title, keyword
        
        print(f"[ERROR] 최근 7일 데이터도 없습니다.")
        return None, None
        
    except Exception as e:
        print(f"[ERROR] 패러디 데이터 가져오기 실패: {e}")
        print(f"오류 타입: {type(e).__name__}")
        return None, None

def generate_senior_engaging_title(parody_title, keyword):
    """시니어 뉴스 패러디 제목을 생성합니다."""
    if parody_title:
        # 제목 길이 제한 (YouTube 100자 제한 고려)
        if len(parody_title) > 60:  # 쿠팡 문구 길이 고려
            parody_title = parody_title[:60] + "..."
        
        # 시니어 관심 키워드 추가
        seo_keyword = random.choice(SENIOR_SEARCH_KEYWORDS)
        
        # 제목 최적화: 패러디제목 + 시니어키워드 + 쿠팡문구
        final_title = f"{parody_title} {seo_keyword} | {COUPANG_NOTICE}"
    else:
        # 시니어 관심 이슈 기본 템플릿
        hook = random.choice(VIRAL_SENIOR_HOOKS)
        keyword = random.choice(SENIOR_SEARCH_KEYWORDS)
        
        title_templates = [
            f"연금 68세부터? {hook} {keyword} | {COUPANG_NOTICE}",
            f"물가 또 올랐네? {hook} {keyword} | {COUPANG_NOTICE}",
            f"전기료 폭탄! {hook} {keyword} | {COUPANG_NOTICE}",
            f"의료비 인상! {hook} {keyword} | {COUPANG_NOTICE}",
            f"치매 걱정돼! {hook} {keyword} | {COUPANG_NOTICE}",
            f"집값 또 뛰었네? {hook} {keyword} | {COUPANG_NOTICE}",
            f"건강보험료 올라! {hook} {keyword} | {COUPANG_NOTICE}",
            f"세금 더 내라고? {hook} {keyword} | {COUPANG_NOTICE}",
            f"교통비도 인상! {hook} {keyword} | {COUPANG_NOTICE}",
            f"식료품값 천정부지! {hook} {keyword} | {COUPANG_NOTICE}",
        ]
        final_title = random.choice(title_templates)
    
    # 최종 길이 체크 (100자 제한)
    if len(final_title) > 100:
        final_title = final_title[:97] + "..."
    
    return final_title

def get_fixed_description(keyword):
    """시니어 뉴스 패러디 고정 설명을 생성합니다."""
    import pytz
    seoul_tz = pytz.timezone('Asia/Seoul')
    today = datetime.now(seoul_tz).strftime('%Y년 %m월 %d일')
    
    return f"""{COUPANG_NOTICE}

{today} 시니어뉴스패러디 | 라떼는말이야 시리즈

50대 60대 70대 시니어가 "진짜 맞는 말이네!" 하는 현실공감 뉴스해석!

오늘의 핫이슈 '{keyword}'를 유머와 함께 쉽게 풀어드려요
가족 단톡방에서 써먹을 시니어 개그까지 덤으로!

구독 + 좋아요 + 알림설정으로 매일 뉴스패러디 받아보세요!

#시니어뉴스 #라떼는말이야 #50대 #60대 #70대 #시니어유머 #현실공감 #세대공감 #실버세대 #베이비부머 #시사패러디 #뉴스해석 #현실직시 #물가 #연금 #의료비 #건강보험 #요양보험 #치매예방 #정치유머 #경제뉴스 #생활이슈 #노후준비 #시니어라이프"""
    
# 시니어 뉴스 패러디 고정 태그 리스트
FIXED_TAGS = [
    '시니어뉴스', '라떼는말이야', '50대', '60대', '70대', '시니어유머', '실버세대', '현실공감', '세대공감',
    '뉴스패러디', '시사패러디', '정치유머', '경제뉴스', '아재개그', '현실직시', '뉴스해석', '사회이슈',
    '연금개혁', '물가상승', '의료비', '건강보험료', '요양보험', '국민연금', '치매예방', '노후준비',
    '실버라이프', '생활밀착뉴스', '세대갭', '어르신', '노인복지', '시니어라이프', '오늘뉴스',
    '시사정리', '뉴스요약', '이슈분석', '사회현상', '트렌드분석', '현실토크', '베이비부머',
    '물가', '연금', '의료비', '건강보험', '요양보험', '치매예방', '정치유머', '경제뉴스', '생활이슈', '노후준비'
]

def get_authenticated_service():
    """인증된 YouTube API 서비스 객체를 생성하여 반환합니다."""
    try:
        # GitHub Actions 환경에서는 환경변수에서 토큰을 가져옴
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            print("[GitHub] GitHub Actions 환경에서 실행 중 - 환경변수에서 토큰 로드")
            token_json = os.environ.get('YOUTUBE_TOKEN_JSON')
            if not token_json:
                print("[ERROR] GitHub Actions 환경에서 YOUTUBE_TOKEN_JSON 환경변수를 찾을 수 없습니다.")
                return None
            
            try:
                # JSON 문자열을 파싱하여 Credentials 객체 생성 (YouTube용 Credentials 사용)
                import json
                token_data = json.loads(token_json)
                from google.oauth2.credentials import Credentials as UserCredentials
                creds = UserCredentials.from_authorized_user_info(token_data, SCOPES)
                print("[OK] GitHub Secrets에서 토큰 로드 성공")
            except Exception as e:
                print(f"[ERROR] GitHub Secrets 토큰 파싱 실패: {e}")
                return None
        else:
            # 로컬 환경에서는 토큰 파일 사용
            print("[로컬] 로컬 환경에서 실행 중 - 토큰 파일에서 로드")
            script_dir = os.path.dirname(os.path.abspath(__file__))
            token_path = os.path.join(script_dir, 'token.json')
            
            # 토큰 파일 존재 확인
            if not os.path.exists(token_path):
                print(f"[ERROR] 토큰 파일이 없습니다: {token_path}")
                return None
            
            # 토큰 파일 크기 확인
            token_size = os.path.getsize(token_path)
            if token_size == 0:
                print("[ERROR] 토큰 파일이 비어있습니다.")
                return None
            
            print(f"[파일] 토큰 파일 크기: {token_size} bytes")
            print(f"[파일] 토큰 파일 경로: {token_path}")
            
            # 토큰 로드 및 검증 (YouTube용 Credentials 사용)
            from google.oauth2.credentials import Credentials as UserCredentials
            creds = UserCredentials.from_authorized_user_file(token_path, SCOPES)
        
        # 토큰 유효성 확인 및 자동 새로고침
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                print("[새로고침] 토큰이 만료되었습니다. 자동 새로고침을 시도합니다...")
                try:
                    creds.refresh(Request())
                    print("[OK] 토큰 자동 새로고침 성공!")
                    
                    # GitHub Actions 환경에서는 토큰 파일 저장하지 않음
                    if os.environ.get('GITHUB_ACTIONS') != 'true':
                        # 로컬 환경에서만 새로고침된 토큰 저장
                        with open(token_path, 'w') as f:
                            f.write(creds.to_json())
                        print("[저장] 새로고침된 토큰 저장 완료")
                    else:
                        print("[팁] GitHub Actions 환경에서는 토큰 파일 저장을 건너뜁니다.")
                except Exception as refresh_error:
                    print(f"[ERROR] 토큰 자동 새로고침 실패: {refresh_error}")
                    return None
            else:
                print("[ERROR] 토큰이 유효하지 않습니다.")
                return None
        
        # YouTube API 서비스 생성
        youtube = build('youtube', 'v3', credentials=creds)
        
        # 연결 테스트 (간단한 검증)
        try:
            request = youtube.channels().list(part='snippet', mine=True)
            response = request.execute()
            if response.get('items'):
                channel_title = response['items'][0].get('snippet', {}).get('title', 'Unknown')
                print(f"[OK] YouTube API 연결 성공! 채널: {channel_title}")
            else:
                print("[경고] 채널 정보를 가져올 수 없습니다. (업로드는 계속 진행)")
        except Exception as test_error:
            print(f"[경고] 연결 테스트 실패 (업로드는 계속 진행): {test_error}")
        
        return youtube
        
    except Exception as e:
        print(f"[ERROR] YouTube 인증 오류: {e}")
        print(f"오류 타입: {type(e).__name__}")
        print("[팁] 토큰 파일 형식을 확인해주세요.")
        return None

def upload_video(file_path, title, description, tags, max_retries=3):
    """지정된 동영상 파일을 YouTube에 업로드합니다."""
    youtube = get_authenticated_service()
    if youtube is None:
        print("YouTube API 인증 실패. 업로드를 중단합니다.")
        return None

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '24',
            'defaultLanguage': 'ko',
            'defaultAudioLanguage': 'ko'
        },
        'status': {
            'privacyStatus': 'private',
            'selfDeclaredMadeForKids': False
        }
    }

    media = MediaFileUpload(
        file_path,
        chunksize=1024*1024,  # 1MB
        resumable=True,
        mimetype='video/mp4'
    )

    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    retry = 0
    response = None
    error = None
    print(f"[시작] 시니어 뉴스 패러디 업로드를 시작합니다... (파일: {file_path})")
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                print(f"업로드 진행률: {int(status.progress() * 100)}%")
        except HttpError as e:
            if e.resp.status in [500, 502, 503, 504]:
                error = f"서버 오류: {e.resp.status}, 재시도 중..."
            else:
                print(f"API 오류: {e}\n응답 내용: {e.content}")
                break
        except Exception as e:
            error = f"예외 발생: {e}"
        if error:
            retry += 1
            if retry > max_retries:
                print(f"최대 재시도 횟수 초과. 업로드 실패: {error}")
                return None
            sleep_time = 2 ** retry
            print(f"{error} {sleep_time}초 후 재시도...")
            time.sleep(sleep_time)
            error = None
        else:
            retry = 0
    if response:
        print(f"[OK] 업로드 성공! 영상 ID: {response['id']}")
        print(f"YouTube API 응답: {response}")
        return response['id']
    else:
        print("[ERROR] 업로드 실패: 응답 없음")
        return None

if __name__ == '__main__':
    print("[검색] 오늘의 시니어 뉴스 독자 관심도 최적화 중...")
    print(f"[시간] 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # GitHub Actions 환경 정보 출력
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        print("[GitHub] GitHub Actions 환경에서 실행 중")
        print(f"   - 워크스페이스: {os.environ.get('GITHUB_WORKSPACE', 'N/A')}")
        print(f"   - 러너 OS: {os.environ.get('RUNNER_OS', 'N/A')}")
        print(f"   - 현재 디렉토리: {os.getcwd()}")
        print(f"   - 환경 변수: GITHUB_ACTIONS={os.environ.get('GITHUB_ACTIONS')}")
    else:
        print("[로컬] 로컬 환경에서 실행 중")
    
    try:
        # 오늘의 패러디 제목과 키워드 가져오기
        parody_title, keyword = get_today_parody_title_and_keyword()
        
        if not parody_title and not keyword:
            print("[경고] 패러디 데이터가 없어 기본 템플릿을 사용합니다.")
            parody_title = "시니어뉴스패러디"
            keyword = "시니어뉴스"
        
        # 시니어 독자 관심도 최적화된 제목 생성
        final_title = generate_senior_engaging_title(parody_title, keyword)
        print(f"[타겟] 생성된 제목 ({len(final_title)}자): {final_title}")
        
        # 시니어 독자 관심도 최적화된 설명 생성
        description = get_fixed_description(keyword)
        tags = FIXED_TAGS
        
        print(f"[설명] 설명 길이: {len(description)}자")
        print(f"[태그] 태그 수: {len(tags)}개")
        print(f"[타겟] 타겟: 50-70대 시니어 세대")
        print(f"[법적] 쿠팡파트너스 의무사항 준수 완료")
        print(f"[목록] 패러디 제목: {parody_title}")
        print(f"[키워드] 키워드: {keyword}")
        
        # 업로드할 영상 파일 찾기 (상위 디렉토리의 parody_video 폴더)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(script_dir)
        video_dir = os.path.join(parent_dir, 'parody_video')
        
        print(f"[폴더] 비디오 디렉토리 확인: {video_dir}")
        print(f"   - 스크립트 위치: {script_dir}")
        print(f"   - 상위 디렉토리: {parent_dir}")
        print(f"   - 비디오 디렉토리: {video_dir}")
        print(f"   - 디렉토리 존재: {os.path.exists(video_dir)}")
        
        if os.path.exists(video_dir):
            print(f"   - 디렉토리 내용:")
            try:
                for item in os.listdir(video_dir):
                    item_path = os.path.join(video_dir, item)
                    if os.path.isfile(item_path):
                        size = os.path.getsize(item_path) / (1024 * 1024)  # MB
                        mtime = datetime.fromtimestamp(os.path.getmtime(item_path))
                        print(f"     [파일] {item} ({size:.1f}MB, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
                    else:
                        print(f"     [폴더] {item}/")
            except Exception as e:
                print(f"     [ERROR] 디렉토리 읽기 실패: {e}")
        
        video_files = glob.glob(os.path.join(video_dir, '*.mp4'))
        print(f"[동영상] 발견된 MP4 파일: {len(video_files)}개")
        
        if not video_files:
            print(f"[ERROR] '{video_dir}' 폴더에 업로드할 동영상 파일이 없습니다.")
            print(f"[팁] 전체 디렉토리 검색 중...")
            
            # 전체 디렉토리에서 MP4 파일 검색 (상위 디렉토리부터)
            all_mp4_files = []
            search_root = parent_dir  # 상위 디렉토리에서 검색
            for root, dirs, files in os.walk(search_root):
                for file in files:
                    if file.endswith('.mp4'):
                        file_path = os.path.join(root, file)
                        all_mp4_files.append(file_path)
            
            if all_mp4_files:
                print(f"[검색] 다른 위치에서 {len(all_mp4_files)}개 MP4 파일 발견:")
                for file_path in all_mp4_files:
                    size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                    mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    print(f"   [동영상] {file_path} ({size:.1f}MB, {mtime.strftime('%Y-%m-%d %H:%M:%S')})")
            
            exit(1)
        
        # 가장 최근 파일 선택 (파일명의 날짜 기준으로 변경)
        def get_date_from_filename(file_path):
            """파일명에서 날짜를 추출합니다 (senior_ou_news_parody_YYYYMMDD_HHMMSS.mp4 형식)"""
            filename = os.path.basename(file_path)
            try:
                # senior_ou_news_parody_20250727_072241.mp4 형식에서 날짜 추출
                if filename.startswith('senior_ou_news_parody_'):
                    date_part = filename.replace('senior_ou_news_parody_', '').replace('.mp4', '')
                    # YYYYMMDD_HHMMSS 형식을 datetime으로 변환
                    date_str = date_part.split('_')[0]  # YYYYMMDD
                    time_str = date_part.split('_')[1]  # HHMMSS
                    
                    year = int(date_str[:4])
                    month = int(date_str[4:6])
                    day = int(date_str[6:8])
                    hour = int(time_str[:2])
                    minute = int(time_str[2:4])
                    second = int(time_str[4:6])
                    
                    return datetime(year, month, day, hour, minute, second)
                else:
                    # 파일명 형식이 다르면 파일 시스템 시간 사용
                    return datetime.fromtimestamp(os.path.getmtime(file_path))
            except:
                # 오류 발생 시 파일 시스템 시간 사용
                return datetime.fromtimestamp(os.path.getmtime(file_path))
        
        # 파일명의 날짜 기준으로 정렬하여 가장 최근 파일 선택
        latest_video = max(video_files, key=get_date_from_filename)
        latest_date = get_date_from_filename(latest_video)
        
        print(f"[동영상] 발견된 모든 MP4 파일 (파일명 날짜 순):")
        for video_file in sorted(video_files, key=get_date_from_filename, reverse=True):
            file_date = get_date_from_filename(video_file)
            size = os.path.getsize(video_file) / (1024 * 1024)  # MB
            print(f"   [동영상] {os.path.basename(video_file)} ({size:.1f}MB, {file_date.strftime('%Y-%m-%d %H:%M:%S')})")
        
        print(f"[동영상] 선택된 최신 동영상: {latest_video}")
        print(f"[날짜] 파일 생성 시간: {latest_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 파일 크기 확인
        file_size = os.path.getsize(latest_video) / (1024 * 1024)  # MB
        print(f"[통계] 파일 크기: {file_size:.1f} MB")
        
        # 업로드 실행
        video_id = upload_video(
            latest_video,
            final_title,
            description,
            tags
        )
        
        # 업로드 성공/실패와 관계없이 오래된 파일 정리 (로컬에서만)
        print(f"\n🧹 오래된 동영상 파일 정리 중...")
        deleted_count = 0
        
        # GitHub Actions 환경에서는 파일 삭제 건너뛰기
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            print("[경고] GitHub Actions 환경에서는 파일 삭제를 건너뜁니다.")
            print("[팁] 로컬에서 수동으로 오래된 파일을 정리해주세요.")
        else:
            # 로컬에서만 파일 삭제 실행
            for f in glob.glob(os.path.join(video_dir, '*.mp4')):
                if os.path.abspath(f) != os.path.abspath(latest_video):
                    try:
                        os.remove(f)
                        deleted_count += 1
                        print(f"[삭제] 파일 삭제 완료: {os.path.basename(f)}")
                    except Exception as e:
                        print(f"[경고] 파일 삭제 실패: {os.path.basename(f)} ({e})")
            
            print(f"[통계] 정리 결과: {deleted_count}개 파일 삭제됨")
        
        if video_id:
            print(f"\n[완료] 시니어 독자 관심도 최적화된 뉴스 패러디 업로드 완료!")
            print(f"[영상] 영상 URL: https://youtu.be/{video_id}")
            print(f"[검색] 검색 최적화: 시니어뉴스, 라떼는말이야, 50대, 60대, 70대")
            print(f"[법적] 쿠팡파트너스 의무사항 완료")
            
            # 성공 로그
            print(f"\n[OK] 업로드 성공 로그:")
            print(f"   - 영상 ID: {video_id}")
            print(f"   - 제목: {final_title}")
            print(f"   - 파일: {os.path.basename(latest_video)}")
            print(f"   - 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        else:
            print("[ERROR] 업로드에 실패했습니다.")
            print(f"[저장] 최신 파일은 보존됨: {os.path.basename(latest_video)}")
            exit(1)
            
    except Exception as e:
        print(f"[ERROR] 예상치 못한 오류 발생: {e}")
        print(f"오류 타입: {type(e).__name__}")
        exit(1)
