import os
import glob
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 유튜브 업로드를 위한 권한 범위
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    """
    인증된 YouTube API 서비스 객체를 생성하여 반환합니다.
    'youtube_uploader/token.json' 파일이 필요합니다.
    """
    creds = Credentials.from_authorized_user_file('youtube_uploader/token.json', SCOPES)
    return build('youtube', 'v3', credentials=creds)

def upload_video(file_path, title, description, tags):
    """
    지정된 동영상 파일을 YouTube에 업로드합니다.
    """
    youtube = get_authenticated_service()
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': '24'  # 'Entertainment' 카테고리, 또는 '26' (Howto & Style), '27' (Education)도 적합
        },
        'status': {
            'privacyStatus': 'private'  # 'private', 'public', 'unlisted' 중 선택
        }
    }
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True, mimetype='video/mp4')
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    
    response = None
    print("동영상 업로드를 시작합니다...")
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"업로드 진행률: {int(status.progress() * 100)}%")
    
    print(f"업로드 성공! 영상 ID: {response['id']}")
    print(f"YouTube Studio에서 확인: https://studio.youtube.com/video/{response['id']}/edit")
    return response['id']

if __name__ == '__main__':
    # 오늘 날짜를 "YYYY년 MM월 DD일" 형식으로 구하기
    today = datetime.now().strftime('%Y년 %m월 %d일')

    # 유튜브 영상 제목, 설명, 태그 자동 생성
    title = f"{today} 시니어 뉴스패러디 | AI가 전하는 오늘의 유머 | 이 포스팅은 쿠팡파트너스 활동으로 일정보수를 지급받습니다."
    
    description = f"""매일 오전 AI가 전하는 유익하고 재미있는 시니어 뉴스! 이 포스팅은 쿠팡파트너스 활동으로 일정보수를 지급받습니다.

딱딱한 뉴스는 이제 그만! OU의 AI가 오늘의 핫한 시니어 관련 뉴스를 위트 넘치는 밈과 패러디로 재해석해드립니다. 복잡한 세상 소식을 쉽고 재미있게 이해하고, 활기찬 하루를 위한 정보까지 얻어가세요!

▶ 이런 분들께 추천:
- 매일 새로운 정보를 얻고 싶은 액티브 시니어
- 재미있게 세상 돌아가는 소식을 알고 싶은 분
- 자녀, 손주와 함께 공감하며 볼만한 콘텐츠를 찾는 분
- 건강, 취미, 생활 꿀팁 등 유용한 정보가 필요한 분
- AI가 분석한 시니어 트렌드가 궁금한 분

▶ 매일 업데이트되는 콘텐츠:
- 건강, 정책, 사회 등 당일 주요 시니어 뉴스 패러디
- AI 기반 생활 정보 분석
- 시니어들이 놓치기 쉬운 유용한 꿀팁
- 밈으로 보는 요즘 이야기

구독과 좋아요로 매일 아침 즐거운 정보를 받아보세요!

※ 본 콘텐츠는 정보 제공 목적이며, 특정 상품이나 서비스를 권유하지 않습니다.

#시니어뉴스 #AI뉴스 #노후준비 #은퇴 #5060 #실버세대 #건강정보 #생활꿀팁 #OU시니어뉴스 #뉴스패러디 #AI아나운서 #매일뉴스 #유머
"""
    
    tags = ["OU시니어뉴스", "시니어", "뉴스", "패러디", "AI", "건강정보", "꿀팁", "노후준비", "실버세대", "유머", "자동생성"]

    # 업로드할 영상 파일 경로 설정
    video_dir = 'parody_video'
    # 'parody_video' 폴더 내의 mp4 파일 목록 가져오기
    video_files = glob.glob(os.path.join(video_dir, '*.mp4'))
    
    if not video_files:
        raise FileNotFoundError(f"'{video_dir}' 폴더에 업로드할 동영상 파일이 없습니다.")

    # 가장 최근에 수정된 파일을 업로드 대상으로 선택
    latest_video = max(video_files, key=os.path.getmtime)
    video_path = latest_video

    print(f"업로드할 동영상: {video_path}")

    # 동영상 업로드 함수 호출
    upload_video(
        video_path,
        title,
        description,
        tags
    )
