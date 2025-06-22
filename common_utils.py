import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
import json
import traceback

# .env 파일에서 환경 변수를 로드
load_dotenv()

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]
CREDS_FILE = "service_account.json"

def get_gspread_client():
    """gspread 클라이언트를 인증하고 반환합니다."""
    try:
        if not os.path.exists(CREDS_FILE):
            raise FileNotFoundError(f"인증 파일 '{CREDS_FILE}'을(를) 찾을 수 없습니다.")
        creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPE)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"  ! gspread 클라이언트 인증 중 심각한 오류 발생: {e}")
        raise

def get_gsheet(spreadsheet_id, worksheet_name=None):
    """주어진 ID와 워크시트 이름으로 gspread 워크시트 객체를 반환합니다."""
    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        if worksheet_name:
            try:
                worksheet = spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                print(f"  - 워크시트 '{worksheet_name}'을(를) 찾을 수 없어 새로 생성합니다.")
                worksheet = spreadsheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
        else:
            worksheet = spreadsheet.sheet1
        return worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"  ! 스프레드시트 ID '{spreadsheet_id}'을(를) 찾을 수 없습니다.")
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"  ! 구글 시트 워크시트를 가져오는 중 오류 발생: {e}")
        traceback.print_exc()
        raise 