#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""개인 구글 계정 Drive/Docs OAuth 토큰 발급 스크립트."""

from utils.google_oauth import DRIVE_TOKEN_FILE, OAUTH_CLIENT_FILE, authorize_drive_oauth


def main() -> None:
    print("Drive/Docs OAuth 토큰 발급을 시작합니다.")
    print(f"클라이언트 파일: {OAUTH_CLIENT_FILE}")
    print(f"토큰 저장 위치: {DRIVE_TOKEN_FILE}")
    print("브라우저에서 구글 로그인 및 권한 허용을 완료하세요.\n")

    if authorize_drive_oauth():
        print(f"\n[완료] 토큰이 저장되었습니다: {DRIVE_TOKEN_FILE}")
    else:
        print("\n[실패] 토큰 발급에 실패했습니다.")


if __name__ == "__main__":
    main()
