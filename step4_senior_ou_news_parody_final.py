import subprocess
import sys
import os
from datetime import datetime
from common_utils import get_kst_now

def run_script(script_name):
    """지정된 파이썬 스크립트를 실행하고 성공 여부를 반환합니다."""
    print(f"--- [시작] {script_name} ---")
    
    if not os.path.exists(script_name):
        print(f"[오류] 스크립트 파일을 찾을 수 없습니다: {script_name}")
        return False

    try:
        # 자식 프로세스의 입출력 인코딩을 UTF-8로 강제
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'

        # 현재 파이썬 인터프리터를 사용하여 스크립트 실행
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore', # 인코딩 오류 발생 시 무시
            env=env # 수정된 환경 변수 적용
        )

        # 실시간으로 출력 스트리밍
        if process.stdout:
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    print(output.strip())

        # 프로세스 종료 후, 남은 stderr 출력
        if process.stderr:
            stderr_output = process.stderr.read()
            if stderr_output:
                print("--- [오류 출력] ---")
                print(stderr_output.strip())

        if process.returncode != 0:
            print(f"--- [실패] {script_name} (종료 코드: {process.returncode}) ---")
            return False
        
        print(f"--- [성공] {script_name} ---")
        return True

    except Exception as e:
        print(f"--- [치명적 오류] {script_name} 실행 중 예상치 못한 오류 발생 ---")
        print(str(e))
        return False

def main():
    """전체 패러디 뉴스 생성 파이프라인을 실행합니다."""
    start_time = get_kst_now()
    print(f"=== O_U Stock Parody 자동 생성 파이프라인 시작 ({start_time.strftime('%Y-%m-%d %H:%M:%S')}) ===")
    
    scripts_to_run = [
        "step1_senior_ou_news_parody_collection.py",
        "step2_senior_ou_news_parody_card.py",
        "step3_senior_ou_news_parody_video.py"
    ]
    
    for script in scripts_to_run:
        print("\n" + "="*50)
        success = run_script(script)
        if not success:
            print(f"\n[파이프라인 중단] '{script}' 실행에 실패하여 이후 단계를 중단합니다.")
            break
    
    end_time = get_kst_now()
    print("\n" + "="*50)
    print(f"=== O_U Stock Parody 자동 생성 파이프라인 종료 ({end_time.strftime('%Y-%m-%d %H:%M:%S')}) ===")
    print(f"총 소요 시간: {end_time - start_time}")

if __name__ == "__main__":
    main() 