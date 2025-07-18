#!/usr/bin/env python3
"""
YouTube 토큰 상태 확인 스크립트
토큰이 만료되었는지 확인하고 필요시 새로고침합니다.
"""

import os
import json
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def check_token_status():
    """토큰 상태를 확인하고 필요시 새로고침합니다."""
    
    if not os.path.exists('youtube_uploader/token.json'):
        print("❌ 토큰 파일이 없습니다.")
        return False
    
    try:
        # 토큰 로드
        creds = Credentials.from_authorized_user_file('youtube_uploader/token.json', 
                                                     ['https://www.googleapis.com/auth/youtube.upload'])
        
        print(f"📅 토큰 만료일: {creds.expiry}")
        print(f"⏰ 현재 시간: {datetime.now()}")
        
        # 만료까지 남은 시간 계산
        if creds.expiry:
            time_left = creds.expiry - datetime.now()
            days_left = time_left.days
            hours_left = time_left.seconds // 3600
            
            print(f"⏳ 만료까지 남은 시간: {days_left}일 {hours_left}시간")
            
            # 7일 이내로 만료되면 경고
            if days_left <= 7:
                print("⚠️ 토큰이 곧 만료됩니다!")
                if days_left <= 3:
                    print("🚨 긴급: 3일 이내 만료!")
                
                # 자동 새로고침 시도
                if creds.expired and creds.refresh_token:
                    print("🔄 토큰 자동 새로고침 시도...")
                    try:
                        creds.refresh(Request())
                        with open('youtube_uploader/token.json', 'w') as f:
                            f.write(creds.to_json())
                        print("✅ 토큰 새로고침 완료!")
                        return True
                    except Exception as e:
                        print(f"❌ 자동 새로고침 실패: {e}")
                        print("수동으로 refresh_token.py를 실행하세요.")
                        return False
                elif not creds.refresh_token:
                    print("❌ 리프레시 토큰이 없습니다. 새로 인증이 필요합니다.")
                    return False
            else:
                print("✅ 토큰이 유효합니다.")
                return True
        else:
            print("❌ 토큰 만료일 정보가 없습니다.")
            return False
            
    except Exception as e:
        print(f"❌ 토큰 확인 중 오류: {e}")
        return False

if __name__ == '__main__':
    print("🔍 YouTube 토큰 상태 확인 중...")
    success = check_token_status()
    
    if success:
        print("\n✅ 토큰 상태 정상")
    else:
        print("\n❌ 토큰 문제 발견")
        print("💡 해결방법: python youtube_uploader/refresh_token.py 실행") 