# Handoff Spec: KCS Talk v4 신규 컴포넌트
스킬: `design:design-handoff` (Image #6 적용 6/8) · 스택: Python 3 + PyQt5 (QSS + QPainter), 토큰 = `client/kakao/theme.py`

### Overview
카카오톡 2026 업데이트 반영분의 화면 부품. 모두 채팅방 메시지 열(`MessageRow`) 또는 채팅 탭 목록(`RowList`) 안에 들어간다. 데스크톱 창 폭 320~1320px, 채팅방 말풍선 최대 폭 `max_bubble_width()` (창 폭의 약 73%).

### Layout
- 메시지 열: 좌우 12px, 프로필 40px + 간격 7px. 카드 폭 = `min(카드 최대, max_w)` — 연락처 230, 음성 230, 통화 220.
- 공감 줄: 말풍선 아래 4px 간격, **max_w 안에 들어가는 만큼만(최대 6종)** + `+N`. 넘치면 대화 영역 전체가 넓어져 오른쪽 말풍선이 잘리므로 반드시 지킬 것.
- 요약 칩: 공지 배너 아래 가운데, 위 2 · 아래 4px.

### Design Tokens Used
| Token | Value (light / dark) | Usage |
|---|---|---|
| `c('yellow')` (주 강조) | #2A386C / 밝은 블루 | 받은 음성 재생 버튼, 요약·주요 버튼, 공감 수 배지 |
| `c('on_accent')` | #FFFFFF | 강조색 위 글자·삼각형 |
| `_mine['bg'] / ['fg']` | 말풍선 꾸미기 색 | 내 음성 말풍선 배경 / 재생 버튼 채움 |
| `c('bubble_other')` + `c('border')` | #FFF / #3A3D41 | 받은 카드 배경·테두리 |
| `c('danger_text')` (신규) | #C5221F / #FF8A80 | 부재중 부제 |
| `c('text_hint')` | #6A6A6A / #ABABAB | 카드 캡션('연락처') |
| `fs('meta')` 12 · `fs('emphasis')` 14 · `fs('title')` 15 · `fs('micro')` 10 | 배율 적용 | 음성 길이·부제 / 카드 제목 / 대화상자 제목 / 수 배지 |
| `radius('card')` 12 · `radius('bubble')` 16 · `radius('pill')` 15 | | 카드 / 음성 말풍선 / 요약 칩 |

### Components
| Component | Variant | Props | Notes |
|---|---|---|---|
| `VoiceCard` | 내(`voiceMine`) / 상대(`voice`) | msg(content=초, attachment) | 만료 첨부면 재생 불가 + 툴팁 |
| `PlayButton` | play / pause | fill, glyph | 32×32 원, **QPainter 삼각형·막대**(글자 기호 금지), Tab 포커스 2px 링 |
| `Waveform` | — | bars(22개, msg_id 고정 시드), progress 0~1 | 막대 간격 2px, 남은 막대 = 글자색 α128(≥3:1), 재생 막대 = 강조(라이트)/글자색(다크·내 말풍선) |
| `ContactCard` | 상대/나 | username | 캡션 → 40px 프로필 + 이름/소속 → [1:1 채팅][프로필 보기]; 나 자신이면 '나와의 채팅' |
| `SummaryDialog` | 안 읽은 대화 / 최근 대화 | room_id | 본문 줄간격 150%, 복사 버튼, 모달리스 |
| 요약 칩 `summaryChip` | — | 안 읽은 수 | 열 때 안 읽은 메시지 ≥ `SUMMARY_CHIP_MIN`(20), 비밀채팅 제외. 누르면 사라지고 열 때의 읽음 위치(`since_msg_id`) 이후만 요약 |
| `ReactionPicker` | — | mine, counts | 8열 × 9행 = 72종, 버튼 46×38, 내 공감 2px 테두리, 수 배지 오른쪽 아래 |
| `CallLogRow` | 일반 / 부재중 | call dict | 44px 원 아이콘(모드별), 부재중 = 빨간 원 + `danger_text` 굵은 부제, 제목은 기본색 |

### States and Interactions
| Element | State | Behavior |
|---|---|---|
| PlayButton | 기본 → 클릭 | 첨부 캐시 있으면 즉시 재생, 없으면 `attachment_get` 후 도착 시 재생 |
| PlayButton | 재생 중 | 정지 막대, 접근성 이름 '음성메시지 정지', 다시 누르면 정지 |
| PlayButton | 다른 음성 재생 | 앱 전체 플레이어 1개 — 이전 것 자동 정지 |
| PlayButton | pressed / disabled(만료) | 채움 15% 어둡게 / `bg_alt` + `text_hint` |
| Waveform | 재생 중 | 40ms 마다 진행률 갱신, 끝나면 0으로 |
| 녹음 창 | 녹음 / 정지 / 오류 | '■ 정지' / '● 다시 녹음' + 보내기 활성(≥1초) / '● 다시 녹음' + 원인·할 일 안내 |
| 공감 +N | 클릭 | 공감 선택 창 (툴팁에 접힌 공감 목록) |
| 요약 창 | 결과 도착 전 | '대화를 요약하는 중입니다…' |

### Responsive Behavior
| 창 폭 | Changes |
|---|---|
| ≥ 1180 (분할 화면) | 채팅방이 메인 창 오른쪽 칸에 들어감 — 카드 폭 규칙 동일 |
| 400~1180 | 카드 고정 폭(230), 공감 칩 수가 max_w 에 맞춰 줄어듦 |
| 320 (최소) | max_w ≈ 230 → 카드가 max_w 로 줄고 이름·소속 말줄임 |

### Edge Cases
- **긴 이름/소속**: 카드 폭 − 78px 에서 말줄임(…).
- **공감 30종**: 서버가 31번째 새 종류 거절 → 토스트로 서버 문구.
- **음성 5분 초과**: 녹음기가 300초에서 자동 정지 + '5분이 되어 녹음을 멈췄습니다. 보내기를 누르면 전송됩니다.'.
- **장치 없음(오프스크린·마이크 없음)**: 녹음 오류 안내 / 재생은 시간만 흐르며 진행률 표시.
- **통화 기록 0건**: '통화 기록이 없습니다 / 채팅방에서 보이스톡·페이스톡을 걸면 여기에 모입니다'.
- **요약 0건**: '요약할 대화가 아직 없습니다. 메시지가 쌓인 뒤 다시 요약해 보세요.'

### Animation / Motion
| Element | Trigger | Animation | Duration | Easing |
|---|---|---|---|---|
| Waveform 진행 | 재생 | 막대 색이 왼쪽부터 채워짐 | 재생 길이 (40ms 틱) | linear |
| 메시지 강조 (`flash`) | 검색·답장 원문 이동 | 강조 배경 후 사라짐 | 1600ms | step |
| (다음 단계) 요약 칩 등장 | 방 열기 | 위에서 4px 내려오며 나타남 | 160ms | OutCubic — impeccable animate 단계 |

### Accessibility Notes
- 포커스: 요약 칩·공지 배너 Tab 가능, 재생 버튼 Tab 가능, 메시지는 Alt+↑/↓ + Shift+F10.
- 접근성 이름: 재생 '음성메시지 재생/정지', 공감 +N '공감 N종 더 보기', 말풍선 '보낸 사람: 내용, 시각', 공감 선택 버튼 '공감 🚀 (N명)'.
- 테스트: `tests/test_kakao_v4.py` (V4ChatRoomUiTest · AccessibilityTest · DesignSystemTest).
