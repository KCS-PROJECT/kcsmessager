# KCS Messenger - 배포 가이드

## 📦 Windows 사용자용 배포 패키지 만들기

### 단계 1: Windows에서 exe 빌드

Windows PC에서 다음 명령 실행:

```batch
# 방법 1: 자동 빌드
QUICK_START_WINDOWS.bat

# 방법 2: 수동 빌드
build_windows.bat --clean
```

빌드 완료 후 `dist/KCS_Messenger.exe` 파일이 생성됩니다.

### 단계 2: 배포 패키지 생성

#### 옵션 A: 단일 exe 파일 배포 (권장)
```
dist/KCS_Messenger.exe (약 40-50MB)
```

**장점:**
- 파일 1개만 배포
- 사용자가 바로 실행 가능
- Python 설치 불필요

**단점:**
- 첫 실행 시 압축 해제로 약간 느림
- 파일 크기가 큼

#### 옵션 B: 폴더 형태 배포
```batch
# onedir 모드로 빌드
python build_windows.py --onedir
```

생성된 `dist/KCS_Messenger/` 폴더 전체를 배포

**장점:**
- 실행 속도 빠름
- 필요시 파일 수정 가능

**단점:**
- 여러 파일 관리 필요
- 사용자가 폴더 구조 유지해야 함

### 단계 3: 배포 패키지 구성

#### 최소 배포 (사용자용)
```
KCS_Messenger_v1.0/
├── KCS_Messenger.exe       # 실행파일
├── README.txt              # 간단한 사용 설명
└── 실행하기.bat            # 더블클릭 실행 스크립트
```

#### 완전 배포 (개발자용)
```
KCS_Messenger_v1.0/
├── KCS_Messenger.exe
├── README.txt
├── 실행하기.bat
├── build_windows.bat       # 재빌드용
├── build_windows.py
├── requirements_windows.txt
└── source/                 # 소스코드 (선택사항)
```

## 📝 배포 파일 준비 스크립트

아래 스크립트를 `prepare_distribution.bat`로 저장:

```batch
@echo off
echo KCS Messenger 배포 패키지 생성...

set VERSION=1.0
set DIST_DIR=KCS_Messenger_v%VERSION%

if exist %DIST_DIR% rmdir /s /q %DIST_DIR%
mkdir %DIST_DIR%

echo exe 파일 복사...
copy dist\KCS_Messenger.exe %DIST_DIR%\

echo 실행 스크립트 생성...
(
echo @echo off
echo start "" "KCS_Messenger.exe"
) > %DIST_DIR%\실행하기.bat

echo README 생성...
(
echo ================================================
echo    KCS Messenger v%VERSION%
echo ================================================
echo.
echo [실행 방법]
echo 1. KCS_Messenger.exe 더블클릭
echo 또는
echo 2. "실행하기.bat" 더블클릭
echo.
echo [시스템 요구사항]
echo - Windows 10 이상
echo - 인터넷 연결 ^(실시간 채팅 기능 사용시^)
echo.
echo [첫 실행 시 Windows Defender 경고]
echo "추가 정보" ^> "실행" 클릭
echo.
echo [문의]
echo GitHub: https://github.com/your-repo/kcsmessager
) > %DIST_DIR%\README.txt

echo.
echo 배포 패키지 생성 완료: %DIST_DIR%\
echo.
pause
```

## 🌐 온라인 배포 방법

### GitHub Releases 배포

1. **Release 생성**
```bash
git tag -a v1.0 -m "Release version 1.0"
git push origin v1.0
```

2. **GitHub에서 Release 생성**
   - Releases → "Create a new release"
   - Tag 선택: v1.0
   - Release title: KCS Messenger v1.0
   - 파일 업로드: `KCS_Messenger.exe` 또는 `.zip` 패키지

3. **다운로드 링크**
```
https://github.com/your-username/kcsmessager/releases/download/v1.0/KCS_Messenger.exe
```

### Google Drive / Dropbox 배포

1. 배포 패키지를 zip으로 압축
2. 클라우드에 업로드
3. 공유 링크 생성
4. 사용자에게 링크 배포

## 📊 배포 체크리스트

빌드 전:
- [ ] 모든 기능 테스트 완료
- [ ] 버전 번호 업데이트
- [ ] README 업데이트
- [ ] 불필요한 파일 제거

빌드:
- [ ] Windows에서 빌드 실행
- [ ] exe 파일 정상 동작 확인
- [ ] 다른 Windows PC에서 테스트

배포:
- [ ] README 포함
- [ ] 실행 스크립트 포함
- [ ] 압축 파일 생성
- [ ] 다운로드 링크 테스트

## 🔒 코드 서명 (선택사항)

Windows Defender 경고를 줄이려면:

1. **코드 서명 인증서 구매**
   - Sectigo, DigiCert 등

2. **signtool로 서명**
```batch
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com KCS_Messenger.exe
```

3. **장점**
   - Windows Defender 경고 감소
   - 신뢰도 향상
   - 전문적인 이미지

**비용:** 연간 약 $100-300

## 📈 사용자 설치 통계 (선택사항)

간단한 다운로드 카운터:

```python
# download_counter.py
import requests

def track_download():
    requests.post('https://your-api.com/download', json={
        'version': '1.0',
        'platform': 'windows'
    })
```

## 💡 배포 팁

1. **파일명에 버전 포함**
   - `KCS_Messenger_v1.0.exe`
   - 사용자가 버전 확인 가능

2. **변경사항 문서화**
   - CHANGELOG.md 작성
   - 각 버전의 새 기능/수정사항 기록

3. **자동 업데이트 고려**
   - GitHub API로 최신 버전 확인
   - 업데이트 알림 표시

4. **다양한 배포 채널**
   - GitHub Releases (개발자용)
   - Google Drive (일반 사용자용)
   - Microsoft Store (공식 배포)

## 🎯 사용자 가이드 예시

배포 패키지의 README.txt:

```
================================================
   KCS Messenger v1.0 - 카카오톡 스타일 메신저
================================================

[빠른 시작]
1. KCS_Messenger.exe 더블클릭
2. 사용자 이름 입력
3. 채팅 시작!

[기능]
✓ 실시간 채팅
✓ 독립 실행 모드
✓ 카카오톡 스타일 UI
✓ 한글 완벽 지원

[시스템 요구사항]
- Windows 10 이상
- 메모리: 최소 2GB
- 저장공간: 100MB

[문제 해결]
Q: Windows Defender 경고가 나타나요
A: "추가 정보" > "실행" 클릭

Q: 프로그램이 실행되지 않아요
A: Visual C++ 재배포 가능 패키지 설치
   https://aka.ms/vs/17/release/vc_redist.x64.exe

[지원]
- 이메일: support@example.com
- GitHub: github.com/your-repo
================================================
```