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


def get_drive_oauth_credentials() -> Credentials:
    """Drive/Docs용 OAuth 자격증명을 반환합니다."""
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
        creds = get_drive_oauth_credentials()
        return bool(creds and creds.valid)
    except Exception as exc:
        print(f"[오류] Drive OAuth 인증 실패: {exc}")
        return False
