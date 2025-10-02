# KCS Messenger - Windows 실행 가이드

## 🚀 빠른 시작 (Python 없이 실행)

이미 빌드된 exe 파일이 있다면:
1. `dist/KCS_Messenger.exe` 더블클릭
2. 또는 `run_messenger.bat` 실행

## 📦 직접 빌드하기 (개발자용)

### 필수 요구사항
- Windows 10 이상
- Python 3.8 이상 ([다운로드](https://www.python.org/downloads/))
- 설치 시 "Add Python to PATH" 체크 필수!

### 빌드 방법

#### 방법 1: 자동 빌드 (권장)
```batch
build_windows.bat
```

#### 방법 2: Python 스크립트 사용
```batch
python build_windows.py --clean
```

#### 방법 3: 수동 빌드
```batch
# 1. 필수 패키지 설치
pip install -r requirements_windows.txt

# 2. PyInstaller로 빌드
pyinstaller kakaotalk_launcher_windows.spec --clean --onefile

# 3. 실행
dist\KCS_Messenger.exe
```

## 🎮 실행 방법

### 빌드된 exe 실행
1. **파일 탐색기**: `dist/KCS_Messenger.exe` 더블클릭
2. **배치 파일**: `run_messenger.bat` 더블클릭
3. **명령 프롬프트**:
   ```batch
   dist\KCS_Messenger.exe
   ```

## 🛡️ Windows Defender 경고

첫 실행 시 Windows Defender가 경고를 표시할 수 있습니다:
1. "Windows의 PC 보호" 창이 나타나면
2. "추가 정보" 클릭
3. "실행" 버튼 클릭

## 📋 파일 설명

| 파일명 | 설명 |
|--------|------|
| `build_windows.bat` | Windows용 자동 빌드 스크립트 |
| `build_windows.py` | Windows 빌드 Python 스크립트 |
| `run_messenger.bat` | 실행파일 실행 스크립트 |
| `kakaotalk_launcher_windows.spec` | PyInstaller Windows 설정 |
| `requirements_windows.txt` | Windows 필수 패키지 목록 |
| `dist/KCS_Messenger.exe` | 생성된 실행파일 |

## 🔧 빌드 옵션

```batch
# 기본 빌드 (단일 exe 파일)
build_windows.bat

# 클린 빌드 (이전 파일 삭제)
build_windows.bat --clean

# 디버그 모드
build_windows.bat --debug

# 폴더 형태로 빌드
build_windows.bat --onedir

# 설치 프로그램 스크립트 생성
build_windows.bat --installer
```

## 🎯 특징

- ✅ **독립 실행**: Python 설치 없이 실행 가능
- ✅ **한국어 지원**: UTF-8 인코딩, 한글 폰트 지원
- ✅ **GUI 앱**: 콘솔 창 없이 실행
- ✅ **경량화**: 불필요한 패키지 제외
- ✅ **Windows 10/11 호환**: 최신 Windows 지원

## ❓ 문제 해결

### Python을 찾을 수 없다는 오류
1. Python 3.8 이상 설치: https://www.python.org/downloads/
2. 설치 시 "Add Python to PATH" 체크
3. CMD 재시작 후 다시 시도

### PyQt5 관련 오류
```batch
pip install --upgrade PyQt5
```

### 빌드 실패
```batch
# 캐시 정리 후 재빌드
build_windows.bat --clean --fresh
```

### 실행 시 DLL 오류
Visual C++ 재배포 가능 패키지 설치:
- [Microsoft Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist)

## 📝 개발자 참고사항

### 아이콘 추가
1. `assets/icon.ico` 파일 생성
2. spec 파일이 자동으로 아이콘 적용

### 버전 정보 커스터마이징
`version_info.txt` 파일 수정 후 재빌드

### 설치 프로그램 만들기
1. NSIS 설치: https://nsis.sourceforge.io/
2. `python build_windows.py --installer` 실행
3. `installer.nsi` 파일로 설치 프로그램 생성

## 💡 팁

- 파일 크기를 줄이려면 `--onefile` 대신 `--onedir` 사용
- 빠른 시작을 위해 바탕화면에 바로가기 생성 권장
- 정기적으로 `--clean` 옵션으로 클린 빌드 수행