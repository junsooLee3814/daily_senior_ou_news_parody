"""
step3_ou_stock_parody_video.py

parody_card 폴더에 생성된 카드뉴스 이미지들을 동영상으로 제작합니다.
- 인트로 이미지(intro_ou_stock.png)를 영상 처음에 추가합니다.
- 각 카드 이미지에 줌인 효과를 적용합니다.
- 배경음악(bgm.mp3)을 페이드인/아웃 효과와 함께 추가합니다.

실행 전 FFmpeg가 설치되어 있어야 합니다.
"""

import os
import glob
import subprocess
from datetime import datetime
import shutil
import re
import time
import sys
from utils.common_utils import get_kst_now

def parse_rawdata(file_path='asset/rawdata.txt'):
    """rawdata.txt 파일을 파싱하여 설정값을 딕셔너리로 반환합니다."""
    config = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('['):
                    continue
                if ':' in line:
                    key, value = line.split(':', 1)
                    config[key.strip()] = value.strip()
    except FileNotFoundError:
        print(f"설정 파일({file_path})을 찾을 수 없습니다. 기본값으로 진행합니다.")
    return config

print("--- 패러디 카드 동영상 제작 시작 ---", flush=True)

# 설정 파일 로드
raw_config = parse_rawdata()
card_duration_str = raw_config.get('동영상_길이', '4초') # '동영상_길이' 키를 사용하도록 수정
try:
    match = re.search(r'\d+', card_duration_str)
    if match:
        card_duration_val = int(match.group())
    else:
        card_duration_val = 4
except (AttributeError, ValueError):
    card_duration_val = 4

# --- 설정 ---
CARD_DURATION = card_duration_val  # 각 카드 이미지의 노출 시간 (초)
INTRO_DURATION = 4 # 인트로 이미지의 노출 시간 (초)
WIDTH, HEIGHT = 1920, 1080 # 동영상 해상도 (가로 영상에 맞게 수정)

# --- 경로 설정 ---
now_str = get_kst_now().strftime('%Y%m%d_%H%M%S')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CARD_IMG_DIR = os.path.join(BASE_DIR, 'parody_card')
VIDEO_OUT_DIR = os.path.join(BASE_DIR, 'parody_video')
SINGLE_CLIP_DIR = os.path.join(VIDEO_OUT_DIR, 'single_clips')

INTRO_IMG_PATH = os.path.join(BASE_DIR, 'asset', 'intro_senior_ou_news-parody.png')
BGM_PATH = os.path.join(BASE_DIR, 'asset', 'bgm.mp3')

INTRO_CLIP_PATH = os.path.join(SINGLE_CLIP_DIR, f'intro_clip_{now_str}.mp4')
FINAL_INTRO_CLIP_PATH = os.path.join(SINGLE_CLIP_DIR, f'final_intro_clip_{now_str}.mp4')
MERGED_CLIP_PATH = os.path.join(VIDEO_OUT_DIR, f'merged_senior_ou_news_parody_{now_str}.mp4')
FINAL_VIDEO_PATH = os.path.join(VIDEO_OUT_DIR, f'senior_ou_news_parody_{now_str}.mp4')

# --- 폴더 생성 ---
os.makedirs(VIDEO_OUT_DIR, exist_ok=True)
os.makedirs(SINGLE_CLIP_DIR, exist_ok=True)

def find_ffmpeg():
    """FFmpeg 실행 파일을 찾습니다."""
    possible_paths = [
        "ffmpeg",  # PATH에 있는 경우
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
        os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe"),
    ]
    
    for path in possible_paths:
        try:
            if path == "ffmpeg":
                # PATH에서 찾기
                result = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return path
            else:
                # 전체 경로로 찾기
                if os.path.exists(path):
                    return path
        except:
            continue
    
    return None

