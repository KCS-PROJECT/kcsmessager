# Image #7 그대로 적용 기록 (2026-10-09)

Image #7 = 디자인/UI 스킬 17개 표 + 추가 스킬 2개(frontend-design, simplify) + 추천 순서 **shape → impeccable craft → animate → polish → audit → adapt**.

## 1. 추천 순서대로 새 기능 하나 만들기 — '보내지 못한 메시지 (전송 실패 · 재전송 · 삭제)'
| 순서 | 단계 | 한 일 | 검증 |
|---|---|---|---|
| 1 | **shape** | 발견 질문 1회 → 사용자 확정(카카오톡처럼 · 앱을 꺼도 유지) → 브리프 | `09_shape_failed_messages.md` |
| 2 | **craft** | 실패 메시지 상태·보존·재전송·삭제, 빨간 ! 버튼 + '전송 실패', 채팅 목록 표시 | `FailedMessageTest` |
| 3 | **animate** | 막 실패한 순간 고리 1회(360ms), 동작 줄이기면 생략 | 테스트·중간 프레임 |
| 4 | **polish** | 연속 메시지에서 '전송 실패' 숨던 문제 수정 | 재촬영 |
| 5 | **audit** | '전송 실패' 대비 4.49 → 5.06:1, 접근성 이름·포커스 | 대비 테스트 |
| 6 | **adapt** | 320px · 글자 150%에서 안 잘림 | `AdaptTest` |

## 2. 표의 impeccable 명령 16개 — 앱 전체에 적용
| 명령 | 적용 내용 | 근거/테스트 |
|---|---|---|
| shape | 위 1번 | 09 문서 |
| adapt | 좁은 창·큰 글자에서 말풍선·시간·카드 버튼·헤더 아이콘 자동 조정 | `AdaptTest` |
| animate | 녹음 표시 깜빡임, 요약 진행 막대, 전송 실패 고리 + 동작 줄이기 설정 | `MotionTest` |
| audit | 기술 점수 11/20 → 16/20, 전송 실패 기능 감사 | 08 문서 |
| **bolder** | 대화 요약 첫 줄을 제목으로(굵게·크게), 결정/요청이 한눈에 | `SummaryStyleTest` |
| clarify | 새 문구 존댓말 통일(녹음·요약·공감 안내) + 03 ux-copy | 03 문서 |
| **colorize** | 요약 유형 태그 색(결정 남색·요청 주황·일정 청록·질문 보라), 라이트/다크 모두 4.5:1 이상 | `test_tag_colors_meet_aa` |
| critique | v4 화면 비평 | 01 문서 |
| **delight** | 음성메시지를 재생하면 파형이 실제 녹음 모양으로 바뀜 | `real_wave` 테스트 |
| **distill** | 채팅 탭에서 항상 숨겨져 있던 버튼 2개·클래스·아이콘 함수(쓰이지 않는 코드) 제거 | 전체 테스트 |
| layout | 요약 결과 배치(제목 → 키워드 칩 → 유형 줄 → 공유 보조) + 이전 세션 layout | 스크린샷 |
| **optimize** | 설치 안 된 글꼴('맑은 고딕' on macOS)을 체인에서 제외 → **메인 창 첫 화면 290ms → 155ms**, Qt 경고 제거 | `OptimizeTest` |
| **overdrive** | 녹음 창에 실시간 흐르는 파형(최근 막대일수록 진하게, 5분 진행 바탕) | 스크린샷·테스트 |
| polish | 버튼 변형 통합, 다크 강조색 4.62:1, 전송 실패 표시 | 08 문서 |
| **quieter** | 키워드 알림의 이중 강조(진한 테두리+칩)를 칩 위주로, 테두리 1px·반투명. 칩 글자 대비 2.51 → 5.42:1 | `test_keyword_chip_text_contrast` |
| typeset | 글자 크기 177곳을 이름 있는 단계로 + 회귀 테스트 | `DesignSystemTest` |

