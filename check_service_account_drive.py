#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
서비스 계정의 Google Drive 할당량 및 파일 목록 확인 스크립트
"""

import sys
from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# 스크립트 디렉토리 설정
SCRIPT_DIR = Path(__file__).resolve().parent

# 서비스 계정 인증 파일 경로
CREDS_FILE = SCRIPT_DIR / "config" / "service_account.json"

SCOPE = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]

def get_drive_service():
    """Google Drive API 서비스를 생성하고 반환합니다."""
    try:
        if not CREDS_FILE.exists():
            print(f"[오류] 인증 파일을 찾을 수 없습니다: {CREDS_FILE}")
            return None
        
        creds = Credentials.from_service_account_file(str(CREDS_FILE), scopes=SCOPE)
        drive_service = build('drive', 'v3', credentials=creds)
        return drive_service
    except Exception as e:
        print(f"[오류] Google Drive API 서비스 생성 실패: {e}")
        return None

def check_quota(drive_service):
    """서비스 계정의 Drive 할당량을 확인합니다."""
    try:
        about = drive_service.about().get(fields='storageQuota,user').execute()
        quota = about.get('storageQuota', {})
        user_info = about.get('user', {})
        
        service_account_email = user_info.get('emailAddress', '알 수 없음')
        print("=" * 60)
        print(f"서비스 계정 이메일: {service_account_email}")
        print("=" * 60)
        
        if 'limit' in quota and 'usage' in quota:
            limit = int(quota.get('limit', 0))
            usage = int(quota.get('usage', 0))
            usage_in_drive = int(quota.get('usageInDrive', 0))
            
            if limit > 0:
                usage_percent = (usage / limit) * 100
                limit_gb = limit / (1024 ** 3)
                usage_gb = usage / (1024 ** 3)
                usage_in_drive_gb = usage_in_drive / (1024 ** 3)
                
                print(f"\n[정보] 할당량 정보:")
                print(f"   전체 사용량: {usage_gb:.2f}GB / {limit_gb:.2f}GB ({usage_percent:.1f}%)")
                print(f"   Drive 사용량: {usage_in_drive_gb:.2f}GB")
                
                if usage_percent >= 100:
                    print(f"\n[오류] 할당량 100% 초과!")
                elif usage_percent >= 95:
                    print(f"\n[주의] 할당량이 거의 가득 찼습니다!")
                else:
                    print(f"\n[정상] 할당량 여유 있음")
            else:
                print("\n[주의] 할당량 정보를 가져올 수 없습니다.")
                print("   서비스 계정의 기본 할당량은 15GB입니다.")
        else:
            print("\n[주의] 할당량 정보를 가져올 수 없습니다.")
            print(f"   quota 데이터: {quota}")
            print("   서비스 계정의 기본 할당량은 15GB입니다.")
        
        return True
    except HttpError as e:
        if 'storageQuotaExceeded' in str(e):
            print("\n[오류] 서비스 계정의 Google Drive 할당량이 초과되었습니다!")
            return False
        else:
            print(f"\n[오류] 할당량 확인 중 오류: {e}")
            return False
    except Exception as e:
        print(f"\n[오류] 예상치 못한 오류: {e}")
        return False

def list_files(drive_service, max_files=20):
    """서비스 계정 Drive의 파일 목록을 확인하고 반환합니다."""
    try:
        print("\n" + "=" * 60)
        print(f"서비스 계정 Drive의 파일 목록 (상위 {max_files}개, 크기 순)")
        print("=" * 60)
        
        # 크기 순으로 정렬하여 가져오기
        results = drive_service.files().list(
            q="trashed=false",
            fields='files(id, name, size, mimeType, createdTime, modifiedTime)',
            orderBy='quotaBytesUsed desc',
            pageSize=max_files
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            print("   파일이 없습니다.")
            return []
        
        total_size = 0
        print(f"\n{'번호':<5} {'파일명':<50} {'크기':<15} {'타입':<20}")
        print("-" * 90)
        
        for i, file in enumerate(files, 1):
            file_name = file.get('name', '이름 없음')
            file_size = int(file.get('size', 0) or 0)
            file_type = file.get('mimeType', '알 수 없음')
            
            total_size += file_size
            
            # 크기 포맷팅
            if file_size >= 1024 ** 3:  # GB
                size_str = f"{file_size / (1024 ** 3):.2f}GB"
            elif file_size >= 1024 ** 2:  # MB
                size_str = f"{file_size / (1024 ** 2):.1f}MB"
            elif file_size >= 1024:  # KB
                size_str = f"{file_size / 1024:.1f}KB"
            else:
                size_str = f"{file_size}B"
            
            # 파일명이 너무 길면 자르기
            if len(file_name) > 47:
                file_name = file_name[:44] + "..."
            
            print(f"{i:<5} {file_name:<50} {size_str:<15} {file_type[:20]:<20}")
        
        total_size_gb = total_size / (1024 ** 3)
        print("-" * 90)
        print(f"총 {len(files)}개 파일, 총 크기: {total_size_gb:.2f}GB")
        return files
        
    except HttpError as e:
        print(f"\n[오류] 파일 목록 조회 중 오류: {e}")
        return []
    except Exception as e:
        print(f"\n[오류] 예상치 못한 오류: {e}")
        return []


def delete_files_interactive(drive_service):
    """목록을 보고 선택한 파일을 삭제합니다."""
    files = list_files(drive_service, max_files=50)
    if not files:
        return

    print("\n삭제할 파일 번호를 입력하세요.")
    print("예) 1,3,5  (엔터만 입력하면 취소)")
    raw = input("번호 입력: ").strip()
    if not raw:
        print("삭제를 취소했습니다.")
        return

    # 번호 파싱
    try:
        indices = sorted(
            {int(x.strip()) for x in raw.split(",") if x.strip()},
        )
    except ValueError:
        print("[오류] 번호 형식이 잘못되었습니다.")
        return

    targets = []
    for idx in indices:
        if 1 <= idx <= len(files):
            targets.append((idx, files[idx - 1]))

    if not targets:
        print("[오류] 유효한 번호가 없습니다.")
        return

    print("\n다음 파일들이 삭제 대상입니다:")
    for idx, f in targets:
        name = f.get("name", "이름 없음")
        size = int(f.get("size", 0) or 0)
        size_mb = size / (1024 ** 2)
        print(f"  - 번호 {idx}: {name} ({size_mb:.1f}MB)")

    confirm = input("\n정말 삭제하시겠습니까? (y/N): ").strip().lower()
    if confirm != "y":
        print("삭제를 취소했습니다.")
        return

    deleted = 0
    for _, f in targets:
        file_id = f.get("id")
        name = f.get("name", "이름 없음")
        try:
            drive_service.files().delete(fileId=file_id).execute()
            print(f"삭제 완료: {name}")
            deleted += 1
        except HttpError as e:
            print(f"[오류] 삭제 실패 ({name}): {e}")
        except Exception as e:
            print(f"[오류] 삭제 실패 ({name}): {e}")

    print(f"\n총 {deleted}개 파일을 삭제했습니다.")


def delete_largest_files(drive_service):
    """큰 파일부터 자동으로 일부 삭제합니다."""
    try:
        print("\n자동 삭제할 파일 개수를 입력하세요. (예: 3)")
        raw = input("개수 입력 (엔터=취소): ").strip()
        if not raw:
            print("자동 삭제를 취소했습니다.")
            return

        try:
            count = int(raw)
        except ValueError:
            print("[오류] 숫자를 입력하세요.")
            return

        if count <= 0:
            print("[오류] 1 이상의 숫자를 입력하세요.")
            return

        files = list_files(drive_service, max_files=count)
        if not files:
            return

        print("\n다음 파일들이 삭제 대상입니다:")
        for i, f in enumerate(files, 1):
            name = f.get("name", "이름 없음")
            size = int(f.get("size", 0) or 0)
            size_mb = size / (1024 ** 2)
            print(f"  - 번호 {i}: {name} ({size_mb:.1f}MB)")

        confirm = input("\n정말 위 파일들을 모두 삭제하시겠습니까? (y/N): ").strip().lower()
        if confirm != "y":
            print("자동 삭제를 취소했습니다.")
            return

        deleted = 0
        for f in files:
            file_id = f.get("id")
            name = f.get("name", "이름 없음")
            try:
                drive_service.files().delete(fileId=file_id).execute()
                print(f"삭제 완료: {name}")
                deleted += 1
            except HttpError as e:
                print(f"[오류] 삭제 실패 ({name}): {e}")
            except Exception as e:
                print(f"[오류] 삭제 실패 ({name}): {e}")

        print(f"\n총 {deleted}개 파일을 삭제했습니다.")
    except Exception as e:
        print(f"[오류] 자동 삭제 중 예외 발생: {e}")

def main():
    """메인 함수"""
    print("서비스 계정의 Google Drive 할당량 확인 중...\n")
    
    drive_service = get_drive_service()
    if not drive_service:
        print("Drive 서비스를 생성할 수 없습니다.")
        return
    
    # 할당량 확인
    quota_ok = check_quota(drive_service)
    
    # 파일 목록 확인
    list_files(drive_service, max_files=30)

    # 정리 메뉴
    print("\n" + "=" * 60)
    print("정리 작업을 선택하세요.")
    print("  1) 번호를 선택해서 개별 파일 삭제")
    print("  2) 큰 파일부터 N개 자동 삭제")
    print("  기타 입력 또는 엔터: 건너뛰기")
    choice = input("선택: ").strip()

    if choice == "1":
        delete_files_interactive(drive_service)
    elif choice == "2":
        delete_largest_files(drive_service)
    else:
        print("삭제 작업을 건너뜁니다.")

    print("\n" + "=" * 60)
    print("확인 및 정리 작업 완료!")
    print("=" * 60)

    if not quota_ok:
        print("\n[안내] 할당량 초과 상태입니다.")
        print("   1. 위 목록에서 불필요한 파일을 더 삭제하세요.")
        print("   2. 서비스 계정 Drive의 휴지통도 비우세요.")
        print("   3. 또는 서비스 계정이 사용자 Drive에 직접 접근하도록 설정하세요.")

if __name__ == "__main__":
    main()

