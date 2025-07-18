#!/usr/bin/env python3
"""
일일 YouTube 토큰 상태 확인 및 자동 새로고침
매일 실행하여 토큰 상태를 관리합니다.
"""

import os
import sys
from pathlib import Path

# check_token 모듈의 함수를 직접 정의
def check_token_status():
    """토큰 상태를 확인하고 필요시 새로고침합니다."""
    import os
    import json
    from datetime import datetime, timedelta
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    
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

def main():
    """일일 토큰 체크 및 관리"""
    print("🔍 일일 YouTube 토큰 상태 확인")
    print("=" * 50)
    
    # 토큰 상태 확인
    token_ok = check_token_status()
    
    if not token_ok:
        print("\n🔄 토큰 새로고침 시도...")
        try:
            # refresh_token.py 실행
            import subprocess
            result = subprocess.run([sys.executable, 'youtube_uploader/refresh_token.py'], 
                                  capture_output=True, text=True, cwd=Path(__file__).parent)
            
            if result.returncode == 0:
                print("✅ 토큰 새로고침 성공!")
                print("📝 GitHub Secrets 업데이트가 필요할 수 있습니다.")
            else:
                print("❌ 토큰 새로고침 실패!")
                print("수동으로 확인해주세요.")
                
        except Exception as e:
            print(f"❌ 토큰 새로고침 중 오류: {e}")
    else:
        print("\n✅ 토큰 상태 정상 - 추가 작업 불필요")
    
    print("\n" + "=" * 50)
    print("📅 다음 체크: 내일 같은 시간")

if __name__ == '__main__':
    main() 