def create_intro_video(img_path, out_path, duration):
    """인트로 이미지를 사용하여 줌 효과가 적용된 비디오 클립을 생성합니다."""
    if not os.path.exists(img_path):
        print(f"[오류] 인트로 이미지 파일 없음: {img_path}", flush=True)
        return None

    print("1. 인트로 영상 제작 중...", flush=True)
    
    # FFmpeg 경로 찾기
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("[오류] FFmpeg를 찾을 수 없습니다. FFmpeg가 설치되어 있는지 확인하세요.", flush=True)
        return None
    
    cmd = [
        ffmpeg_path, "-y", "-loop", "1", "-i", img_path,
        "-t", str(duration),
        "-vf", f"zoompan=z='min(zoom+0.001,1.05)':d={duration*25}:s={WIDTH}x{HEIGHT}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"   - 인트로 영상 저장 완료: {out_path}", flush=True)
        return out_path
    except subprocess.CalledProcessError as e:
        print(f"[오류] 인트로 영상 제작 실패: {e.stderr}", flush=True)
        return None

def create_card_videos(card_img_paths, duration):
    """카드 이미지들을 개별 비디오 클립으로 변환합니다."""
    video_clips = []
    total_cards = len(card_img_paths)
    print(f"2. 총 {total_cards}개의 카드 이미지로 영상 제작 중...", flush=True)

    # FFmpeg 경로 찾기
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("[오류] FFmpeg를 찾을 수 없습니다. FFmpeg가 설치되어 있는지 확인하세요.", flush=True)
        return []

    for idx, img_path in enumerate(card_img_paths):
        out_path = os.path.join(SINGLE_CLIP_DIR, f'card_{idx+1:02d}_{now_str}.mp4')
        cmd = [
            ffmpeg_path, "-y", "-loop", "1", "-i", img_path,
            "-t", str(duration),
            "-vf", f"zoompan=z='min(zoom+0.001,1.05)':d={duration*25}:s={WIDTH}x{HEIGHT}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", out_path
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            print(f"   - 카드 영상 ({idx+1}/{total_cards}) 저장 완료: {out_path}", flush=True)
            video_clips.append(out_path)
        except subprocess.CalledProcessError as e:
            print(f"[오류] 카드 영상({idx+1}) 제작 실패: {e.stderr}", flush=True)
            continue
    return video_clips

def merge_videos(video_paths, out_path):
    """생성된 모든 비디오 클립을 하나로 합칩니다."""
    print("3. 모든 영상 클립 합치는 중...", flush=True)
    
    # FFmpeg 경로 찾기
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("[오류] FFmpeg를 찾을 수 없습니다. FFmpeg가 설치되어 있는지 확인하세요.", flush=True)
        return
    
    list_file_path = os.path.join(BASE_DIR, "video_list.txt")
    with open(list_file_path, "w", encoding="utf-8") as f:
        for v_path in video_paths:
            f.write(f"file '{os.path.abspath(v_path)}'\n")

    cmd = [
        ffmpeg_path, "-y", "-f", "concat", "-safe", "0",
        "-i", list_file_path, "-c", "copy", out_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"   - 영상 합치기 완료: {out_path}", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"[오류] 영상 합치기 실패: {e.stderr}", flush=True)
    finally:
        if os.path.exists(list_file_path):
            os.remove(list_file_path)

def add_background_music(video_path, bgm_path, out_path, total_duration):
    """영상에 배경음악을 추가합니다."""
    if not os.path.exists(bgm_path):
        print(f"[오류] 배경음악 파일 없음: {bgm_path}", flush=True)
        # BGM 없이 파일 복사
        shutil.copy(video_path, out_path)
        return

    print("4. 배경음악 추가 중 (페이드인/아웃 적용)...", flush=True)
    
    # FFmpeg 경로 찾기
    ffmpeg_path = find_ffmpeg()
    if not ffmpeg_path:
        print("[오류] FFmpeg를 찾을 수 없습니다. FFmpeg가 설치되어 있는지 확인하세요.", flush=True)
        # FFmpeg 없이 파일 복사
        shutil.copy(video_path, out_path)
        return
    
    cmd = [
        ffmpeg_path, "-y", "-i", video_path,
        "-stream_loop", "-1", "-i", bgm_path,
        "-filter_complex", f"[1:a]volume=0.4,afade=t=in:st=0:d=1,afade=t=out:st={total_duration-1}:d=1[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", out_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        print(f"   - 최종 영상 저장 완료: {out_path}", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"[오류] 배경음악 추가 실패: {e.stderr}", flush=True)

def cleanup(temp_dirs, temp_files):
    """임시 파일 및 폴더를 정리합니다."""
    print("5. 임시 파일 정리 중...", flush=True)
    time.sleep(1) # 파일 핸들이 해제될 때까지 잠시 대기

    # 임시 폴더 삭제 (재시도 로직 추가)
    for d in temp_dirs:
        if not os.path.exists(d):
            continue

        for i in range(3): # 최대 3번 재시도
            try:
                shutil.rmtree(d)
                print(f"   - 임시 폴더 삭제: {d}", flush=True)
                break # 성공 시 루프 탈출
            except Exception as e:
                print(f"   - 폴더 삭제 실패 (시도 {i+1}/3), 2초 후 재시도: {e}", flush=True)
                time.sleep(2)
        else: # for-else: 루프가 break 없이 끝나면 실행
            print(f"[경고] 임시 폴더({d})를 자동으로 삭제하지 못했습니다. 수동으로 삭제해주세요.", flush=True)

    # 임시 파일 삭제
    for f in temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"   - 임시 파일 삭제: {f}", flush=True)
            except Exception as e:
                print(f"[경고] 임시 파일({f})을 자동으로 삭제하지 못했습니다: {e}", flush=True)

if __name__ == "__main__":
    # --- 시작 전, 이전 최종 동영상 파일 삭제 ---
    if os.path.exists(VIDEO_OUT_DIR):
        for file in glob.glob(os.path.join(VIDEO_OUT_DIR, '*.mp4')):
            # single_clips 폴더 안의 파일은 삭제하지 않도록 예외 처리
            if 'single_clips' not in os.path.dirname(file):
                try:
                    os.remove(file)
                    print(f"[이전 파일 삭제] {file}", flush=True)
                except OSError as e:
                    print(f"[오류] 파일 삭제 실패: {file} ({e})", flush=True)
    # ------------------------------------

    # parody_card 폴더에서 이미지 목록 가져오기 (이름순 정렬)
    card_images = sorted(glob.glob(os.path.join(CARD_IMG_DIR, '*.png')))

    if not card_images:
        print("[오류] 'parody_card' 폴더에 이미지 파일이 없습니다. 스크립트를 종료합니다.", flush=True)
    else:
        # 1. 인트로 영상 생성 (앞)
        intro_clip = create_intro_video(INTRO_IMG_PATH, INTRO_CLIP_PATH, INTRO_DURATION)
        # 2. 카드 영상 생성
        card_clips = create_card_videos(card_images, CARD_DURATION)
        # 3. 인트로 영상 생성 (뒤)
        final_intro_clip = create_intro_video(INTRO_IMG_PATH, FINAL_INTRO_CLIP_PATH, INTRO_DURATION)
        # 4. 모든 클립 목록 결합 (인트로 + 카드 + 인트로)
        all_clips = ([intro_clip] if intro_clip else []) + card_clips + ([final_intro_clip] if final_intro_clip else [])

        if all_clips:
            # 5. 클립 합치기
            merge_videos(all_clips, MERGED_CLIP_PATH)

            # 6. BGM 추가
            total_video_duration = (INTRO_DURATION if intro_clip else 0) + (len(card_clips) * CARD_DURATION) + (INTRO_DURATION if final_intro_clip else 0)
            add_background_music(MERGED_CLIP_PATH, BGM_PATH, FINAL_VIDEO_PATH, total_video_duration)

            # 7. 임시 파일 정리
            cleanup(
                temp_dirs=[SINGLE_CLIP_DIR],
                temp_files=[MERGED_CLIP_PATH]
            )
            print(f"\n[완료] 모든 작업 완료! 최종 영상은 다음 경로에 저장되었습니다:\n{FINAL_VIDEO_PATH}", flush=True)

            # --- 최신 mp4 파일 1개만 남기고 나머지 삭제 ---
            mp4_files = [f for f in glob.glob(os.path.join(VIDEO_OUT_DIR, '*.mp4')) if 'single_clips' not in os.path.dirname(f)]
            if len(mp4_files) > 1:
                # 파일 생성시간 기준 내림차순 정렬
                mp4_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                # 최신 파일 1개만 남기고 나머지 삭제
                for old_file in mp4_files[1:]:
                    try:
                        os.remove(old_file)
                        print(f"[자동정리] 오래된 mp4 파일 삭제: {old_file}", flush=True)
                    except Exception as e:
                        print(f"[경고] mp4 파일 삭제 실패: {old_file} ({e})", flush=True)

            # --- single_clips 폴더 내부 mp4 파일 모두 삭제 ---
            single_clips_mp4 = glob.glob(os.path.join(SINGLE_CLIP_DIR, '*.mp4'))
            for clip_file in single_clips_mp4:
                try:
                    os.remove(clip_file)
                    print(f"[자동정리] single_clips mp4 파일 삭제: {clip_file}", flush=True)
                except Exception as e:
                    print(f"[경고] single_clips mp4 파일 삭제 실패: {clip_file} ({e})", flush=True)
        else:
            print("[오류] 생성된 영상 클립이 없어 동영상 제작을 중단합니다.", flush=True) 