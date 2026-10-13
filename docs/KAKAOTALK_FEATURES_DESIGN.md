# KakaoTalk 스타일 기능 설계 문서

카카오톡의 주요 UI/UX 기능을 KCS Messenger에 적용하기 위한 종합 설계 문서

## 목차
1. [섹션별 접기/펼치기 기능](#1-섹션별-접기펼치기-기능)
2. [즐겨찾기 기능](#2-즐겨찾기-기능)
3. [업데이트한 프로필 표시](#3-업데이트한-프로필-표시)
4. [생일 표시 및 선물하기](#4-생일-표시-및-선물하기)
5. [채널 기능](#5-채널-기능)
6. [다크 모드 지원](#6-다크-모드-지원)

---

## 1. 섹션별 접기/펼치기 기능

### 개요
각 섹션(즐겨찾기, 업데이트한 프로필, 온라인 친구, 생일인 친구 등)을 사용자가 접거나 펼칠 수 있는 기능

### 데이터 구조
```python
class FriendsTab:
    def __init__(self):
        # 섹션 접기/펼치기 상태 저장
        self.section_states = {
            'favorites': True,      # 즐겨찾기 (기본 펼침)
            'updated_profile': True, # 업데이트한 프로필 (기본 펼침)
            'birthday': True,        # 생일인 친구 (기본 펼침)
            'online': True,          # 온라인 친구 (기본 펼침)
            'offline': False,        # 오프라인 친구 (기본 접힘)
            'channels': False        # 채널 (기본 접힘)
        }
```

### UI 컴포넌트
**CollapsibleSectionHeader 위젯:**
```python
class CollapsibleSectionHeader(QWidget):
    clicked = pyqtSignal(str)  # section_name

    def __init__(self, section_name, title, count, is_expanded=True):
        self.section_name = section_name
        self.title = title
        self.count = count
        self.is_expanded = is_expanded

        # 화살표 아이콘 (▼ 펼침 / ▶ 접힘)
        self.arrow_label = QLabel("▼" if is_expanded else "▶")

        # 제목 + 카운트
        self.title_label = QLabel(f"{title} {count}")
```

### 필요한 SVG 아이콘
- `chevron-down.svg` - 펼침 상태 (▼)
- `chevron-right.svg` - 접힘 상태 (▶)

### 구현 흐름
1. 섹션 헤더 클릭 → `toggle_section(section_name)` 호출
2. `section_states[section_name]` 토글
3. `refresh_user_list()` 호출하여 UI 갱신
4. 접힌 섹션은 헤더만 표시, 아이템은 숨김

---

## 2. 즐겨찾기 기능

### 개요
중요한 친구를 즐겨찾기로 지정하여 목록 최상단에 표시

### 데이터 구조
```python
class FriendsTab:
    def __init__(self):
        self.favorites = set()  # {'홍길동', '김철수'}
```

### UI 컴포넌트
**FriendListItemWidget 확장:**
- 별 아이콘 추가 (즐겨찾기 토글 버튼)
- 즐겨찾기된 친구는 노란색 별(★), 아니면 회색 별(☆)

**우클릭 컨텍스트 메뉴 확장:**
```python
def show_context_menu(self, position):
    menu = QMenu(self)
    chat_action = menu.addAction(f"💬 {username}님과 대화하기")

    # 즐겨찾기 추가/제거
    if username in self.favorites:
        fav_action = menu.addAction(f"☆ 즐겨찾기 해제")
    else:
        fav_action = menu.addAction(f"★ 즐겨찾기 추가")
```

### 필요한 SVG 아이콘
- `star.svg` - 즐겨찾기 (채워진 별)
- `star-outline.svg` - 즐겨찾기 아님 (빈 별)

### 섹션 순서
```
1. 즐겨찾기 (접기/펼치기 가능)
2. 업데이트한 프로필
3. 생일인 친구
4. 온라인 친구
5. 오프라인 친구
6. 채널
```

---

## 3. 업데이트한 프로필 표시

### 개요
최근 7일 이내에 프로필을 변경한 친구를 별도 섹션에 표시

### 데이터 구조
```python
class FriendsTab:
    def __init__(self):
        # 프로필 업데이트 타임스탬프
        self.profile_updates = {
            '노승한': datetime(2025, 10, 14, 15, 30),
            '정현아': datetime(2025, 10, 13, 10, 20),
            '박희정': datetime(2025, 10, 12, 18, 45)
        }
```

### UI 컴포넌트
**UpdatedProfileItemWidget:**
- 원형 프로필 이미지 (더 큰 사이즈: 60x60)
- 이름 하단 표시
- 주황색 점 표시 (업데이트 인디케이터)
- 가로 스크롤 가능한 레이아웃

```python
class UpdatedProfileItemWidget(QWidget):
    def __init__(self, username, profile_image_url=None):
        # 60x60 원형 프로필 이미지
        # 우측 상단에 주황색 점 (새 업데이트 표시)
        # 하단에 이름
```

### 레이아웃
- 가로 스크롤 뷰 사용 (QScrollArea + horizontal layout)
- 최대 3-4개 동시 표시, 스크롤로 더 보기

---

## 4. 생일 표시 및 선물하기

### 개요
생일인 친구와 생일이 임박한 친구를 표시하고 선물하기 버튼 제공

### 데이터 구조
```python
class FriendsTab:
    def __init__(self):
        # 생일 정보 (월-일)
        self.birthdays = {
            '도기현': (10, 16),  # 10월 16일
            '장모님': (10, 16),
            '조원택': (10, 16),
            '후지타 리카코': (10, 16)
        }
```

### UI 컴포넌트
**BirthdayItemWidget:**
```python
class BirthdayItemWidget(QWidget):
    gift_clicked = pyqtSignal(str)  # username

    def __init__(self, username, birthday_date):
        # 원형 프로필 이미지
        # 이름
        # 🎂 케이크 아이콘
        # "오늘 10월 16일" 텍스트
        # "선물하기" 버튼 (우측)
```

### 선물하기 버튼
- 둥근 테두리, 어두운 배경
- 클릭 시 선물하기 다이얼로그 표시 (현재는 메시지만)
```python
def on_gift_click(self, username):
    QMessageBox.information(self, "선물하기",
        f"{username}님에게 선물을 보내시겠습니까?\n(추후 구현 예정)")
```

### 필요한 SVG 아이콘
- `cake.svg` - 생일 케이크 아이콘
- `gift.svg` - 선물 아이콘

---

## 5. 채널 기능

### 개요
공식 채널, 그룹 채널 등을 구독하고 관리하는 기능

### 데이터 구조
```python
class FriendsTab:
    def __init__(self):
        # 구독 중인 채널 목록
        self.channels = [
            {
                'name': 'marie claire',
                'id': 'marieclairekorea',
                'icon': 'marie_claire_logo.png',
                'description': '우아하고 강인한 목소리를 내는 동시대적인 패...',
                'verified': True  # 인증 채널
            },
            {
                'name': '채널 110',
                'id': 'channel110',
                'icon': 'Ch',  # 텍스트 아이콘
                'description': '',
                'verified': False
            }
        ]
```

### UI 컴포넌트
**ChannelItemWidget:**
```python
class ChannelItemWidget(QWidget):
    def __init__(self, channel_data):
        # 원형 또는 사각형 채널 아이콘
        # 채널 이름
        # 인증 배지 (파란색 체크마크)
        # 설명 (1줄, 말줄임표)
```

### 필요한 SVG 아이콘
- `verified.svg` - 인증 배지 (파란색 체크마크)
- `channel.svg` - 채널 기본 아이콘

---

## 6. 다크 모드 지원

### 개요
라이트 모드와 다크 모드를 전환할 수 있는 테마 시스템

### 아키텍처
**ThemeManager 싱글톤:**
```python
class ThemeManager:
    _instance = None

    def __init__(self):
        self.current_theme = 'light'  # 'light' or 'dark'
        self.themes = {
            'light': {
                'bg_primary': '#FFFFFF',
                'bg_secondary': '#F8F8F8',
                'bg_tertiary': '#FAFAFA',
                'text_primary': '#333333',
                'text_secondary': '#666666',
                'text_tertiary': '#999999',
                'border': '#E0E0E0',
                'accent': '#FFE400',
                'sidebar_bg': '#3A3A3C',
                'online_indicator': '#00D000'
            },
            'dark': {
                'bg_primary': '#1C1C1E',
                'bg_secondary': '#2C2C2E',
                'bg_tertiary': '#3A3A3C',
                'text_primary': '#FFFFFF',
                'text_secondary': '#AEAEB2',
                'text_tertiary': '#8E8E93',
                'border': '#38383A',
                'accent': '#FFD60A',
                'sidebar_bg': '#000000',
                'online_indicator': '#30D158'
            }
        }

    def get_color(self, key):
        return self.themes[self.current_theme][key]

    def toggle_theme(self):
        self.current_theme = 'dark' if self.current_theme == 'light' else 'light'
        # 모든 위젯 스타일 업데이트
```

### 구현 전략
1. **ThemeManager 생성** (`utils/theme_manager.py`)
2. **모든 QWidget 스타일을 동적으로 생성**
   ```python
   def get_header_style(self):
       return f"""
           QWidget {{
               background-color: {theme_manager.get_color('bg_secondary')};
               border-bottom: 1px solid {theme_manager.get_color('border')};
           }}
       """
   ```
3. **테마 변경 Signal**
   ```python
   class ThemeManager(QObject):
       theme_changed = pyqtSignal(str)  # 'light' or 'dark'
   ```
4. **모든 위젯에서 theme_changed Signal 구독**
   ```python
   theme_manager.theme_changed.connect(self.update_theme)
   ```

### 다크 모드 UI 차이점
- 배경: 흰색 → 어두운 회색/검정
- 텍스트: 검정 → 흰색
- 테두리: 밝은 회색 → 어두운 회색
- 사이드바: 어두운 회색 → 완전 검정
- 액센트 색상: 카카오톡 노란색 → 더 밝은 노란색
- 온라인 인디케이터: 녹색 → 더 밝은 녹색

---

## 통합 데이터 모델

### UserProfile 클래스
```python
class UserProfile:
    def __init__(self, username):
        self.username = username
        self.is_online = False
        self.is_favorite = False
        self.birthday = None  # (month, day) tuple
        self.profile_updated_at = None  # datetime
        self.profile_image_url = None
        self.status_message = ""
```

### FriendsTab 확장 데이터 구조
```python
class FriendsTab(QWidget):
    def __init__(self, my_username, parent=None):
        # 기존
        self.my_username = my_username
        self.all_users = []
        self.online_users = set()
        self.unread_counts = {}
        self.item_widgets = {}

        # 새로 추가
        self.favorites = set()
        self.section_states = {
            'favorites': True,
            'updated_profile': True,
            'birthday': True,
            'online': True,
            'offline': False,
            'channels': False
        }
        self.profile_updates = {}  # {username: datetime}
        self.birthdays = {}  # {username: (month, day)}
        self.channels = []  # [{name, id, icon, description, verified}]
```

---

## 구현 우선순위

### Phase 1: 기본 구조 (가장 중요)
1. **섹션별 접기/펼치기** - 모든 섹션의 기반 기능
2. **즐겨찾기** - 데이터 구조 단순, UI 영향 큼

### Phase 2: 콘텐츠 섹션
3. **업데이트한 프로필** - 새로운 UI 패턴 (가로 스크롤)
4. **생일 표시 및 선물하기** - 인터랙션 추가

### Phase 3: 확장 기능
5. **채널** - 별도 데이터 소스, 독립적
6. **다크 모드** - 전체 UI 영향, 가장 복잡

---

## 필요한 SVG 아이콘 목록

### 새로 생성할 아이콘
1. `chevron-down.svg` - 섹션 펼침 표시
2. `chevron-right.svg` - 섹션 접힘 표시
3. `star.svg` - 즐겨찾기 (채워진 별)
4. `star-outline.svg` - 즐겨찾기 아님 (빈 별)
5. `cake.svg` - 생일 케이크
6. `gift.svg` - 선물
7. `verified.svg` - 인증 배지
8. `channel.svg` - 채널 아이콘
9. `moon.svg` - 다크 모드 토글
10. `sun.svg` - 라이트 모드 토글

### 아이콘 위치
```
assets/icons/
├── actions/
│   ├── chevron-down.svg
│   ├── chevron-right.svg
│   ├── star.svg
│   ├── star-outline.svg
│   ├── cake.svg
│   └── gift.svg
├── misc/
│   ├── verified.svg
│   ├── channel.svg
│   ├── moon.svg
│   └── sun.svg
```

---

## 테스트 데이터

### 샘플 친구 데이터
```python
SAMPLE_DATA = {
    'favorites': ['홍길동', '김철수'],
    'profile_updates': {
        '노승한': datetime(2025, 10, 14, 15, 30),
        '정현아': datetime(2025, 10, 13, 10, 20),
        '박희정': datetime(2025, 10, 12, 18, 45)
    },
    'birthdays': {
        '도기현': (10, 16),
        '장모님': (10, 16),
        '조원택': (10, 16),
        '후지타 리카코': (10, 16)
    },
    'channels': [
        {
            'name': 'marie claire',
            'id': 'marieclairekorea',
            'icon_text': 'MC',
            'description': '우아하고 강인한 목소리를 내는 동시대적인 패...',
            'verified': True
        },
        {
            'name': '채널 110',
            'id': 'channel110',
            'icon_text': 'Ch',
            'description': '',
            'verified': False
        }
    ]
}
```

---

## 성능 고려사항

### 최적화 전략
1. **섹션 캐싱**: 접힌 섹션의 위젯은 생성하지 않음 (Lazy Loading)
2. **가상 스크롤**: 친구 수가 많을 경우 QListWidget 대신 QListView + Model 사용 고려
3. **아이콘 캐싱**: IconManager에서 이미 구현됨 (LRU Cache)
4. **테마 전환**: 전체 스타일시트 재생성 대신 색상만 교체

### 메모리 관리
- 접힌 섹션의 아이템 위젯은 메모리에서 제거
- 프로필 이미지는 지연 로딩 + 캐싱

---

## UI/UX 가이드라인

### 간격 및 크기
- 섹션 헤더 높이: 40px
- 친구 아이템 높이: 60px (기본), 80px (업데이트한 프로필)
- 생일 아이템 높이: 70px
- 채널 아이템 높이: 65px
- 섹션 간 간격: 0px (접힌 상태), 0px (펼친 상태)

### 색상 (라이트 모드)
- 섹션 헤더 배경: #F9F9F9
- 섹션 헤더 텍스트: #666666
- 아이템 배경: #FFFFFF
- 아이템 hover: #F8F8F8
- 선물하기 버튼: #3A3A3C (배경), #FFFFFF (텍스트)

### 애니메이션
- 섹션 펼치기/접기: 150ms ease-in-out
- 별 아이콘 토글: 100ms
- 테마 전환: 200ms fade

---

## 구현 체크리스트

### SVG 아이콘
- [ ] chevron-down.svg
- [ ] chevron-right.svg
- [ ] star.svg
- [ ] star-outline.svg
- [ ] cake.svg
- [ ] gift.svg
- [ ] verified.svg
- [ ] channel.svg
- [ ] moon.svg
- [ ] sun.svg

### 유틸리티 클래스
- [ ] ThemeManager (`utils/theme_manager.py`)
- [ ] IconManager 확장 (새 아이콘 매핑 추가)

### UI 컴포넌트
- [ ] CollapsibleSectionHeader
- [ ] UpdatedProfileItemWidget
- [ ] BirthdayItemWidget
- [ ] ChannelItemWidget
- [ ] FriendListItemWidget (별 아이콘 추가)

### FriendsTab 확장
- [ ] section_states 데이터 구조
- [ ] favorites 데이터 구조
- [ ] profile_updates 데이터 구조
- [ ] birthdays 데이터 구조
- [ ] channels 데이터 구조
- [ ] toggle_section() 메서드
- [ ] toggle_favorite() 메서드
- [ ] refresh_user_list() 수정 (섹션 순서 반영)

### 테마 지원
- [ ] 모든 위젯 스타일을 ThemeManager 기반으로 변경
- [ ] 테마 토글 버튼 추가 (설정 또는 프로필)
- [ ] theme_changed Signal 연결

### 테스트
- [ ] 섹션 접기/펼치기 동작
- [ ] 즐겨찾기 추가/제거
- [ ] 업데이트한 프로필 표시
- [ ] 생일인 친구 표시
- [ ] 선물하기 버튼 동작
- [ ] 채널 목록 표시
- [ ] 다크 모드 전환
- [ ] 섹션 순서 정확성

---

## 예상 코드 라인 수

| 기능 | 예상 라인 수 |
|------|-------------|
| SVG 아이콘 (10개) | ~500 라인 |
| ThemeManager | ~150 라인 |
| CollapsibleSectionHeader | ~80 라인 |
| UpdatedProfileItemWidget | ~100 라인 |
| BirthdayItemWidget | ~120 라인 |
| ChannelItemWidget | ~100 라인 |
| FriendsTab 확장 | ~400 라인 |
| 테마 적용 (모든 위젯) | ~300 라인 |
| **총계** | **~1,750 라인** |

---

## 향후 확장 가능성

### 단계별 발전
1. **현재**: 로컬 데이터 기반 UI
2. **다음 단계**: 서버 연동
   - 프로필 업데이트 실시간 감지
   - 생일 알림 서버 푸시
   - 채널 구독/취소 API
3. **장기**: 고급 기능
   - 프로필 스토리 (24시간 제한)
   - 생일 선물 실제 연동
   - 채널 메시지 수신
   - 테마 커스터마이징 (사용자 정의 색상)