## 3. 추가 스킬
- **frontend-design**: 01 비평 수정(그린 재생 버튼·파형 대비·요약 칩·카드 문구), 이후 모든 아이콘은 직접 그림.
- **simplify**: 검토 에이전트 4개(재사용·단순화·효율·추상화 수준) → 30건 중 아래 반영.
  - 연결 상태는 연결 객체의 `is_connected` 사용(비공개 필드 탐색 제거), 실패 메시지 메모리 사본·`message_removed` 신호로 **행 하나만 제거**(방 전체 재구성 없음), 재전송 실패 시 설정 이중 저장 제거, 실패 메시지 묶음 규칙을 `_run_key`로(특수 처리 제거)
  - 시간·날짜·길이·소속 포맷을 `state`의 공용 함수로(내보내기·말풍선·통화 창·통화 기록), 통화 모드 표 하나로, `menu_qss()` 공용, 첨부 형식 `attachment_payload`
  - 글꼴 조회 캐시 하나로, 요약 모델 이름 RAG와 공유 + **API 키 인증 실패 시 이후 호출 중단**, 요약 라벨 표 하나로
  - 음성: 레벨 계산은 numpy `rms_level`, 장치 확인은 통화와 같은 `devices_enabled()`, 장치가 열린 뒤에만 녹음 중, 애니메이션 위젯 공통 기반(`_PhaseWidget`), 동그란 버튼 공통 기반(`RoundGlyphButton`), 재생 중인 카드만 플레이어 신호 수신
  - 시간 열 폭 캐시, 요약 중복 요청 무시(같은 사람·같은 방), 채팅 목록 행 값 한 번만 계산
  - **세그폴트 수정**: 실패 고리 애니메이션의 `finished` 람다가 위젯 소멸 중 호출되던 문제
  - 2차 반영: 녹음 입력을 통화 `AudioEngine.start_input()` 재사용, 대화 내보내기를 500개씩 읽어 저장소 잠금을 짧게, 통화 기록 아이콘 캐시, 실패 말풍선이 있을 때 새 메시지를 그 위에 한 행만 끼워 넣기(방 재구성 없음)
  - 3차 반영(남은 것 없음): 재생도 통화 `AudioEngine` 출력(`play_tick` + 음성용 믹서) 사용 → voice.py 의 장치 코드 전부 제거, 실패 메시지를 서버 메시지 저장소와 **분리**(화면에만 맨 아래로 붙임 → 읽음·기록 요청의 id 거르기 제거), 실패 메시지 저장은 첫 변경 즉시 + 0.5초 안의 연속 변경은 한 번에(앱 종료 직전 남은 저장)
- **ui-styling** (참고 문서 4종을 PyQt 앱에 실제로 적용)
  - *shadcn-accessibility 체크리스트*: 대화상자 열면 첫 입력칸 포커스 · 닫으면 연 곳으로 포커스 복귀(`_Dialog`), 토스트 = 라이브 영역(접근성 이름 + Alert 이벤트, API 없는 빌드는 이름만), 폼 오류를 입력칸에 연결(`accessibleDescription` + 포커스 이동, 프로필 편집·친구 추가), 건너뛰기 = **F6 → 입력창**, **200% 글자 확대**(배율 상한 1.5 → 2.0, '최대 (200%)' 선택지, 320/400px 레이아웃 확인), 오류 글자 다크 대비(badge → danger_text)
  - *shadcn-theming*: `theme.py` → **shadcn 형식 CSS 변수**(`assets/design-tokens.css`, `:root`/`.dark` HSL 17개 + `--radius`)와 `assets/design-tokens.json` — 웹 클라이언트를 만들면 shadcn/Tailwind 가 같은 토큰을 바로 쓴다
  - *canvas-design-system*: 색 면 · 기하 리듬 · 최소 글자 원칙으로 **디자인 시스템 보드**(`docs/design/kcs_talk_design_system_{light,dark}.png`) — 실제 토큰과 실제 부품(버튼 5종·연락처·음성·전송 실패·요약 태그)을 캡처해 그린다 (`scripts/make_design_board.py`)
  - *버튼 변형 원칙*: `theme.button_qss` (primary/secondary/outline/ghost/danger × hover/pressed/focus/disabled)
  - *React/shadcn/Tailwind 코드 흐름* (사용자 선택: '디자인 시스템 웹 문서'): `web/` 에 Vite + React + TypeScript 프로젝트 → **`tailwind_config_gen.py`** 로 Tailwind 설정(KCS 색·한글 글꼴·animate 플러그인) → **`shadcn_add.py`** 로 shadcn 2.3.0 컴포넌트 6개(button·card·badge·tabs·separator·switch) → `theme.py`에서 만든 CSS 변수로 색·글자·부품·접근성 4탭 문서. `npm run build` 성공, 브라우저(Playwright)로 데스크톱 1280px·모바일 375px·라이트/다크 확인. 포커스 링은 데스크톱과 같게 2px로 조정
- **ui-ux-pro-max**: 배지 맥락 읽기, 기호 아이콘 금지(08 문서).

## 검증
`python3 scripts/verify_features.py` → 테스트 482개 통과, 기능 80/80 (연속 2회) · `python3 scripts/demo.py --headless-check` → 26/26
