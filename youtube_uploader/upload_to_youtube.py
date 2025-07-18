import os
import glob
import random
import gspread
import sys
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import time
import httplib2
from googleapiclient.errors import HttpError

# 상위 폴더의 common_utils 모듈을 import하기 위한 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from common_utils import get_gspread_client

# 유튜브 업로드를 위한 권한 범위
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]

# 쿠팡파트너스 공지사항 (법적 의무)
COUPANG_NOTICE = "이 포스팅은 쿠팡파트너스 활동으로 일정보수를 지급받습니다."

# 🔥 시니어 SEO 최적화 키워드 (50-70대 타겟)
SENIOR_SEARCH_KEYWORDS = [
    "시니어뉴스", "라떼는말이야", "50대현실", "60대공감", "70대걱정",
    "시니어유머", "실버세대", "현실직시", "세대공감", "베이비부머"
]

VIRAL_SENIOR_HOOKS = [
    "실화냐??", "이게맞나??", "세상에나!!!", "아이고참!!!", "말도안돼!!!", 
    "어이없네!!", "답답해!!", "화나네!!", "억울해!!"
]

def get_latest_parody_titles():
    """구글 시트에서 오늘 생성된 패러디 제목들을 가져옵니다."""
    try:
        config = {}
        try:
            with open('asset/rawdata.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        config[key.strip()] = value.strip()
        except FileNotFoundError:
            return []
        
        if '패러디결과_스프레드시트_ID' not in config:
            return []
        
        g_client = get_gspread_client()
        spreadsheet = g_client.open_by_key(config['패러디결과_스프레드시트_ID'])
        worksheet = spreadsheet.worksheet('senior_ou_news_parody_v3')
        
        # 오늘 날짜 데이터만 필터링
        today_str = datetime.now().strftime('%Y-%m-%d, %a').lower()
        all_data = worksheet.get_all_records()
        
        today_titles = []
        for row in all_data:
            if row.get('today') == today_str and row.get('ou_title'):
                today_titles.append(row['ou_title'])
        
        return today_titles[:5]  # 최대 5개만 반환
    except Exception as e:
        print(f"패러디 제목 가져오기 실패: {e}")
        return []

def generate_seo_optimized_title():
    """SEO 최적화 + 쿠팡파트너스 의무준수 제목 생성"""
    parody_titles = get_latest_parody_titles()
    
    if parody_titles:
        # 실제 패러디 제목 활용
        selected_title = random.choice(parody_titles)
        
        # 제목 길이 제한 (YouTube 100자 제한 고려)
        if len(selected_title) > 60:  # 쿠팡 문구 길이 고려
            selected_title = selected_title[:60] + "..."
        
        # SEO 키워드 추가
        seo_keyword = random.choice(SENIOR_SEARCH_KEYWORDS)
        
        # 제목 최적화: 핵심내용 + SEO키워드 + 쿠팡문구
        title = f"{selected_title} {seo_keyword} | {COUPANG_NOTICE}"
        
    else:
        # 기본 템플릿 (검색 최적화)
        hook = random.choice(VIRAL_SENIOR_HOOKS)
        keyword = random.choice(SENIOR_SEARCH_KEYWORDS)
        
        title_templates = [
            f"연금 68세부터? {hook} {keyword} | {COUPANG_NOTICE}",
            f"물가 또 올랐네? {hook} {keyword} | {COUPANG_NOTICE}",
            f"전기료 폭탄! {hook} {keyword} | {COUPANG_NOTICE}",
            f"의료비 인상! {hook} {keyword} | {COUPANG_NOTICE}",
            f"치매 걱정돼! {hook} {keyword} | {COUPANG_NOTICE}",
            f"집값 또 뛰었네! {hook} {keyword} | {COUPANG_NOTICE}",
            f"건강보험료 올라! {hook} {keyword} | {COUPANG_NOTICE}",
            f"세금 더 내라고? {hook} {keyword} | {COUPANG_NOTICE}",
            f"교통비도 인상! {hook} {keyword} | {COUPANG_NOTICE}",
            f"식료품값 천정부지! {hook} {keyword} | {COUPANG_NOTICE}",
        ]
        title = random.choice(title_templates)
    
    # 최종 길이 체크 (100자 제한)
    if len(title) > 100:
        title = title[:97] + "..."
    
    return title

def get_seo_optimized_description():
    """검색 최적화 + 쿠팡파트너스 의무준수 설명"""
    import pytz
    seoul_tz = pytz.timezone('Asia/Seoul')
    today = datetime.now(seoul_tz).strftime('%Y년 %m월 %d일')
    
    # 설명 맨 앞에 쿠팡파트너스 문구 (법적 의무)
    description = f"""{COUPANG_NOTICE}

🔥 {today} 시니어뉴스패러디 | 라떼는말이야 시리즈

📺 50대 60대 70대 시니어가 "진짜 맞는 말이네!" 하는 현실공감 뉴스해석!

⭐ 오늘의 핵심 시니어 이슈:
• 국민연금개혁 - 68세 수령, 우리 세대는?
• 물가상승 - 라떼 한 잔이 5천원 시대
• 의료비폭탄 - 아프면 안 되는 현실
• 건강보험료 - 매년 오르는 부담
• 요양보험 - 노후 돌봄 걱정
• 치매예방 - 건강한 노후 준비

🎯 시니어세대 맞춤 콘텐츠:
✓ 복잡한 뉴스를 쉽고 재미있게 해석
✓ "우리 때는 말이야" 라떼 시리즈
✓ 50대 60대 70대 시니어 공감 100%
✓ 가족 단톡방 공유용 현실직시 유머
✓ 시니어 관점으로 풀어보는 시사이슈

📱 이런 분들께 추천:
• 딱딱한 뉴스가 지겨운 시니어
• 세대공감 원하는 50대 60대 70대
• 자녀들과 소통하고 싶은 실버세대
• 현실적 관점으로 뉴스 보고 싶은 분
• "라떼는 말이야"가 입에 붙은 어르신

🔥 매일 업데이트되는 시니어뉴스:
• 연금/의료비/물가 등 생활밀착 이슈
• 건강관리/요양보험 등 노후 정보
• 정치/경제 뉴스의 시니어 관점 해석  
• 과거와 현재 비교한 세대갭 분석
• 손자녀 세대와의 소통을 위한 트렌드

👨‍👩‍👧‍👦 가족들과 함께 보며 세대 소통하세요!
💬 댓글로 여러분의 "라떼" 경험담도 공유해주세요!

🔔 구독 + 좋아요 + 알림설정으로 매일 뉴스패러디 받아보세요!

⚠️ 면책조항:
• 본 콘텐츠는 패러디/유머 목적입니다
• 특정 정치적 입장을 대변하지 않습니다  
• 투자나 정책 관련 내용은 참고용입니다
• 개인적 판단과 전문가 상담이 중요합니다

#시니어뉴스 #라떼는말이야 #50대 #60대 #70대 #시니어유머 #현실공감 #세대공감 #실버세대 #베이비부머 #시사패러디 #뉴스해석 #현실직시 #물가 #연금 #의료비 #건강보험 #요양보험 #치매예방 #정치유머 #경제뉴스 #생활이슈 #노후준비 #시니어라이프"""
    
    return description

def get_seo_optimized_tags():
    """검색 최적화된 태그 (50개 한도 내, 중복 제거)"""
    
    # 1순위: 핵심 시니어 키워드 (높은 검색량)
    core_tags = [
        "시니어뉴스", "라떼는말이야", "50대", "60대", "70대", 
        "시니어유머", "실버세대", "현실공감", "세대공감"
    ]
    
    # 2순위: 시니어 특화 이슈 키워드 (타겟팅)
    issue_tags = [
        "연금개혁", "물가상승", "의료비", "건강보험료", "요양보험",
        "국민연금", "치매예방", "노후준비", "은퇴준비", "건강관리"
    ]
    
    # 3순위: 콘텐츠 형태 키워드
    content_tags = [
        "뉴스패러디", "시사패러디", "정치유머", "경제뉴스", 
        "아재개그", "현실직시", "뉴스해석", "사회이슈"
    ]
    
    # 4순위: 롱테일 키워드 (경쟁 낮음, 중복 제거)
    longtail_tags = [
        "실버라이프", "생활밀착뉴스", "세대갭", 
        "어르신", "노인복지", "시니어라이프"
    ]
    
    # 5순위: 검색 유도 키워드
    search_tags = [
        "오늘뉴스", "시사정리", "뉴스요약", "이슈분석",
        "사회현상", "트렌드분석", "현실토크"
    ]
    
    # 태그 통합 (중복 제거 후 50개 한도)
    all_tags = list(dict.fromkeys(core_tags + issue_tags + content_tags + longtail_tags + search_tags))
    return all_tags[:49]  # 여유분 1개 남김

def get_authenticated_service():
    """인증된 YouTube API 서비스 객체를 생성하여 반환합니다."""
    try:
        # 토큰 파일 존재 확인
        if not os.path.exists('youtube_uploader/token.json'):
            print("❌ 토큰 파일이 없습니다: youtube_uploader/token.json")
            return None
        
        # 토큰 파일 크기 확인
        token_size = os.path.getsize('youtube_uploader/token.json')
        if token_size == 0:
            print("❌ 토큰 파일이 비어있습니다.")
            return None
        
        print(f"📄 토큰 파일 크기: {token_size} bytes")
        
        # 토큰 로드 및 검증
        creds = Credentials.from_authorized_user_file('youtube_uploader/token.json', SCOPES)
        
        # 토큰 유효성 확인 (새로운 토큰이므로 만료 여부만 체크)
        if not creds.valid:
            print("❌ 토큰이 유효하지 않습니다.")
            print("💡 새로운 토큰을 GitHub Secrets에 업데이트해주세요.")
            return None
        
        # YouTube API 서비스 생성
        youtube = build('youtube', 'v3', credentials=creds)
        
        # 연결 테스트 (간단한 검증)
        try:
            request = youtube.channels().list(part='snippet', mine=True)
            response = request.execute()
            if response.get('items'):
                channel_title = response['items'][0].get('snippet', {}).get('title', 'Unknown')
                print(f"✅ YouTube API 연결 성공! 채널: {channel_title}")
            else:
                print("⚠️ 채널 정보를 가져올 수 없습니다. (업로드는 계속 진행)")
        except Exception as test_error:
            print(f"⚠️ 연결 테스트 실패 (업로드는 계속 진행): {test_error}")
        
        return youtube
        
    except Exception as e:
        print(f"❌ YouTube 인증 오류: {e}")
        print(f"오류 타입: {type(e).__name__}")
        print("💡 토큰 파일 형식을 확인해주세요.")
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
    print(f"🚀 시니어 뉴스 패러디 업로드를 시작합니다... (파일: {file_path})")
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
        print(f"✅ 업로드 성공! 영상 ID: {response['id']}")
        print(f"YouTube API 응답: {response}")
        return response['id']
    else:
        print("❌ 업로드 실패: 응답 없음")
        return None

if __name__ == '__main__':
    print("🔍 오늘의 시니어 패러디 SEO 최적화 중...")
    print(f"⏰ 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # SEO 최적화된 제목 생성 (쿠팡파트너스 의무준수)
        title = generate_seo_optimized_title()
        print(f"🎯 생성된 제목 ({len(title)}자): {title}")
        
        # SEO 최적화된 설명 생성 (쿠팡파트너스 맨 앞 배치)
        description = get_seo_optimized_description()
        tags = get_seo_optimized_tags()
        
        print(f"📝 설명 길이: {len(description)}자")
        print(f"🏷️ 태그 수: {len(tags)}개")
        print(f"🎯 타겟: 40-60대 SEO 최적화 완료")
        print(f"⚖️ 쿠팡파트너스 의무사항 준수 완료")
        
        # 업로드할 영상 파일 찾기
        video_dir = 'parody_video'
        video_files = glob.glob(os.path.join(video_dir, '*.mp4'))
        
        if not video_files:
            print(f"❌ '{video_dir}' 폴더에 업로드할 동영상 파일이 없습니다.")
            exit(1)
        
        # 가장 최근 파일 선택
        latest_video = max(video_files, key=os.path.getmtime)
        print(f"📹 업로드할 동영상: {latest_video}")
        
        # 파일 크기 확인
        file_size = os.path.getsize(latest_video) / (1024 * 1024)  # MB
        print(f"📊 파일 크기: {file_size:.1f} MB")
        
        # 업로드 실행
        video_id = upload_video(
            latest_video,
            title,
            description,
            tags
        )
        
        if video_id:
            print(f"\n🎉 SEO 최적화된 시니어 뉴스 패러디 업로드 완료!")
            print(f"📺 영상 URL: https://youtu.be/{video_id}")
            print(f"🔍 검색 최적화: 시니어뉴스, 라떼는말이야, 50대, 60대, 70대")
            print(f"⚖️ 쿠팡파트너스 의무사항 완료")
            
            # 업로드한 파일(latest_video)은 남기고, 나머지 .mp4 파일 삭제
            for f in glob.glob(os.path.join(video_dir, '*.mp4')):
                if os.path.abspath(f) != os.path.abspath(latest_video):
                    try:
                        os.remove(f)
                        print(f"🗑️ 추가 파일 삭제 완료: {f}")
                    except Exception as e:
                        print(f"⚠️ 추가 파일 삭제 실패: {f} ({e})")
            
            # 성공 로그
            print(f"\n✅ 업로드 성공 로그:")
            print(f"   - 영상 ID: {video_id}")
            print(f"   - 제목: {title}")
            print(f"   - 파일: {os.path.basename(latest_video)}")
            print(f"   - 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        else:
            print("❌ 업로드에 실패했습니다.")
            exit(1)
            
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")
        print(f"오류 타입: {type(e).__name__}")
        exit(1)
