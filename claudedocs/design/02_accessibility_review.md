# Accessibility Audit: KCS Talk 데스크톱 클라이언트 (client/kakao/)
**Standard:** WCAG 2.1 AA | **Date:** 2026-10-09 | 스킬: `design:accessibility-review` (Image #6 적용 2/8)

방법: 오프스크린으로 메인 창 5개 탭 + 채팅방(연락처·음성 카드 포함)을 띄워 위젯 트리를 자동 검사(이름 없는 버튼·클릭 요소, 키보드 포커스 불가 요소, 이름 없는 입력칸) + 토큰 대비 계산. 실제 스크린리더(VoiceOver/NVDA) 테스트는 하지 못했다 — 사람이 한 번 확인해야 한다.

### Summary
**Issues found:** 11 | **Critical:** 1 | **Major:** 6 | **Minor:** 4 — **수정 10 / 남김 1**

### Findings

#### Perceivable
| # | Issue | WCAG | Severity | 조치 |
|---|---|---|---|---|
| 1 | 음성 파형 미재생 막대 2.2~2.6:1 | 1.4.11 | 🟡 Major | ✅ 막대 알파 상향 (03 frontend 단계에서 수정, 3:1 이상) |
| 2 | 다크 모드 카드 안내 글자(`text_hint` on 카드) 3.88:1 | 1.4.3 | 🟡 Major | ✅ 다크 `text_hint` #9A9A9A → #ABABAB (4.6:1) |
| 3 | 부재중 통화 제목(빨강 `badge`) 다크 3.45:1 | 1.4.3 | 🟡 Major | ✅ 새 토큰 `danger_text` (라이트 #C5221F / 다크 #FF8A80), 강조는 부제로 옮김 |
| 4 | 부재중을 색으로만 구분 | 1.4.1 | 🟢 Minor | ✅ 부제에 '부재중' 글자 + 굵게 |

#### Operable
| # | Issue | WCAG | Severity | 조치 |
|---|---|---|---|---|
| 5 | 메시지 말풍선의 메뉴(답장·공감·전달·삭제)를 마우스 우클릭으로만 열 수 있음 | 2.1.1 | 🔴 Critical | ✅ **Alt+↑/↓ 메시지 선택(2px 포커스 테두리) → Shift+F10/메뉴 키로 그 메시지 메뉴, Esc 해제**. 입력 포커스는 그대로 |
| 6 | 공지 배너가 키보드로 열리지 않음 | 2.1.1 | 🟡 Major | ✅ Tab 포커스 + Enter/Space (`Clickable.keyPressEvent`) |
| 7 | 채팅 탭 '폴더 만들기(＋)' 칩이 NoFocus | 2.1.1 | 🟡 Major | ✅ TabFocus |
| 8 | 보낸 사람 프로필이 프로필 사진 클릭으로만 열림 | 2.1.1 | 🟢 Minor | ✅ 메시지 메뉴에 '프로필 보기' |

#### Understandable
| # | Issue | WCAG | Severity | 조치 |
|---|---|---|---|---|
| 9 | 녹음 창: 마이크 오류 뒤에도 버튼이 '■ 정지'로 남음 | 3.3.1 | 🟢 Minor | ✅ 오류 시 '● 다시 녹음'으로 되돌리고 상태 문구에 원인 (04 ux-copy 단계) |

#### Robust
| # | Issue | WCAG | Severity | 조치 |
|---|---|---|---|---|
| 10 | 더보기 토글 4개, 조직도 검색칸, 메시지 입력창, 말풍선·인용·프로필 사진에 접근성 이름 없음 | 4.1.2 | 🟡 Major | ✅ `SettingRow`가 줄 제목을 토글 이름/설명으로, 입력칸·말풍선(“보낸 사람: 내용, 시각”)·인용·링크 카드·프로필 사진 이름 |
| 11 | 말풍선·프로필 사진 17개가 Tab 순서에 없음 | 2.1.1 | 🟢 Minor | ⏸ 의도적으로 남김: 메시지마다 Tab 정지점을 만들면 입력창까지 수백 번 눌러야 한다. 대신 #5의 Alt+↑/↓ 경로 제공 |

### Color Contrast Check (수정 후)
| Element | Foreground | Background | Ratio | Required | Pass? |
|---|---|---|---|---|---|
| 본문 | text | bg | 17.6 / 14.1 | 4.5 | ✅ |
| 카드 안내 (다크) | #ABABAB | #3A3D41 | 4.6 | 4.5 | ✅ |
| 부재중 부제 (라이트/다크) | danger_text | bg | 5.3 / 6.9 | 4.5 | ✅ |
| 음성 길이 | text_sub | 카드 | 5.3 / 4.5 | 4.5 | ✅ |
| 파형 미재생 막대 | 글자색 60% | 말풍선 | ≥3.0 | 3.0 | ✅ |

### Keyboard Navigation
| Element | Tab Order | Enter/Space | Escape | Arrow Keys |
|---|---|---|---|---|
| 사이드바 탭 | 1 | 탭 전환 (Ctrl+1~5) | - | - |
| 채팅 폴더 칩 · ＋ | 헤더 다음 | 폴더 선택/만들기 | - | - |
| 공지 배너 | 채팅방 헤더 다음 | 펼치기/원문 이동 | - | - |
| 메시지 | (Tab 아님) | - | 선택 해제 | Alt+↑/↓ 선택, Shift+F10 메뉴 |
| 입력창 | 마지막 | 전송 | 수정/답장 취소 | - |
| 공감 선택 창 | 72개 버튼 | 공감 | 닫기 | - |

### Screen Reader
| Element | Announced As | Issue |
|---|---|---|
| 말풍선 | "김철수: 다들 내일 회의 시간 괜찮아요?, 오전 11:16" | - |
| 음성 재생 버튼 | "음성메시지 재생" | - |
| 공감 +N | "공감 3종 더 보기" | - |
| 토글 | "다크 모드" + 설명 | - |

### Priority Fixes (모두 반영)
1. **키보드 메시지 메뉴** — 키보드 사용자가 답장·공감·삭제를 전혀 못 하던 문제.
2. **다크 모드 대비 토큰** — 카드 안내·부재중 글자.
3. **접근성 이름** — 토글·입력칸·말풍선.

회귀 테스트: `tests/test_kakao_v4.py::AccessibilityTest`, `tests/test_kakao_layout.py`(대비·이름).
