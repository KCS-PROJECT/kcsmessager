# impeccable audit → adapt · animate · typeset · polish (+ ui-ux-pro-max, ui-styling)
Image #7 추천 순서(shape → craft → animate → polish → audit → adapt)를 기존 앱에 맞게 **audit → adapt → animate → typeset → polish**로 적용. 날짜 2026-10-09.
플랫폼: 데스크톱 PyQt5 (impeccable `audit.native` 기준을 데스크톱에 맞춰 적용 — 웹 전용 `detect`는 해당 없음).

## Audit Health Score
| # | Dimension | Before | After | Key Finding |
|---|---|---|---|---|
| 1 | Accessibility | 2 | 3 | 메시지 메뉴 마우스 전용·이름 없는 토글 → 키보드 경로·접근성 이름 추가 (스크린리더 실기기 검증은 남음) |
| 2 | Performance | 3 | 3 | 메시지 600개 방 열기 354ms, 새 메시지 15ms. 행을 가상화하지 않음(기록은 50개씩 받아 실사용 영향 작음) |
| 3 | Appearance & Theming | 2 | 3 | 글자·모서리 토큰 없음, 다크 강조 버튼 4.26:1 → 토큰 도입·#536ED4(4.62:1) |
| 4 | Platform Conformance | 2 | 3 | 확인 창 'Yes/No' 영어, 기호 아이콘(▶ ✕ 🔔 🤖) → Qt 한국어 번역·그린 아이콘 |
| 5 | Adaptivity | 2 | 4 | 320px·글자 150%에서 대화 영역이 옆으로 넘침 → 시간 열 실측, 카드 버튼 세로 쌓기, 헤더 아이콘 ☰로 이동 |
| **Total** | | **11/20 (Acceptable)** | **16/20 (Good)** | |

**Platform Conformance Verdict:** 이제 macOS·Windows 데스크톱 앱으로 읽힌다. 남은 차이는 운영체제 '동작 줄이기' 설정을 자동으로 읽지 못하는 점(앱 설정으로 대신)과 macOS 메뉴 막대가 없는 점.

## Findings → Fixes
| Sev | Issue | Fix | Command |
|---|---|---|---|
| P1 | 좁은 창(320px)·큰 글자에서 말풍선·시간이 잘림 | `max_bubble_width`가 '오후 12:59' 실제 폭을 남김 | adapt |
| P1 | 글자 150%에서 연락처 카드 버튼 글자 잘림 | 한 줄에 안 들어가면 세로로 쌓기 | adapt |
| P1 | 좁은 헤더에서 방 이름이 3글자만 보임 | 제목 84px 미만이면 '초대'·'서랍'을 ☰ 메뉴로 | adapt |
| P1 | 음성 파형이 길이 글자와 겹침 | 폭에 맞춰 막대 수 줄이기, 최소 폭 36 | adapt |
| P1 | 다크 주요 버튼 흰 글자 4.26:1 | 다크 강조 #5B74D8 → #536ED4 | polish |
| P2 | 녹음 중인지 한눈에 알기 어려움 | 빨간 점 900ms 숨쉬기 (주 움직임) | animate |
| P2 | 요약 대기 중 빈 창 | 1.2초 진행 막대 (OutCubic) | animate |
| P2 | 움직임을 끌 방법 없음 | 더보기 › 상태·화면 › **동작 줄이기** | animate |
| P2 | 글자 크기 숫자 163곳 | `theme.fs('meta')` 등 이름으로 (값 동일 → 화면 변화 없음) + 회귀 테스트 | typeset |
| P2 | 카드 버튼마다 hover/focus/disabled 규칙 제각각 | `theme.button_qss(selector, variant)` — primary/secondary/outline/ghost/danger 모두 같은 상태 규칙 (ui-styling: shadcn 변형 원칙) | polish |
| P2 | 배지가 숫자만 읽힘 | "채팅, 안 읽은 메시지 4개", 채팅방 행 "이름, 안 읽은 메시지 N개, 미리보기, 시각" (ui-ux-pro-max: Contextual Live Badge Updates) | audit |
| P3 | 이모지·기호 아이콘 (🤖 🔔 ✕) | 'AI' 태그 · 그린 종 아이콘 · 그린 닫기 아이콘 (ui-ux-pro-max: No Emoji as Structural Icons) | polish |

## ui-ux-pro-max 검색 근거
- product: *Chat & Messaging App* → "Brand primary + bubble contrast (sender/receiver)" — 현재 구조와 일치, 변경 없음.
- ux: *Contextual Live Badge Updates* (High) → 배지 접근성 이름 반영.
- pro-rules: *No Emoji as Structural Icons* → 기호 아이콘 교체.
- 'emoji as icons' ux 검색은 0건 → style 도메인으로 다시 검색해 확인(가짜 결과를 만들지 않음).

## ui-styling 적용 범위
shadcn/ui·Tailwind는 React 웹용이라 코드는 쓸 수 없다. 옮겨 온 것은 **변형별 상태 완비 원칙**(default·secondary·outline·ghost·destructive × hover·pressed·focus-visible·disabled)뿐이며 `theme.button_qss`로 구현했다.

## 검증
- `python3 scripts/verify_features.py` → 테스트 470개 통과, 기능 79/79 (새로 '키보드로 쓰기' 포함)
- `python3 scripts/demo.py --headless-check` → 26/26
- 새 회귀 테스트: `AdaptTest`, `MotionTest`, `DesignSystemTest`(글자 단계 이름 사용·버튼 변형), `AccessibilityTest`(배지·아이콘), `OrgContactTest`

## Positive Findings
- 색 토큰·간격 단계·아이콘 세트가 이미 갖춰져 있어 이번 수정이 대부분 토큰 교체로 끝났다.
- 분할 화면(1180px↑)과 별도 창 전환이 깔끔하다.

## 다음 권장
1. `$impeccable harden` — 서버 끊김·재연결 중 보낸 메시지 대기열 표시.
2. `$impeccable optimize` — 1,000개 이상 메시지 방에서 행 재사용(가상화).
3. `$impeccable polish` — 남은 `px(16/18/19/20/26)` 한 번만 쓰는 크기 정리.
