# 🚀 KCS Messenger - 빠른 시작 가이드

## 📱 KakaoTalk 클론 메신저

정확한 KakaoTalk 디자인을 구현한 Python 기반 실시간 메신저입니다.

![KakaoTalk UI](docs/screenshot.png)

## ⚡ 1분 안에 시작하기

### Windows 사용자

1. **실행 파일 더블클릭:**
   ```
   run.bat
   ```

2. **메뉴 선택:**
   - `1` - 정확한 KakaoTalk 복제 (스크린샷 일치) **[최신]**
   - `2` - 개선된 UI 버전 **[권장]**
   - `3` - 기본 독립 실행 UI
   - `4` - 전체 실행 (서버 + 클라이언트)

### Mac/Linux 사용자

```bash
# 의존성 설치
pip install PyQt5

# 정확한 복제 버전 (최신)
python kakaotalk_exact_replica.py

# 개선된 UI (권장)
python kakaotalk_improved.py

# 또는 전체 실행
python run_messenger.py
```

## 🎯 주요 기능

### 구현 완료 ✅
- **KakaoTalk 정확한 UI 복제**
  - 노란색 말풍선 (보낸 메시지)
  - 흰색 말풍선 (받은 메시지)
  - 프로필 이미지
  - 한국식 시간 표시 (오전/오후)

- **실시간 메시징**
  - WebSocket 통신
  - 즉시 메시지 전달
  - 타이핑 인디케이터

- **사용자 인증**
  - 로그인 화면
  - 사용자 프로필

### 구현 예정 🔄
- 읽음 확인
- 이모지 리액션
- 파일 전송
- 음성/영상 통화

## 📂 프로젝트 구조

```
kcsmessager/
├── run.bat                      # Windows 실행 파일
├── kakaotalk_exact_replica.py  # 스크린샷 정확한 복제 (최신)
├── kakaotalk_improved.py       # 개선된 UI 메신저 (권장)
├── kakaotalk_standalone.py     # 기본 독립 실행 메신저
├── run_messenger.py             # 메인 런처
├── client/
│   └── desktop/
│       ├── kakaotalk_ui.py     # KakaoTalk UI 컴포넌트
│       └── kakaotalk_integrated.py  # 서버 연동 클라이언트
├── server/
│   └── core/
│       └── async_server.py     # WebSocket 서버
└── docs/
    └── KAKAOTALK_UI_GUIDE.md   # UI 가이드
```

## 🔧 문제 해결

### PyQt5 설치 오류

```bash
# Windows
pip install PyQt5 --only-binary :all:

# Mac
brew install pyqt5

# Linux
sudo apt-get install python3-pyqt5
```

### 서버 연결 실패

서버 없이 UI만 테스트:
```bash
python kakaotalk_improved.py
# 또는 기본 버전
python kakaotalk_standalone.py
```

### 한글 깨짐

시스템 폰트 설정:
- Windows: 맑은 고딕 자동 사용
- Mac/Linux: 시스템 한글 폰트 설정 필요

## 💻 개발 모드

### 빠른 독립 실행 (권장)
```bash
python kakaotalk_improved.py
```

### 서버만 실행
```bash
python server/core/async_server.py
```

### 클라이언트만 실행
```bash
python client/desktop/kakaotalk_integrated.py
```

### UI 컴포넌트 테스트
```bash
python client/desktop/kakaotalk_ui.py
```

## 📊 시스템 요구사항

- **Python**: 3.8 이상
- **RAM**: 2GB 이상
- **OS**: Windows 10/11, macOS 10.14+, Ubuntu 18.04+
- **네트워크**: 로컬 실행 (인터넷 불필요)

## 🎨 UI 특징

### KakaoTalk 정확한 복제
- **색상**: #FFE400 (카카오 노란색)
- **폰트**: 맑은 고딕
- **레이아웃**: 1:1 동일
- **아이콘**: 이모지 기반

### 반응형 디자인
- 창 크기 조절 가능
- 스크롤 자동 조정
- 고DPI 지원

## 📝 라이선스

교육 목적 프로젝트입니다. KakaoTalk는 Kakao Corp의 상표입니다.

## 🆘 도움말

### 설치 확인
```bash
python test_installation.py
```

### 전체 문서
- [설치 가이드](INSTALLATION.md)
- [시스템 설계](docs/SYSTEM_DESIGN.md)
- [UI 가이드](docs/KAKAOTALK_UI_GUIDE.md)

---

**🎉 준비 완료! run.bat을 실행하세요!**