import subprocess
import sys
import os
from datetime import datetime

def print_progress_bar(step_num, total_steps):
    bar_length = 30
    filled_length = int(round(bar_length * step_num / float(total_steps)))
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f"\n진행률: |{bar}| {step_num}/{total_steps} 단계 완료\n")

def run_script(script_name, step_num=None, total_steps=None):
    if step_num and total_steps:
        print_progress_bar(step_num, total_steps)
    print(f"\n🚀 [시작] {script_name} 실행 중...")
    print(f"⏰ 시작 시간: {datetime.now().strftime('%H:%M:%S')}\n")
    if not os.path.exists(script_name):
        print(f"❌ [오류] 스크립트 파일을 찾을 수 없습니다: {script_name}")
        return False
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUNBUFFERED'] = '1'
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            env=env
        )
        print(f"✅ 프로세스 시작됨 (PID: {process.pid})")
        
        stdout, stderr = process.communicate(timeout=300)
        
        if stdout:
            lines = stdout.strip().split('\n')
            for i, line in enumerate(lines[:50], 1):
                if line.strip():
                    print(f"[{i:3d}] {line}")
            if len(lines) > 50:
                print(f"... (총 {len(lines)}줄 중 50줄 표시)")
        
        if stderr and stderr.strip():
            print(f"\n⚠️ [오류 출력] {script_name}")
            print("-" * 50)
            print(stderr.strip())
            print("-" * 50)
        
        if process.returncode != 0:
            print(f"\n❌ [실패] {script_name}")
            print(f"   종료 코드: {process.returncode}")
            return False
        print(f"\n✅ [성공] {script_name}")
        return True
        
    except subprocess.TimeoutExpired:
        print(f"\n⏰ [타임아웃] {script_name} (5분 초과)")
        process.kill()
        return False
    except Exception as e:
        print(f"\n💥 [치명적 오류] {script_name} 실행 중 예상치 못한 오류 발생")
        print(f"   오류 내용: {str(e)}")
        return False

def main():
    start_time = datetime.now()
    print(f"=== Senior OU News Parody 자동 생성 파이프라인 시작 ({start_time.strftime('%Y-%m-%d %H:%M:%S')}) ===")

    scripts_to_run = [
        "step1_senior_ou_news_parody_collection.py",
        "step2_senior_ou_news_parody_card.py",
        "step3_senior_ou_news_parody_video.py"
    ]
    total_steps = len(scripts_to_run)

    for idx, script in enumerate(scripts_to_run, 1):
        print("\n" + "="*50)
        success = run_script(script, step_num=idx, total_steps=total_steps)
        if not success:
            print(f"\n[파이프라인 중단] '{script}' 실행에 실패하여 이후 단계를 중단합니다.")
            break

    end_time = datetime.now()
    print("\n" + "="*50)
    print(f"=== Senior OU News Parody 자동 생성 파이프라인 종료 ({end_time.strftime('%Y-%m-%d %H:%M:%S')}) ===")
    print(f"총 소요 시간: {end_time - start_time}")

if __name__ == "__main__":
    main() 