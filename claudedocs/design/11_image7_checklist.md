# Image #7 대조표 — 표의 모든 줄 · 검토 결과 모든 항목 (2026-10-09)

## A. Image #7 표 (디자인/UI 스킬 17개 + 추가 2개) → 적용 증거
| # | 스킬 (표 설명) | 적용한 것 | 증거 (파일 / 테스트) |
|---|---|---|---|
| 1 | impeccable (craft/teach/extract) | craft: '보내지 못한 메시지' 새 기능을 기존 KCS 시각 체계 안에서 구현 · extract: 글자/모서리/버튼 변형을 토큰으로 추출 | `chat_room.FailButton`, `state` 실패 메시지 · `theme.TYPE_SCALE/RADII/button_qss` · `FailedMessageTest`, `DesignSystemTest` |
| 2 | shape (코딩 전 기획) | 발견 질문 → 사용자 확정 → 브리프 | `09_shape_failed_messages.md` |
| 3 | adapt (반응형) | 320px·150%·200% 에서 말풍선·시간·카드 버튼·헤더 자동 조정 | `max_bubble_width`, `ContactCard.relayout`, `_elide_title` · `AdaptTest` (1.5·2.0 둘 다 항상 실행, subTest) |
| 4 | animate (목적 있는 움직임) | 녹음 점·요약 진행 막대·전송 실패 고리, 동작 줄이기 | `voice.PulseDot/BusyBar`, `FailButton.announce` · `MotionTest` |
| 5 | audit (접근성·성능·테마 점수) | 11/20 → 16/20, 실패 기능 감사 | `08_impeccable_audit_and_fixes.md` |
| 6 | bolder | 요약 첫 줄 제목화 | `summary_html` · `SummaryStyleTest` |
| 7 | clarify (UX 문구) | 오류에 '할 일', 존댓말 통일, 확인 창 한국어 | `03_ux_copy.md` · `UxCopyTest` |
| 8 | colorize | 요약 유형 태그 4색 (4.5:1↑) | `SUMMARY_TAGS` · `test_tag_colors_meet_aa` |
| 9 | critique | v4 화면 비평 | `01_design_critique_v4.md` |
| 10 | delight | 재생하면 실제 녹음 모양 파형 | `VoiceCard.play` · `real_wave` 검사 |
| 11 | distill | 숨겨진 버튼 2개·클래스·아이콘 함수 제거 | `chats_tab.py` (OpenChatButton 제거) |
| 12 | layout | 요약 결과 배치 · 이전 세션 layout | `summary_html` · 스크린샷 |
| 13 | optimize | 없는 글꼴 제외 → 첫 화면 **282→159ms** (중앙값, 5회씩) | `theme.font_families/installed` · `OptimizeTest` · 재현: `python3 scripts/measure_startup.py [--legacy]` |
| 14 | overdrive | 녹음 창 실시간 파형 | `voice.LiveWave` · 녹음 테스트 |
| 15 | polish | 버튼 변형 통합·다크 강조 4.62:1·실패 표시 | `theme.button_qss` · `test_button_variants_cover_all_states` |
| 16 | quieter | 키워드 이중 강조 완화, 칩 대비 2.51→5.42 | `keyword_text_color` · `test_keyword_chip_text_contrast` |
| 17 | typeset | 스타일시트·`theme.font()`·`ElidedLabel` 의 글자 크기 전부 이름 단계로(단계 11개: headline 19·numeral 26 추가, 흩어진 8/9/10.5/11.5/12.5/13.5/18/20/24 를 가까운 단계로) | `theme.fs`, `theme.size_of` · `test_type_scale_steps_used_by_name`(세 형태 모두 숫자 금지, 이모티콘 그림 46px만 예외) |
| + | frontend-design | 그린 아이콘·파형 대비·요약 칩·카드 문구 | `RoundGlyphButton`, `Waveform` |
| + | simplify | 검토 4종 30건 → 아래 B | 아래 표 |
| 순서 | shape → craft → animate → polish → audit → adapt | 한 기능에 그 순서대로 | `10_image7_workflow_run.md` §1 |
| 요청 | ui-ux-pro-max | 배지 맥락 읽기, 기호 아이콘 금지 | `AccessibilityTest.test_badges_read_with_context_and_no_glyph_icons` |
| 요청 | ui-styling | 접근성 체크리스트 · shadcn 테마 변수 · Canvas 보드 · **`tailwind_config_gen.py` + `shadcn_add.py`로 `web/` 디자인 시스템 문서** | `UiStylingPatternsTest`, `DesignTokenExportTest`, `web/` (`npm run build` 성공) |

