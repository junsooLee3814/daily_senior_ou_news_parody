#!/usr/bin/env python3
"""
멀티 OU 프로젝트 관리 스크립트
여러 OU 프로젝트를 효율적으로 관리하고 LFS 한도를 절약합니다.
"""

import os
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

class MultiOUManager:
    def __init__(self):
        self.projects = {
            'senior_ou': {
                'path': '.',  # 현재 디렉토리
                'description': '시니어 OU 뉴스 패러디',
                'priority': 'high'
            },
            # 다른 OU 프로젝트들 추가
            # 'other_ou': {
            #     'path': '../07_other_ou_news_parody',
            #     'description': '다른 OU 뉴스 패러디',
            #     'priority': 'medium'
            # }
        }
    
    def get_lfs_usage(self, project_path):
        """프로젝트별 LFS 사용량 확인"""
        try:
            result = subprocess.run(['git', 'lfs', 'status'], 
                                  cwd=project_path, capture_output=True, text=True)
            return result.stdout
        except Exception as e:
            return f"LFS 상태 확인 실패: {e}"
    
    def cleanup_project(self, project_name):
        """프로젝트 정리"""
        project_info = self.projects.get(project_name)
        if not project_info:
            print(f"❌ 프로젝트 '{project_name}'을 찾을 수 없습니다.")
            return False
        
        project_path = Path(project_info['path'])
        if not project_path.exists():
            print(f"❌ 프로젝트 경로가 존재하지 않습니다: {project_path}")
            return False
        
        print(f"🧹 {project_name} 프로젝트 정리 중...")
        
        # 오래된 파일들 정리
        self._cleanup_old_files(project_path)
        
        # LFS 최적화
        self._optimize_lfs(project_path)
        
        return True
    
    def _cleanup_old_files(self, project_path):
        """오래된 파일 정리"""
        # 비디오 파일 (최근 2개만 유지)
        video_dir = project_path / 'parody_video'
        if video_dir.exists():
            video_files = list(video_dir.glob('*.mp4'))
            video_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for video_file in video_files[2:]:
                try:
                    subprocess.run(['git', 'lfs', 'untrack', str(video_file)], 
                                 cwd=project_path, capture_output=True)
                    video_file.unlink()
                    print(f"🗑️ 비디오 삭제: {video_file.name}")
                except Exception as e:
                    print(f"⚠️ 비디오 삭제 실패: {e}")
        
        # 카드 이미지 (최근 5개만 유지)
        card_dir = project_path / 'parody_card'
        if card_dir.exists():
            card_files = list(card_dir.glob('*.png'))
            card_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for card_file in card_files[5:]:
                try:
                    subprocess.run(['git', 'lfs', 'untrack', str(card_file)], 
                                 cwd=project_path, capture_output=True)
                    card_file.unlink()
                    print(f"🗑️ 카드 삭제: {card_file.name}")
                except Exception as e:
                    print(f"⚠️ 카드 삭제 실패: {e}")
    
    def _optimize_lfs(self, project_path):
        """LFS 최적화"""
        # .lfsignore 파일 생성
        lfs_ignore_content = """# LFS에서 제외할 파일들
*.txt
*.py
*.yml
*.yaml
*.json
*.md
*.gitignore
*.gitattributes
*.log
*.tmp
"""
        
        lfs_ignore_path = project_path / '.lfsignore'
        with open(lfs_ignore_path, 'w', encoding='utf-8') as f:
            f.write(lfs_ignore_content)
        
        print(f"📝 .lfsignore 생성: {lfs_ignore_path}")
    
    def run_project(self, project_name, step=None):
        """프로젝트 실행"""
        project_info = self.projects.get(project_name)
        if not project_info:
            print(f"❌ 프로젝트 '{project_name}'을 찾을 수 없습니다.")
            return False
        
        project_path = Path(project_info['path'])
        if not project_path.exists():
            print(f"❌ 프로젝트 경로가 존재하지 않습니다: {project_path}")
            return False
        
        print(f"🚀 {project_name} 프로젝트 실행 중...")
        
        if step:
            # 특정 단계 실행
            script_path = project_path / f"step{step}_*.py"
            scripts = list(project_path.glob(f"step{step}_*.py"))
            if scripts:
                script = scripts[0]
                print(f"📜 스크립트 실행: {script.name}")
                try:
                    result = subprocess.run([sys.executable, str(script)], 
                                          cwd=project_path, capture_output=True, text=True)
                    print(result.stdout)
                    if result.stderr:
                        print(f"⚠️ 오류: {result.stderr}")
                    return result.returncode == 0
                except Exception as e:
                    print(f"❌ 스크립트 실행 실패: {e}")
                    return False
            else:
                print(f"❌ step{step} 스크립트를 찾을 수 없습니다.")
                return False
        else:
            # 전체 파이프라인 실행
            steps = [1, 2, 3, 4, 5]
            for step_num in steps:
                script_pattern = f"step{step_num}_*.py"
                scripts = list(project_path.glob(script_pattern))
                if scripts:
                    script = scripts[0]
                    print(f"📜 Step {step_num} 실행: {script.name}")
                    try:
                        result = subprocess.run([sys.executable, str(script)], 
                                              cwd=project_path, capture_output=True, text=True)
                        print(result.stdout)
                        if result.stderr:
                            print(f"⚠️ 오류: {result.stderr}")
                        if result.returncode != 0:
                            print(f"❌ Step {step_num} 실패")
                            return False
                    except Exception as e:
                        print(f"❌ Step {step_num} 실행 실패: {e}")
                        return False
        
        return True
    
    def show_status(self):
        """모든 프로젝트 상태 표시"""
        print("📊 멀티 OU 프로젝트 상태")
        print("=" * 50)
        
        for project_name, project_info in self.projects.items():
            project_path = Path(project_info['path'])
            print(f"\n🏷️ {project_name} ({project_info['description']})")
            print(f"📍 경로: {project_path}")
            print(f"⭐ 우선순위: {project_info['priority']}")
            
            if project_path.exists():
                # LFS 사용량 확인
                lfs_status = self.get_lfs_usage(project_path)
                print(f"📊 LFS 상태: {lfs_status.split()[0] if lfs_status else '확인 불가'}")
                
                # 최근 파일 확인
                video_dir = project_path / 'parody_video'
                if video_dir.exists():
                    video_files = list(video_dir.glob('*.mp4'))
                    print(f"📹 비디오 파일: {len(video_files)}개")
                
                card_dir = project_path / 'parody_card'
                if card_dir.exists():
                    card_files = list(card_dir.glob('*.png'))
                    print(f"🃏 카드 파일: {len(card_files)}개")
            else:
                print("❌ 프로젝트 경로가 존재하지 않습니다.")

