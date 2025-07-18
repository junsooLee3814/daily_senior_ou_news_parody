#!/usr/bin/env python3
"""
YouTube API 토큰 새로 발급 스크립트
GitHub Actions에서 사용할 새로운 토큰을 생성합니다.
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# YouTube API 권한 범위
SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]

def refresh_youtube_token():
    """YouTube API 토큰을 새로 발급받습니다."""
    
    creds = None
    
    # 기존 토큰 파일이 있으면 로드
    if os.path.exists('youtube_uploader/token.json'):
        try:
            creds = Credentials.from_authorized_user_file('youtube_uploader/token.json', SCOPES)
            print("기존 토큰 파일을 찾았습니다.")
        except Exception as e:
            print(f"기존 토큰 파일 로드 실패: {e}")
    
    # 토큰이 없거나 만료되었으면 새로 발급
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("토큰을 새로고침했습니다.")
            except Exception as e:
                print(f"토큰 새로고침 실패: {e}")
                creds = None
        
        # 새로 인증 진행
        if not creds:
            if not os.path.exists('youtube_uploader/client_secrets.json'):
                print("❌ client_secrets.json 파일이 없습니다.")
                print("Google Cloud Console에서 OAuth 2.0 클라이언트 ID를 다운로드하여 youtube_uploader/client_secrets.json에 저장하세요.")
                return None
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'youtube_uploader/client_secrets.json', SCOPES)
                creds = flow.run_local_server(port=0)
                print("새로운 토큰을 발급받았습니다.")
            except Exception as e:
                print(f"토큰 발급 실패: {e}")
                return None
    
    # 토큰 저장
    if creds:
        try:
            with open('youtube_uploader/token.json', 'w') as token:
                token.write(creds.to_json())
            print("✅ 토큰이 youtube_uploader/token.json에 저장되었습니다.")
            
            # GitHub Secrets용 JSON 출력
            print("\n🔑 GitHub Secrets용 토큰 (전체 내용을 복사하여 YOUTUBE_TOKEN_JSON에 설정):")
            print("=" * 80)
            print(creds.to_json())
            print("=" * 80)
            
            return True
        except Exception as e:
            print(f"토큰 저장 실패: {e}")
            return False
    
    return False

if __name__ == '__main__':
    print("🔄 YouTube API 토큰 새로 발급을 시작합니다...")
    success = refresh_youtube_token()
    
    if success:
        print("\n🎉 토큰 발급 완료!")
        print("📝 다음 단계:")
        print("1. 위의 JSON 내용을 복사")
        print("2. GitHub 저장소 → Settings → Secrets and variables → Actions")
        print("3. YOUTUBE_TOKEN_JSON 시크릿을 업데이트")
        print("4. GitHub Actions를 다시 실행")
    else:
        print("\n❌ 토큰 발급 실패!")
        print("client_secrets.json 파일을 확인하고 다시 시도하세요.") 