## B. simplify 검토 결과 30건 → 처리 상태 (전부 처리)
| 관점 | 항목 | 상태 |
|---|---|---|
| 재사용 1 | 녹음·재생이 통화 오디오 코드를 복사 | ✅ `AudioEngine.start_input` / `play_tick` 재사용, voice.py 장치 코드 제거 |
| 재사용 2 | pcm_level 이 rms_level 복사 | ✅ `rms_level` 사용 |
| 재사용 3 | fmt_duration ↔ format_duration (시간 단위 누락) | ✅ 하나로 (h:mm:ss 포함) |
| 재사용 4 | 내보내기 시간·날짜 포맷 복사 | ✅ `state.fmt_ampm/fmt_day` 공용 |
| 재사용 5 | 소속 문자열 7곳 | ✅ `AppState.org_text(username, sep)` — chat_room(연락처 카드·선택·대화상대 목록·헤더), friends_tab(친구 추가 카드), more_tab(내 프로필) 모두 |
| 재사용 6 | font_families ↔ installed 중복 | ✅ `_available_families` 하나 |
| 재사용 7 | 요약 모델 이름·인증 실패 처리 복사 | ✅ `rag.DEFAULT_MODEL`, `rag.FATAL_LLM_ERRORS`(RAG 답변·요약 공용), `on_fatal` |
| 재사용 8 | 통화 모드 이름표 5벌 | ✅ `state.CALL_MODE_LABELS` 하나 — chat_room `CALL_MODES`(별칭)·`CALL_LABELS` 제거, call `MODE_LABELS`(가져옴), feature_tour, chats_tab |
| 단순화 1 | PulseDot/BusyBar 같은 타이머 | ✅ `_PhaseWidget` |
| 단순화 2 | PlayButton/FailButton 같은 그리기 | ✅ `RoundGlyphButton` |
| 단순화 3 | 실패 저장소 중복 가드·redraw 핵 | ✅ 메모리 사본 + `message_removed` |
| 단순화 4 | is_connected 비공개 필드 | ✅ `conn.is_connected` |
| 단순화 5 | _on_error 가 _stopped 복사, LevelMeter 군더더기 | ✅ 합침·삭제 |
| 단순화 6 | 요약 라벨 표 2벌·링크 2번 셈 | ✅ `KIND_LABELS`, 1번 |
| 단순화 7 | _elide_title 중복 계산 | ✅ `is_secret`, `title_room` 하나 |
| 단순화 8 | VoiceCard/SummaryDialog 잔가지 | ✅ `real_wave`·`_plain` 초기화, `_summary_dlg()` 등 |
| 효율 1 | 실패 말풍선 하나 지우려 방 전체 재구성 | ✅ 행 하나만 제거 (예외: 그날 유일한 메시지면 날짜 구분선 정리를 위해 다시 만듦) |
| 효율 2 | 실패마다 설정 전체 저장 + 채팅 목록 전체 재구성 | ✅ 저장 0.5초 모으기 · **채팅 목록은 그 방 행만 교체**(`ChatsTab._on_room_changed`; 예외: 검색 중·'통화' 폴더에서는 전체 다시 그림) |
| 효율 3 | room_has_failed 행마다 목록 복사·순회 | ✅ 방별 개수 사전(O(1)) |
| 효율 4 | pcm_level 전체 언팩 | ✅ numpy |
| 효율 5 | 모든 음성 카드가 초당 25회 신호 수신 | ✅ 재생 중 카드만 |
| 효율 6 | max_bubble_width 매번 글꼴 측정 | ✅ 배율별 캐시 |
| 효율 7 | 요약마다 스레드·Python 필터 | ✅ 진행 중 중복 무시 · **LLM 없으면 스레드 없이 즉시** · **'이후만'은 SQL** (`history(after_msg_id)`) |
| 효율 8 | 내보내기 2만 개를 잠금 쥔 채 한 덩어리 | ✅ 500개씩 읽기 · **2000개씩 조각 응답**(`part`/`done`, 클라이언트가 모음) |
| 효율 소 | 통화 기록 아이콘 매번 그림 | ✅ `call_icon` 캐시 |
| 추상화 1 | is_connected | ✅ (단순화 4) |
| 추상화 2 | history_loaded 를 다시 그리기용으로 | ✅ `message_removed` |
| 추상화 3 | 실패 메시지가 서버 id 공간에 섞임 | ✅ 별도 저장소, 화면에서만 맨 아래 |
| 추상화 4 | set_run 특수 처리 | ✅ `_run_key` 에서 실패는 독립 묶음 |
| 추상화 5 | compact header 가 _elide_title 에 묻힘 | ✅ 계산 하나로 정리(우선순위 목록 일반화는 버튼 2개뿐이라 보류할 이유 없음 → 현재 구조 유지) |
| 추상화 6 | 글꼴 캐시 2개 | ✅ (재사용 6) |

## C. 검증
- `python3 scripts/verify_features.py` — 전체 테스트 · 기능 표 (결과는 FEATURE_VERIFICATION.md)
- `python3 scripts/demo.py --headless-check` — 실제 서버 26항목
- `cd web && npm run build` — 디자인 시스템 웹 문서 빌드, Playwright 1280/375px · 라이트/다크 확인
