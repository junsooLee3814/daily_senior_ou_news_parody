"""개인 구글 계정 OAuth 인증 (Drive / Docs)."""

from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCRIPT_DIR = Path(__file__).resolve().parent.parent
OAUTH_CLIENT_FILE = SCRIPT_DIR / "youtube_uploader" / "client_secrets.json"
DRIVE_TOKEN_FILE = SCRIPT_DIR / "config" / "drive_token.json"

DRIVE_DOCS_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
]


def get_drive_oauth_credentials(interactive: bool = False) -> Credentials:
    """Drive/Docs용 OAuth 자격증명을 반환합니다.

    interactive=False(기본): 저장된 토큰만 사용. 없으면 예외를 던집니다.
        (CI/서버 환경에서 브라우저 로그인으로 멈추는 것을 방지)
    interactive=True: 토큰이 없으면 브라우저 로그인 플로우를 실행합니다.
    """
    creds = None

    if DRIVE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(
            str(DRIVE_TOKEN_FILE), DRIVE_DOCS_SCOPES
        )

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        DRIVE_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        DRIVE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    if not creds or not creds.valid:
        if not interactive:
            raise FileNotFoundError(
                f"유효한 Drive OAuth 토큰이 없습니다: {DRIVE_TOKEN_FILE}. "
                "로컬에서 'python refresh_drive_token.py'로 토큰을 먼저 발급하세요."
            )

        if not OAUTH_CLIENT_FILE.exists():
            raise FileNotFoundError(
                f"OAuth 클라이언트 파일이 없습니다: {OAUTH_CLIENT_FILE}"
            )

        flow = InstalledAppFlow.from_client_secrets_file(
            str(OAUTH_CLIENT_FILE), DRIVE_DOCS_SCOPES
        )
        creds = flow.run_local_server(port=0)

        DRIVE_TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        DRIVE_TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

    return creds


def authorize_drive_oauth() -> bool:
    """브라우저 로그인으로 Drive/Docs 토큰을 발급합니다."""
    try:
        creds = get_drive_oauth_credentials(interactive=True)
        return bool(creds and creds.valid)
    except Exception as exc:
        print(f"[오류] Drive OAuth 인증 실패: {exc}")
        return False
