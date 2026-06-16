# 서비스 계정이 사용자 Drive에 접근하도록 설정하기

## 문제 상황
- 서비스 계정의 Drive 할당량(15GB)이 초과되어 파일 생성 실패
- 사용자 Drive는 5.7GB/2TB로 여유 공간 충분

## 해결 방법: 사용자 Drive에 서비스 계정 공유

### 방법 1: 사용자 Drive 폴더에 서비스 계정 공유 (권장)

1. **Google Drive 접속**
   - https://drive.google.com 접속
   - 사용자 계정으로 로그인

2. **폴더 생성 또는 기존 폴더 선택**
   - `내문서함` 폴더 생성 (없는 경우)
   - 또는 기존 폴더 사용

3. **서비스 계정 이메일로 공유**
   - 폴더 우클릭 > "공유" 선택
   - 공유할 사용자/그룹 추가:
     ```
     ou-stock-parody-account@ou-stock-parody01.iam.gserviceaccount.com
     ```
   - 권한: "편집자" 또는 "뷰어" (파일 생성이 필요하면 "편집자")
   - "알림 보내기" 체크 해제 (서비스 계정은 이메일을 받지 않음)
   - "공유" 클릭

4. **코드 수정**
   - `find_or_create_folder` 함수에서 공유된 폴더 ID를 직접 사용
   - 또는 폴더 이름으로 검색 (공유된 폴더도 검색 가능)

### 방법 2: Domain-wide Delegation 설정 (고급)

Google Workspace 도메인을 사용하는 경우:
1. Google Cloud Console > IAM & Admin > Service Accounts
2. 서비스 계정 선택 > "Domain-wide delegation" 활성화
3. OAuth 동의 화면 설정
4. 사용자 계정으로 인증하여 사용자 Drive 접근

### 방법 3: 코드에서 공유된 폴더 ID 사용

공유된 폴더의 ID를 직접 사용:

```python
# 공유된 폴더 ID (URL에서 확인 가능)
SHARED_FOLDER_ID = "폴더ID"

# 폴더 ID를 직접 사용
stock_parody_folder_id = find_or_create_folder(
    drive_service, 
    'stock_parody', 
    SHARED_FOLDER_ID
)
```

## 확인 방법

1. **공유 확인**
   - Google Drive에서 폴더 우클릭 > "공유" 메뉴
   - 서비스 계정 이메일이 공유 목록에 있는지 확인

2. **코드 테스트**
   - `step1_senior_ou_news_parody_collection.py` 실행
   - 파일이 사용자 Drive에 생성되는지 확인

## 참고

- 서비스 계정 이메일: `ou-stock-parody-account@ou-stock-parody01.iam.gserviceaccount.com`
- 공유된 폴더는 서비스 계정의 Drive 할당량이 아닌 사용자 Drive 할당량을 사용
- 사용자 Drive는 2TB이므로 충분한 공간 확보