def main():
    """메인 실행 함수"""
    manager = MultiOUManager()
    
    import sys
    
    if len(sys.argv) < 2:
        print("🔧 멀티 OU 프로젝트 관리 도구")
        print("=" * 50)
        print("사용법:")
        print("  python multi_ou_manager.py status                    # 상태 확인")
        print("  python multi_ou_manager.py cleanup <project_name>    # 프로젝트 정리")
        print("  python multi_ou_manager.py run <project_name>        # 전체 실행")
        print("  python multi_ou_manager.py run <project_name> <step> # 특정 단계 실행")
        print("\n사용 가능한 프로젝트:")
        for name, info in manager.projects.items():
            print(f"  - {name}: {info['description']}")
        return
    
    command = sys.argv[1]
    
    if command == 'status':
        manager.show_status()
    
    elif command == 'cleanup':
        if len(sys.argv) < 3:
            print("❌ 프로젝트 이름을 지정해주세요.")
            return
        project_name = sys.argv[2]
        manager.cleanup_project(project_name)
    
    elif command == 'run':
        if len(sys.argv) < 3:
            print("❌ 프로젝트 이름을 지정해주세요.")
            return
        project_name = sys.argv[2]
        step = sys.argv[3] if len(sys.argv) > 3 else None
        success = manager.run_project(project_name, step)
        if success:
            print(f"✅ {project_name} 프로젝트 실행 완료!")
        else:
            print(f"❌ {project_name} 프로젝트 실행 실패!")
    
    else:
        print(f"❌ 알 수 없는 명령어: {command}")

if __name__ == '__main__':
    main() 