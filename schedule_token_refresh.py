#!/usr/bin/env python3
"""
YouTube 토큰 자동 새로고침 스케줄러
토큰이 만료되기 7일 전에 자동으로 새로고침합니다.
"""

import os
import sys
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def should_refresh_token():
    """토큰 새로고침이 필요한지 확인"""
    if not os.path.exists('youtube_uploader/token.json'):
        return True
    
    try:
        creds = Credentials.from_authorized_user_file('youtube_uploader/token.json', 
                                                     ['https://www.googleapis.com/auth/youtube.upload'])
        
        if not creds.expiry:
            return True
        
        # 만료까지 남은 일수 계산
        days_until_expiry = (creds.expiry - datetime.now()).days
        
        # 7일 이내로 만료되면 새로고침
        return days_until_expiry <= 7
        
    except Exception:
        return True

def auto_refresh_token():
    """토큰 자동 새로고침"""
    if should_refresh_token():
        print("🔄 토큰 자동 새로고침 시작...")
        
        # refresh_token.py 실행
        import subprocess
        result = subprocess.run([sys.executable, 'youtube_uploader/refresh_token.py'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 토큰 자동 새로고침 완료!")
            print("📝 GitHub Secrets 업데이트가 필요합니다.")
            return True
        else:
            print("❌ 토큰 자동 새로고침 실패!")
            return False
    else:
        print("✅ 토큰이 유효합니다. 새로고침 불필요.")
        return True

if __name__ == '__main__':
    print(f"🔍 토큰 상태 확인 중... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    success = auto_refresh_token()
    
    if success:
        print("🎉 토큰 관리 완료!")
    else:
        print("❌ 토큰 관리 실패!")
        print("수동으로 python youtube_uploader/refresh_token.py를 실행하세요.") 