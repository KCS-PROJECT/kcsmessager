# Design System Audit — KCS Talk (`client/kakao/theme.py` ↔ 사용처)
스킬: `design:design-system audit` (Image #6 적용 5/8) · 날짜 2026-10-09

### Summary
**Components reviewed:** 24 (탭 헤더·폴더 칩·목록 행·말풍선·카드 7종·대화상자·토글·아이콘 버튼 …) | **Issues found:** 6 | **Score:** 74/100 → 조치 후 81/100

점수 근거: 색 토큰·간격 단계·아이콘 체계는 잘 갖춰져 있다(+). 글자·모서리는 숫자를 직접 써서 단계가 흩어져 있다(−). 일부 화면은 색을 하드코딩했다(−).

### Naming Consistency
| Issue | Components | Recommendation |
|---|---|---|
| 강조색 토큰 이름이 `yellow`, `yellow_dark` (실제 값은 KCS 네이비) | 거의 모든 화면 | 호환 때문에 유지하되 문서에 '주 강조색'으로 명시 (theme.py 주석 있음). 새 별칭 `accent` 도입은 다음 단계 |
| 버튼 objectName 혼재: `cardPrimary` / `cardBtn` / `primary` / `fileBtn` | 카드·대화상자·파일 | 역할 기준 3종으로: primary(채움) · secondary(테두리) · ghost(글자만) |
| 같은 행동 다른 이름: '프로필' / '프로필 보기' | 연락처 카드 ↔ 프로필 창 | ✅ '프로필 보기'로 통일 (03 ux-copy) |

### Token Coverage
| Category | Defined | Hardcoded Values Found |
|---|---|---|
| Colors | LIGHT/DARK 각 약 40개 + 브랜드 오버레이 | `#hex` 188개 — call.py 39(어두운 통화 화면 전용), chat_room 31, wallpaper 30(배경 프리셋 = 데이터라 정상), story 15 … 그중 `#FFFFFF` 39개는 대부분 '색 배경 위 흰 글자' |
| Spacing | `SPACE` 7단계 + `GUTTER` | 레이아웃 여백 숫자 다수(12, 9, 7 …) — 화면별로 점진 이전 |
| Typography | (없었음) → ✅ **`TYPE_SCALE` 8단계 + `theme.fs()`** | `px(N)` 직접 지정 10종 크기, **배율을 무시하는 `font-size: Npx` 9곳** (로그인 8곳은 설정 전 화면이라 허용, 더보기 1곳 ✅ 수정) |
| Radius | (없었음) → ✅ **`RADII` 6단계 + `theme.radius()`** | `border-radius` 리터럴 10종(4,6,8,9,10,11,12,13,14,16) |

### Component Completeness
| Component | States | Variants | Docs | Score |
|---|---|---|---|---|
| 아이콘 버튼 (`IconButton`) | ✅ hover/focus/disabled | ✅ 크기 | ⚠️ 코드 주석만 | 8/10 |
| 폴더 칩 | ✅ checked/hover/focus | ✅ ＋ 칩 | ⚠️ | 8/10 |
| 메시지 카드 (일정·투표·통화·사다리·게시판·연락처·음성) | ✅ 진행/종료·만료 | ✅ 내/상대 | ⚠️ | 7/10 |
| 말풍선 | ✅ 첫 줄 꼬리·연속·삭제·강조 | ✅ 꾸미기 7종 | ✅ 명세 | 9/10 |
| 토글 스위치 | ✅ on/off/focus | — | ⚠️ | 7/10 (✅ 접근성 이름) |
| 음성 재생 버튼 (`PlayButton`, 신규) | ✅ play/pause/pressed/focus/disabled | ✅ 내/상대 | ✅ 05 핸드오프 | 9/10 |
| 대화상자 | ✅ | ⚠️ 제목 스타일이 화면마다 다름 | ⚠️ | 6/10 |

### 이번에 한 조치
1. `theme.TYPE_SCALE` (micro 10 · caption 11 · meta 12 · body 13 · emphasis 14 · title 15 · heading 17 · display 22) + `fs(name)` — 모두 글자 크기 배율 적용.
2. `theme.RADII` (xs 4 · s 6 · m 8 · card 12 · pill 15 · bubble 16) + `radius(name)`.
3. v4에서 새로 만든 화면(음성·요약·공감 선택·녹음 창)은 토큰만 쓰도록 이전.
4. 회귀 방지 테스트: `tests/test_kakao_v4.py::DesignSystemTest` — 단계 정렬, 배율 적용, **로그인 외 `font-size: Npx` 금지**.

### Priority Actions (다음 단계)
1. **기존 화면 글자 크기 이전** — `px(12)` 90곳 → `fs('meta')` 식으로 기계적 치환 (값이 같아 화면 변화 없음).
2. **버튼 변형 3종 통합** — `cardPrimary/cardBtn/primary/fileBtn` QSS를 공통 함수로.
3. **'색 위 흰 글자' 토큰** — `#FFFFFF` 리터럴을 `on_color` 토큰으로 (다크·브랜드 변경 시 한 곳에서 조정).
