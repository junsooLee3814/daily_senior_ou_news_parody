#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
이모지 문자를 일반 텍스트로 변환하는 스크립트
"""

import re

def fix_emojis_in_file(file_path):
    """파일의 이모지를 일반 텍스트로 변환"""
    
    # 이모지와 대체 텍스트 매핑
    emoji_replacements = {
        '🔍': '[검색]',
        '⏰': '[시간]',
        '🏗️': '[GitHub]',
        '💻': '[로컬]',
        '📄': '[파일]',
        '🔄': '[새로고침]',
        '✅': '[OK]',
        '❌': '[ERROR]',
        '⚠️': '[경고]',
        '💡': '[팁]',
        '💾': '[저장]',
        '📁': '[폴더]',
        '📹': '[동영상]',
        '📊': '[통계]',
        '🎯': '[타겟]',
        '📝': '[설명]',
        '🏷️': '[태그]',
        '⚖️': '[법적]',
        '📋': '[목록]',
        '🔑': '[키워드]',
        '🚀': '[시작]',
        '🎉': '[완료]',
        '📺': '[영상]',
        '🔔': '[알림]',
        '👍': '[좋아요]',
        '📢': '[공유]',
        '💪': '[힘내]',
        '🗑️': '[삭제]',
        '▶️': '[재생]',
        '💥': '[핫]',
        '🔥': '[핫]',
        '👨‍👩‍👧‍👦': '[가족]',
        '💬': '[댓글]',
        '🔔': '[알림]',
        '👍': '[좋아요]',
        '📢': '[공유]',
        '💪': '[힘내]',
        '🗑️': '[삭제]',
        '▶️': '[재생]',
        '💥': '[핫]',
        '🔥': '[핫]',
        '👨‍👩‍👧‍👦': '[가족]',
        '💬': '[댓글]'
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 이모지 치환
        for emoji, replacement in emoji_replacements.items():
            content = content.replace(emoji, replacement)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[OK] {file_path} 이모지 변환 완료")
        return True
        
    except Exception as e:
        print(f"[ERROR] {file_path} 변환 실패: {e}")
        return False

if __name__ == "__main__":
    file_path = "youtube_uploader/upload_to_youtube.py"
    fix_emojis_in_file(file_path)
