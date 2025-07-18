#!/usr/bin/env python3
"""
Git LFS 최적화 스크립트
LFS 사용량을 줄이고 불필요한 파일들을 정리합니다.
"""

import os
import glob
import shutil
from pathlib import Path
import subprocess

def get_lfs_usage():
    """현재 LFS 사용량 확인"""
    try:
        result = subprocess.run(['git', 'lfs', 'status'], 
                              capture_output=True, text=True)
        print("📊 현재 LFS 상태:")
        print(result.stdout)
        return result.stdout
    except Exception as e:
        print(f"LFS 상태 확인 실패: {e}")
        return None

def cleanup_old_videos():
    """오래된 비디오 파일 정리"""
    video_dir = Path('parody_video')
    if not video_dir.exists():
        print("❌ parody_video 디렉토리가 없습니다.")
        return
    
    # 최근 3개 파일만 유지
    video_files = list(video_dir.glob('*.mp4'))
    video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print(f"📹 발견된 비디오 파일: {len(video_files)}개")
    
    # 최근 3개 제외하고 삭제
    for video_file in video_files[3:]:
        try:
            # LFS에서 제거
            subprocess.run(['git', 'lfs', 'untrack', str(video_file)], 
                         capture_output=True)
            # 파일 삭제
            video_file.unlink()
            print(f"🗑️ 삭제됨: {video_file.name}")
        except Exception as e:
            print(f"⚠️ 삭제 실패 {video_file.name}: {e}")

def cleanup_old_cards():
    """오래된 카드 이미지 정리"""
    card_dir = Path('parody_card')
    if not card_dir.exists():
        print("❌ parody_card 디렉토리가 없습니다.")
        return
    
    # 최근 10개 파일만 유지
    card_files = list(card_dir.glob('*.png'))
    card_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print(f"🃏 발견된 카드 파일: {len(card_files)}개")
    
    # 최근 10개 제외하고 삭제
    for card_file in card_files[10:]:
        try:
            # LFS에서 제거
            subprocess.run(['git', 'lfs', 'untrack', str(card_file)], 
                         capture_output=True)
            # 파일 삭제
            card_file.unlink()
            print(f"🗑️ 삭제됨: {card_file.name}")
        except Exception as e:
            print(f"⚠️ 삭제 실패 {card_file.name}: {e}")

def optimize_assets():
    """asset 폴더 최적화"""
    asset_dir = Path('asset')
    if not asset_dir.exists():
        print("❌ asset 디렉토리가 없습니다.")
        return
    
    # 불필요한 파일들 정리
    unnecessary_files = [
        'rawdata.txt',  # 설정 파일은 LFS 불필요
    ]
    
    for file_name in unnecessary_files:
        file_path = asset_dir / file_name
        if file_path.exists():
            try:
                # LFS에서 제거
                subprocess.run(['git', 'lfs', 'untrack', str(file_path)], 
                             capture_output=True)
                print(f"📄 LFS에서 제거됨: {file_name}")
            except Exception as e:
                print(f"⚠️ LFS 제거 실패 {file_name}: {e}")

def create_lfs_ignore():
    """LFS 무시 파일 생성"""
    lfs_ignore_content = """# LFS에서 제외할 파일들
*.txt
*.py
*.yml
*.yaml
*.json
*.md
*.gitignore
*.gitattributes

# 임시 파일들
*.tmp
*.temp
*.log

# 설정 파일들
.env
config.json
rawdata.txt

# 스크립트 파일들
*.sh
*.bat
*.ps1
"""
    
    with open('.lfsignore', 'w', encoding='utf-8') as f:
        f.write(lfs_ignore_content)
    
    print("📝 .lfsignore 파일 생성 완료")

def main():
    """메인 실행 함수"""
    print("🔧 Git LFS 최적화 시작...")
    print("=" * 50)
    
    # 현재 LFS 상태 확인
    get_lfs_usage()
    
    print("\n🧹 오래된 파일 정리 중...")
    
    # 오래된 비디오 정리
    cleanup_old_videos()
    
    # 오래된 카드 이미지 정리
    cleanup_old_cards()
    
    # asset 최적화
    optimize_assets()
    
    # LFS 무시 파일 생성
    create_lfs_ignore()
    
    print("\n✅ LFS 최적화 완료!")
    print("\n📝 다음 단계:")
    print("1. git add .")
    print("2. git commit -m 'LFS 최적화'")
    print("3. git push")
    print("4. 다른 OU 프로젝트도 동일하게 최적화")

if __name__ == '__main__':
    main() 