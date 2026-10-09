# KCS Messenger – 카카오톡 기능 분석 & 구현 명세 (v2)

작성일: 2026-10-08 · 브랜치: `feature/kakao-full-features`

이 문서는 (1) 카카오톡 PC 버전의 기능 분석, (2) 이번 버전에서 구현할 범위,
(3) 서버-클라이언트 **프로토콜 계약**, (4) 클라이언트 모듈 구조를 정의한다.
서버·클라이언트·테스트는 모두 이 문서를 기준으로 구현한다.

---

## 1. 카카오톡 기능 분석

| 영역 | 카카오톡 기능 | 이번 버전 | 비고 |
|------|--------------|-----------|------|
| 친구 | 친구 목록, 내 프로필, 상태메시지, 즐겨찾기, 생일인 친구, 온라인 상태 | ✅ | 즐겨찾기는 클라이언트 로컬 |
| 친구 | 프로필 편집(이름·상태메시지) | ✅ | `profile_update` |
| 채팅방 | 1:1 채팅, 그룹 채팅, 나와의 채팅 | ✅ | `direct` / `group` / `self` |
| 채팅방 | 채팅방 목록(마지막 메시지, 시간, 안 읽은 수 배지) | ✅ | |
| 채팅방 | 채팅방 이름 변경, 친구 초대, 나가기 | ✅ | 시스템 메시지 생성 |
| 채팅방 | 채팅방 상단 고정, 알림 끄기 | ✅ | 클라이언트 로컬 |
| 메시지 | 텍스트, 이모티콘, 사진, 파일 | ✅ | 첨부 2MB 제한 |
| 메시지 | 읽음 표시(안 읽은 사람 수 노란 숫자) | ✅ | read pointer 기반 |
| 메시지 | 답장(인용) | ✅ | `reply_to` |
| 메시지 | 공감(반응 이모지) | ✅ | 토글 |
| 메시지 | 모든 대화 상대에게서 삭제(24시간 이내), 나에게서 삭제 | ✅ | 나에게서 삭제=로컬 |
| 메시지 | 복사, 전달, 나에게 보내기 | ✅ | 클라이언트에서 send 재사용 |
| 메시지 | 멘션(@이름) | ✅ | `mentions` |
| 메시지 | 예약 메시지 | ✅ | `send_at` |
| 메시지 | 날짜 구분선, 연속 메시지 프로필 생략 | ✅ | UI |
| 채팅방 기능 | 공지 등록/해제(상단 배너) | ✅ | |
| 채팅방 기능 | 투표(단일/복수 선택, 마감) | ✅ | |
| 채팅방 기능 | 대화 검색 | ✅ | |
| 채팅방 기능 | 채팅방 서랍(사진·파일·링크 모아보기) | ✅ | |
| 일정 | 톡캘린더 월간 보기, 일정 생성/수정/삭제 | ✅ | |
| 일정 | 채팅방 일정 공유(일정 카드 메시지) + 참석/불참/미정 응답 | ✅ | |
| 일정 | 일정 알림(N분 전) | ✅ | 서버 스케줄러 → 트레이 알림 |
| 일정 | 할 일(To-do) | ✅ | 개인 |
| 일정 | 생일·기념일 표시 | ✅ | 생일만 |
| 설정 | 다크 모드, 글자 크기 | ✅ | 클라이언트 로컬 |
| 알림 | 새 메시지 데스크톱 알림, 안 읽은 수 합계 | ✅ | `QSystemTrayIcon` |
| 제외 | 보이스톡/페이스톡, 송금(페이), 오픈채팅 검색, 선물하기 결제, E2E 비밀채팅 | ❌ | 외부 인프라·결제 필요 |

## 2. 전송 계층

- TCP, 기본 `127.0.0.1:5555`.
- **줄 단위 JSON(NDJSON)**, UTF-8. 메시지 1개 = JSON 객체 1개 + `\n`.
- 서버는 줄바꿈 없이 이어 붙은 JSON(구버전 클라이언트)도 `json.JSONDecoder.raw_decode`로 파싱한다.
- 모든 요청은 `"type"`을 가진다. 선택 필드 `"req_id"`를 보내면 응답에 그대로 돌려준다.
- 오류: `{"type":"error","req_type":"<요청 type>","message":"<한국어 설명>","req_id":...}`

## 3. 데이터 모델 (JSON)

```text
User    {username, display_name, status_message, birthday:"MM-DD"|null, online:bool}

Room    {room_id:str, type:"direct"|"group"|"self", name:str,        # direct/self의 name은 ""(클라이언트가 표시명 계산)
         members:[username], created_at:ISO,
         notice:Message|null, last_message:Message|null,
         read_pointers:{username: last_read_msg_id:int}}             # 0 = 아무것도 안 읽음

Message {msg_id:int(전역 증가), room_id, sender:username|"" (system),
         kind:"text"|"emoticon"|"image"|"file"|"system"|"event"|"poll",
         content:str, timestamp:ISO,
         reply_to:{msg_id, sender, preview}|null,
         mentions:[username], reactions:{emoji:[username]},
         deleted:bool,
         attachment:{attachment_id, name, mime, size}|null,         # image/file
         event_id:int|null,                                          # kind=event
         poll:Poll|null}                                             # kind=poll

Poll    {poll_id:int, question, multiple:bool, closed:bool,
         options:[{text, voters:[username]}]}

Event   {event_id:int, room_id:str|null, creator, title, description, location,
         start:ISO, end:ISO, all_day:bool, remind_minutes:int|null, color:"#RRGGBB",
         attendees:{username:"yes"|"no"|"maybe"|"pending"}, created_at:ISO}

Todo    {todo_id:int, owner, title, due:"YYYY-MM-DD"|null, done:bool, created_at:ISO}
```

**안 읽은 수 계산 규칙(클라이언트)**: 메시지 `m`의 unread =
`room.members` 중 `read_pointers.get(u, 0) < m.msg_id` 인 사람 수. (`system` 메시지는 표시 안 함)
발신자는 전송 즉시 자신의 read pointer가 해당 msg_id로 올라간다(서버 처리).
방의 내 안 읽은 메시지 수 = `sender != me` 이고 `msg_id > read_pointers[me]` 이며 `kind != system` 인 메시지 수.
서버는 정확한 값을 위해 Room에 `unread_count`(요청자 기준)도 포함한다.

## 4. 요청 / 응답 / 푸시

| 요청 (client→server) | 필드 | 서버 동작 / 응답 |
|---|---|---|
| `join` | username | 사용자 등록(없으면 생성). 응답 `welcome {me:User, users:[User], rooms:[Room]}`. 이어서 구버전 호환 `all_users_list {users:[username], online_users:[username]}`. 다른 사람에게 `user_status_changed {username,status:"online"}` |
| `message` (구버전) | content | 모두에게 `message {sender, content, timestamp}` 브로드캐스트(구버전 호환, DB 미저장) |
| `room_open_direct` | target | 1:1 방 생성/조회 → 양쪽에 `room_updated {room}`. target==me면 `self` 방 |
| `room_create` | name, members:[username] | 그룹 방 생성(요청자 자동 포함) → 멤버에게 `room_updated`, 시스템 메시지 "A님이 B, C님을 초대했습니다." |
| `room_invite` | room_id, usernames | 멤버 추가(direct면 오류) → `room_updated` + 시스템 메시지 |
| `room_leave` | room_id | 멤버 제거 → 나간 사람에게 `room_removed {room_id}`, 남은 사람에게 `room_updated` + "A님이 나갔습니다." |
| `room_rename` | room_id, name | → `room_updated` |
| `history` | room_id, before_msg_id?:int, limit?:int=50 | `history {room_id, messages:[Message](오래된→최신), has_more}` |
| `send` | room_id, kind("text"/"emoticon"/"image"/"file"), content, reply_to_id?, mentions?, attachment?{name,mime,data_b64}, send_at?:ISO, client_tmp_id? | 즉시 전송이면 멤버 모두에게 `msg_new {message, client_tmp_id}` + `read_update`(발신자). `send_at`이 미래면 저장 후 요청자에게 `scheduled_ok {scheduled_id, room_id, send_at, content}`; 시각이 되면 `msg_new` |
| `read` | room_id, last_msg_id | read pointer 갱신(감소 불가) → 멤버에게 `read_update {room_id, username, last_read_msg_id}` |
| `react` | msg_id, emoji | 토글 → 멤버에게 `msg_updated {message}` |
| `delete` | msg_id | 발신자 본인 + 24시간 이내만. deleted=true, content="삭제된 메시지입니다.", attachment/poll 유지하지 않음 → `msg_updated` |
| `notice_set` | room_id, msg_id:int\|null | → `room_updated` + 시스템 메시지 "A님이 공지를 등록했습니다." (해제는 메시지 없음) |
| `search` | query, room_id? | 내가 속한 방에서 삭제 안 된 text 메시지 content LIKE 검색, 최신순 최대 100 → `search_result {query, room_id, messages}` |
| `poll_create` | room_id, question, options:[str](2개 이상), multiple:bool | kind=poll 메시지 생성 → `msg_new` |
| `poll_vote` | poll_id, option_indexes:[int] | 내 표를 교체(빈 배열=취소). 마감이면 오류 → `msg_updated` |
| `poll_close` | poll_id | 생성자만 → `msg_updated` |
| `event_create` | title, start, end, all_day?, description?, location?, remind_minutes?, color?, room_id?, attendees?:[username] | room_id가 있으면 참석자=방 멤버(생성자 "yes", 나머지 "pending")이고 kind=event 메시지(content=title, event_id) 게시. 관련자 전원에게 `event_updated {event}` |
| `event_update` | event_id, + 변경 필드 | 생성자만 → `event_updated`. start/remind 변경 시 알림 재무장 |
| `event_delete` | event_id | 생성자만 → 관련자에게 `event_deleted {event_id}` |
| `event_rsvp` | event_id, response("yes"/"no"/"maybe") | 참석자만 → `event_updated` |
| `event_list` | start, end (ISO) | 내가 생성자/참석자인 일정 중 기간 겹치는 것 → `event_list {start, end, events}` |
| `todo_create` | title, due? | → 요청자에게 `todo_updated {todo}` |
| `todo_update` | todo_id, title?, due?, done? | 소유자만 → `todo_updated` |
| `todo_delete` | todo_id | → `todo_deleted {todo_id}` |
| `todo_list` | – | → `todo_list {todos}` |
| `profile_update` | display_name?, status_message?, birthday? | → 모두에게 `user_updated {user}` |
| `attachment_get` | attachment_id | → `attachment_data {attachment_id, name, mime, data_b64}` |
| `leave` | – | 연결 종료 처리 |

**서버 푸시(요청 없이)**
- `user_status_changed {username, status:"online"|"offline", timestamp}`
- `event_reminder {event, minutes_before}` — `start - remind_minutes` 시각에 응답이 "no"가 아닌 참석자(+생성자) 중 접속자에게 1회. 15초 주기 검사.
- 신규 사용자가 처음 join하면 다른 접속자에게 `user_updated {user}`.

## 5. 서버 구조

```
server/kakao/__init__.py
server/kakao/store.py     # SQLite(sqlite3) 영속 계층. Store(db_path). 스레드 안전(Lock).
server/kakao/server.py    # KakaoServer(host, port, db_path) – start()/serve_in_thread()/stop()
server/chat/chat_server.py  # 기존 진입점 → KakaoServer 실행 (CLI: --host --port --db)
```
- 기본 DB 경로: `<프로젝트>/server_data/kakao.db`
- 기본 사용자: 홍길동, 김철수, 이영희, 박민수, 최지우 (생일 샘플 포함)
- 첨부 최대 2MB(base64 디코딩 기준), 초과 시 error

## 6. 클라이언트 구조 (`client/kakao/`)

```
client/kakao/app.py           # 진입점: python client/kakao/app.py [--host --port --user]
client/kakao/net.py           # ChatConnection(QObject): 소켓 + 수신 스레드
client/kakao/state.py         # AppState(QObject): 모든 데이터 + 액션 + 시그널
client/kakao/settings.py      # 로컬 설정(즐겨찾기, 고정, 알림끔, 다크모드, 글자크기) JSON 저장
client/kakao/theme.py         # 색상 팔레트(라이트/다크), 폰트 체인, QSS 헬퍼
client/kakao/widgets.py       # Avatar, Badge, IconButton 등 공용 위젯(QPainter 그래픽)
client/kakao/login.py         # LoginDialog
client/kakao/main_window.py   # MainWindow: 사이드바 + 친구/채팅/캘린더/더보기 탭, 트레이 알림
client/kakao/friends_tab.py   # FriendsTab
client/kakao/chats_tab.py     # ChatsTab (+ 그룹 채팅 만들기 다이얼로그)
client/kakao/chat_room.py     # ChatRoomWindow: 말풍선, 읽음수, 답장, 공감, 삭제, 공지, 투표, 검색, 서랍, 이모티콘, 파일, 예약
client/kakao/calendar_tab.py  # CalendarTab: 월간 달력 + 일정 목록 + 할 일
client/kakao/event_dialog.py  # EventDialog: 일정 생성/수정
client/kakao/more_tab.py      # MoreTab: 프로필 편집, 다크모드, 글자 크기
```

---

## 7. 확장 명세 v2.1 (추가 요구사항)

### 7.1 첨부 파일 송수신
- 최대 크기 **10MB**(디코딩 기준)로 상향. 이미지/파일 모두 상대방이 `attachment_get`으로 받아 저장 가능.
- 클라이언트: 드래그&드롭, 클립보드 이미지 붙여넣기, 여러 파일 동시 선택 지원.

### 7.2 User 필드 추가
```text
User += {avatar_id:int|null,            # 프로필 사진(attachment_id), 없으면 null
         presence:"online"|"away"|"busy"|"meeting"|"offline",  # 미접속이면 항상 "offline"
         company:str, department:str, title:str,               # 그룹사/부서/직함
         is_bot:bool}
```
- `online`(접속 여부)은 그대로 유지. 접속 시 presence는 마지막으로 설정한 값(기본 "online")으로 복원.
- 요청 `presence_set {presence}` ("online"/"away"/"busy"/"meeting") → 모두에게 `user_updated {user}`.
  접속/해제 시에도 `user_status_changed`와 함께 `user_updated`를 보낸다.
- `profile_update`에 `avatar_b64`(이미지, 디코딩 기준 ≤ 512KB) 또는 `avatar_clear:true` 추가 → 첨부로 저장, `avatar_id` 갱신 → `user_updated`.
  프로필 사진은 누구나 `attachment_get`으로 받을 수 있다(방 멤버 여부와 무관).

### 7.3 그룹사(계열사) 조직도 & 교차 대화
- 시드 사용자(회사/부서/직함):

| 사용자 | company | department | title |
|---|---|---|---|
| 홍길동 | KCS 홀딩스 | 경영지원팀 | 팀장 |
| 김철수 | KCS 홀딩스 | 경영지원팀 | 대리 |
| 윤서준 | KCS 홀딩스 | 재무팀 | 차장 |
| 이영희 | KCS 물류 | 운영팀 | 과장 |
| 박민수 | KCS 물류 | 운영팀 | 사원 |
| 강민지 | KCS 물류 | 고객지원팀 | 대리 |
| 최지우 | KCS 커머스 | 마케팅팀 | 팀장 |
| 정하늘 | KCS 커머스 | 개발팀 | 선임 |
| AI 비서 | KCS AI | 지식봇 | 봇 (is_bot=true, 항상 online) |

- `<db 디렉터리>/org.json`(선택)이 있으면 `[{username, company, department, title, birthday}]`로 시드를 덮어쓴다.
- 처음 join하는 미등록 사용자는 company "게스트", department "", title "".
- 회사가 달라도 자유롭게 1:1/그룹 대화 가능. 클라이언트는 다른 회사 사용자에게 회사명 칩을 표시하고, 조직도 탭(회사 → 부서 → 구성원)을 제공한다.

### 7.4 상태(Presence) 표시 색
online `#3DD16B` · away `#F5B400`(자리비움) · busy `#FF4B3E`(다른 용무 중) · meeting `#8E6CEF`(회의 중) · offline `#BDBDBD`
클라이언트는 10분간 입력이 없으면 자동으로 away, 입력이 생기면 원래 상태로 복원한다(사용자가 직접 설정한 away/busy/meeting은 건드리지 않음).

### 7.5 배경화면(클라이언트 로컬)
- 설정 `chat_wallpaper`: `null`(테마 기본) | `{"type":"color","value":"#RRGGBB"}` | `{"type":"gradient","value":["#..","#.."]}` | `{"type":"image","value":"<절대경로>"}`
- 설정 `room_wallpapers`: `{room_id: 위 형식}` — 방별 덮어쓰기.
- `client/kakao/wallpaper.py`: `resolve_wallpaper(settings, room_id)`, `paint_wallpaper(painter, rect, spec)`, `WallpaperDialog(settings, room_id=None, parent=None)`.

### 7.6 RAG(AI 비서)
- 봇 사용자 `AI 비서`. 다음 경우 서버가 답변 메시지(sender="AI 비서", kind="text")를 같은 방에 게시한다:
  (a) 봇이 포함된 1:1 방의 모든 text 메시지, (b) 봇이 멤버인 그룹 방에서 봇을 멘션(`@AI 비서`)한 메시지.
  답변 생성은 별도 스레드에서 하며, 생성 중에는 아무것도 보내지 않는다.
- 봇 1:1 방으로 보낸 텍스트형 파일(txt, md, csv, json, log, py, pdf)은 자동으로 지식베이스에 추가되고 봇이 "문서를 학습했습니다" 답변.
- 검색 범위: 질문자가 멤버인 방의 메시지 + 질문자가 올린 문서 + 공유 문서(owner="")
- 요청: `rag_doc_list` → `rag_doc_list {docs:[{doc_id,name,owner,size,chunks,created_at}]}` / `rag_doc_add {name, data_b64}` → `rag_doc_added {doc}` / `rag_doc_delete {doc_id}`(소유자만) → `rag_doc_deleted {doc_id}`
- 구현: `server/kakao/rag.py` `RagService(db_path)` — SQLite FTS5(trigram) 검색 + 생성기:
  `ANTHROPIC_API_KEY`와 `anthropic` 패키지가 있으면 Claude로 답변 생성, 없으면 검색 결과 기반 요약(추출형) 답변.

### 7.7 조직도 v2 (2026-10-08)
- `server_data/org.json` v2: `{"version":2, "holding":{name,business,homepage,phone}, "companies":[{name,business,homepage,phone,units:[[경로]...]}], "include_demo_users":false, "users":[...]}` — `scripts/import_org_xlsx.py`가 회사 엑셀에서 생성.
- User 추가 필드: `org_path:[str]`(예: ["기술연구소","연구1실","2팀(SI)"]), `account`, `extension`, `mobile`, `concurrent:[{org_path,title}]`.
- `welcome`에 `org: {holding, companies}` 포함(없으면 `{holding:null, companies:[]}`).
- `include_demo_users:false`면 기본 데모 사용자는 시드하지 않고 기존 DB의 데모 사용자는 company='게스트'로 내린다(AI 비서는 유지).

### 7.8 2025~2026 카카오톡 개편 반영 (deep-research 검증 결과 기반)
| 기능 | 프로토콜 / 동작 |
|---|---|
| 메시지 수정 | 요청 `edit {msg_id, content}` — 본인·kind=text·삭제 안 됨·**24시간 이내**만. Message에 `edited:bool`, `edited_at:ISO|null`. 성공 시 멤버에게 `msg_updated`. 수정된 내용으로 검색/RAG 색인 갱신 |
| 삭제 문구 | 삭제된 메시지 content = **"메시지가 삭제되었습니다"** (누가 지웠는지 표시하지 않음) |
| 조용히 보내기 | `send`에 `silent:true` → Message `silent:true`. 받는 클라이언트는 소리/트레이 알림을 띄우지 않지만 안 읽은 수에는 반영 |
| URL 미리보기 | text 메시지에 http(s) URL이 있으면 서버가 비동기로 첫 URL의 og:title/og:description/og:site_name(없으면 <title>)을 가져와 Message `link_preview:{url,title,description,site}`를 채우고 `msg_updated`. 3초 타임아웃, 256KB까지만 읽음. 서버 옵션 `link_preview=True`(환경변수 `KCS_LINK_PREVIEW=off`로 끔) |
| 오늘의 브리핑(선톡) | 서버 옵션 `daily_briefing`(기본 False, 실행 파일은 True). 사용자가 그날 처음 접속하면 AI 비서 1:1 방에 오늘 일정·응답 필요한 일정·마감 할 일·안 읽은 메시지 수 요약을 봇이 먼저 보냄(하루 1회, users.last_briefing) |
| 채팅방 폴더 | 클라이언트 로컬 설정 `chat_folders:[{name, room_ids}]`. 기본 폴더: 전체 / 안읽음 / 즐겨찾기(고정된 방 + 즐겨찾기 친구와의 1:1). 안읽음 폴더에서 **읽지 않고 미리보기** |
| 일정 변경 알림 | 클라이언트: 이미 알고 있는 일정이 다른 사람에 의해 바뀌면(제목/시간/장소) 트레이 알림 "일정이 변경되었습니다" |
| 채팅방 사이드 일정 | 채팅방 서랍에 '일정' 탭 (그 방에서 만든 일정) |
| AI 챗봇 | 채팅방 메뉴 "AI 비서 부르기"(초대), 채팅탭 상단 AI 버튼(봇 1:1 열기) |

## 8. v3 – 조사된 카카오톡 기능 전부 반영 (2026-10-08)

공통: 아래 요청/응답은 §2의 NDJSON 규칙을 따른다. 오류는 `error`.

### 8.1 비밀채팅 (종단간 암호화)
- 각 클라이언트는 X25519 키쌍을 `~/.kcs_messenger/keys/<username>.key`(KCS_MESSENGER_HOME 우선)에 보관. 접속 후 `key_publish {public_key_b64}` → User에 `public_key:str|null` 추가, 모두에게 `user_updated`.
- 방 종류 `secret` (1:1 전용): `room_open_secret {target}` → 기존 secret 방이 있으면 그 방, 없으면 생성 → `room_updated`. 상대 public_key가 없으면 오류 "상대방이 아직 비밀채팅을 사용할 수 없습니다".
- 메시지: `send {room_id, kind:'secret', content:<base64(nonce12 + AESGCM ciphertext)>}`. 키 = HKDF-SHA256(X25519(my_priv, peer_pub), salt=room_id, info=b'kcs-secret-v1', 32B). 평문은 UTF-8 JSON `{"text": "..."}`.
- 서버는 secret 메시지 내용을 해석하지 않음: 검색·RAG·URL 미리보기·답장 미리보기 제외, 알림 미리보기 "비밀채팅 메시지". secret 방에서는 file/image/poll/event 불가(오류).

### 8.2 통화 – 보이스톡 · 페이스톡(그룹 최대 10명) · 보이스룸 · 화면 공유
- Call = `{call_id:int, room_id, mode:'voice'|'video'|'voiceroom', host, started_at, participants:{username:{role:'host'|'speaker'|'listener', muted:bool, video:bool, screen:bool, hand:bool}}}`
- `call_start {room_id, mode}` → 방에 진행 중 통화가 있으면 오류. kind=`call` 메시지 게시(content=모드 이름, `call_id`) 후 멤버에게 `call_updated {call}`. voice/video: 시작자 role=host, voiceroom: host.
- `call_join {call_id}` → voice/video는 role=speaker(video 최대 10명, 초과 시 오류 "최대 10명까지 참여할 수 있습니다"), voiceroom은 listener(최대 1500명). → 멤버에게 `call_updated`.
- `call_leave {call_id}` → 참여자가 0명이거나, voiceroom에서 host가 모두 나가면 종료.
- `call_hand {call_id, raised:bool}` (voiceroom listener) · `call_role {call_id, username, role:'speaker'|'listener'|'host'}` (host만, speaker+host ≤ 10) · `call_state {call_id, muted?, video?, screen?}` → 각각 `call_updated`.
- 종료: `call_ended {call_id, room_id, duration_seconds}` + 시스템 메시지 "통화 종료 · M:SS" (보이스룸은 "보이스룸이 종료되었습니다"). 보이스룸은 생성 48시간 후 자동 종료(스케줄러).
- 미디어 중계: `call_media {call_id, kind:'audio'|'video'|'screen', seq:int, data_b64}` → 서버가 보낸 사람을 뺀 참여자에게 `call_media {call_id, from, kind, seq, data_b64}` 그대로 전달(저장 안 함). 보이스룸에서 audio는 host/speaker만, listener 것은 버림. 형식: audio = 16kHz mono s16le PCM 40ms 프레임(zlib 압축 가능, `kind:'audio'`에 `codec:'pcm'|'zpcm'` 필드), video/screen = JPEG.
- `call_list {room_id?}` → `call_list {calls}` (내가 속한 방의 진행 중 통화). welcome에도 `calls` 포함.

### 8.3 펑 (24시간 스토리)
- `story_post {kind:'text'|'image', content, attachment?{name,mime,data_b64}, bg_color?}` → Story `{story_id, owner, kind, content, attachment_id?, bg_color, created_at, expires_at, viewers:[username] (owner에게만 채움, 그 외 [])}`. 모든 접속자에게 `story_new {story}`.
- `story_list` → `story_list {stories}` (만료 안 된 것, 최신순). `story_view {story_id}` → 조회자 기록, 소유자에게 `story_updated {story}`. `story_delete {story_id}`(소유자) → 모두에게 `story_deleted {story_id}`. 24시간 지나면 스케줄러가 삭제하고 `story_deleted`.

### 8.4 번역 — 제외
사용자 요청으로 메시지 번역은 구현하지 않는다.

### 8.5 멀티프로필
- `multi_profile_set {profiles:[{profile_id?, name, display_name, status_message, avatar_b64?|avatar_clear?, viewers:[username]}]}` → 내 멀티프로필 전체 교체. `multi_profile_list` → `multi_profile_list {profiles:[{profile_id, name, display_name, status_message, avatar_id, viewers}]}`.
- 서버는 viewer에게 보내는 내 User의 display_name/status_message/avatar_id를 해당 프로필 값으로 바꿔서 보낸다(welcome, user_updated 모두 수신자별). 나 자신은 기본 프로필을 본다.

### 8.6 차단 / 숨김
- 숨김: 클라이언트 로컬 설정 `hidden_friends`.
- 차단: `block_set {username, blocked:bool}` → `block_list {blocked:[username]}` 응답. 차단하면 차단된 사람이 보낸 메시지(1:1·그룹 모두)를 나에게 push 하지 않고, history/last_message/unread_count/search 에서도 제외. 상대는 차단 사실을 알 수 없다. welcome에 `blocked:[...]`.

### 8.7 사다리 게임
- `ladder_create {room_id, participants:[str], results:[str]}` (2~10개, 개수 동일) → 서버가 무작위 사다리 생성: Message kind=`ladder`, `ladder:{participants, results, rungs:[[row, col], ...], mapping:{participant: result}}` (rows=10, col은 왼쪽 세로줄 인덱스, 같은 row에서 인접 가로줄 없음).

### 8.8 톡게시판
- `board_post {room_id, title, content}` → Post `{post_id, room_id, author, title, content, created_at, comments:[{comment_id, author, content, created_at}]}`; 방에 kind=`board` 메시지(content=title, `post_id`) 게시 + 멤버에게 `board_updated {post}`.
- `board_list {room_id}` → `board_list {room_id, posts}` · `board_comment {post_id, content}` → `board_updated` · `board_delete {post_id}`(작성자) → `board_deleted {post_id, room_id}`.

### 8.9 오픈채팅
- 방 종류 `open`: `open_room_create {name, description, tags:[str]}` → 만든 사람 포함 room_updated. Room에 `description`, `tags`, `nicknames:{username: nickname}` 추가.
- `open_room_search {query}` → `open_room_search {rooms:[{room_id, name, description, tags, member_count}]}` (참여 안 한 방 포함). `open_room_join {room_id, nickname}` → 멤버 추가 + 시스템 메시지 "<닉네임>님이 들어왔습니다" (오픈채팅에서는 실명 대신 닉네임 표시).

### 8.10 받은 파일 보관 기간 / 톡서랍
- 첨부 보관 기간: 서버 옵션 `retention_days`(기본 90). attachment 메타에 `expires_at`. 만료된 첨부는 스케줄러가 데이터 삭제, attachment 메타 `expired:true`, `attachment_get`은 오류 "보관 기간이 지난 파일입니다".
- 톡서랍(전체): `drawer_query {kind:'image'|'file'|'link', limit?}` → `drawer_result {kind, messages}` 내가 속한 모든 방에서 최신순.

### 8.11 클라이언트 전용
- 잠금모드: 4자리 PIN(설정 `lock_pin_hash` = sha256(salt+pin), `lock_salt`), N분(설정 `lock_minutes`, 기본 5) 무입력 시 또는 수동 잠금, 잠금 중 알림은 "새 메시지" 로만 표시.
- 키워드 알림: 설정 `alert_keywords:[str]` — 알림 끈 방이어도 키워드 포함 메시지는 알림 + 말풍선 강조.
- 채팅방별 알림 모드: 설정 `room_alert_modes:{room_id: 'all'|'mention'|'off'}` (off = 기존 muted_rooms와 동기).
- 말풍선 꾸미기: 설정 `bubble_style:{preset}` – 'basic'|'round'|'square'|'pastel'|'mono' 등, 내 말풍선 색/모서리.
- 기능 둘러보기: 더보기 → "기능 둘러보기" 체크리스트(기능·설명·해보기 버튼) + `scripts/demo.py`(서버 + 데모 데이터 + 클라이언트 여러 개 실행) + `scripts/verify_features.py`(기능별 테스트 결과 표).

### 8.12 친구 등록 (전화번호 · 이메일)
- User 에 `email` 추가. `profile_update` 에 `mobile`, `email` (형식 검증) 추가.
- `friend_add {query}` → 전화번호(숫자만 비교, +82→0) 또는 이메일(대소문자 무시)이 **정확히** 일치하는 사용자를 내 친구로 등록 → `friend_added {user, already}` + `friend_list {friends}`. 없으면 오류 "해당 전화번호·이메일로 가입한 사용자가 없습니다." (부분 일치·목록 조회 없음)
- `friend_remove {username}` / `friend_list` → `friend_list {friends}`. welcome 에 `friends`.

---

## 9. v4 — 카카오톡 2026 업데이트 반영 (2026-10-09)

출처: 카카오 정기 업데이트 발표 (2차 3월, 4차 5월 v26.4.0, 6차 7월 v26.6.0) + PC 카카오톡 '＋' 메뉴·대화 내보내기.

| 카카오톡 | KCS Talk |
|---|---|
| v26.6.0 채팅방별 AI 대화 요약 | §9.1 `room_summary` (Claude, 실패 시 추출형) + 안 읽은 메시지 20개 이상이면 '대화 요약 보기' 칩 |
| v26.4.0 말풍선 리액션 6종 → 114종, 말풍선당 최대 30개 | §9.2 공감 72종 선택 창, 말풍선당 30종 상한, 6종 넘으면 +N |
| PC ＋ 메뉴: 음성메시지 · 연락처 | §9.3 kind `voice` · `contact` |
| v26.4.0 채팅탭 '통화' 폴더 | §9.4 `call_history` + 기본 폴더 '통화' |
| PC 대화 내보내기(.txt) | §9.5 `room_export` + 클라이언트가 카카오톡 형식 텍스트로 저장 |
| 2차: 친구 소식(피드) 숨기기 | §9.6 클라이언트 설정 `hidden_story_users` |

### 9.1 대화 요약
- `room_summary {room_id, unread_only?:bool, since_msg_id?:int}` → (비동기) `room_summary {room_id, summary, source:'claude'|'extractive', count, unread_only}`.
- 대상: 최근 300개 중 삭제·시스템·비밀 메시지를 뺀 것. `since_msg_id`(또는 unread_only 면 내 읽음 위치) 이후만.
- 비밀채팅방은 오류(서버가 내용을 모름). Claude 는 RAG 서비스의 클라이언트를 재사용하고, 꺼져 있거나 실패하면 추출형(참여자·키워드·[결정]/[요청]/[일정]/[질문] 문장·공유 수).

### 9.2 공감 확대
- `react` 에서 새 종류를 추가할 때 이미 30종이면 오류 "공감은 메시지 하나에 30종류까지 달 수 있습니다." (이미 있는 종류에 더하기·취소는 가능)

### 9.3 음성메시지 · 연락처
- `send {kind:'voice', content:'<초 1~300>', attachment:{name, mime:'audio/*', data_b64}}` — 첨부는 file 과 같이 저장·보관 기간 적용, 톡서랍 '파일'에 포함. 클라이언트는 16kHz mono WAV.
- `send {kind:'contact', content:'<username>'}` — 존재하는 사용자만. 받은 쪽은 카드(1:1 채팅·프로필). 전달 가능.
- 비밀채팅방에서는 둘 다 불가(기존 규칙).

### 9.4 통화 기록
- 서버는 통화가 끝나면 `call_log(call_id, room_id, mode, host, started_at, duration, participants)` 저장 (participants = 한 번이라도 참여한 사람).
- `call_history {limit?}` → `call_history {calls:[{call_id, room_id, mode, host, started_at, duration_seconds, participants, joined, missed}]}` 내가 속한 방, 최근 순. `missed = 내가 참여하지 않음`.
- 클라이언트: welcome 직후·`call_ended` 때 다시 요청. 기본 폴더 '통화'(칩 숫자 = 부재중 수, 0이면 숫자 없음)에서 통화 기록 행을 보여 주고 누르면 그 방을 연다.

### 9.5 대화 내보내기
- `room_export {room_id}` → `room_export {room_id, messages(오래된 순, 최대 20000, 차단 사용자 제외), truncated}`.
- 클라이언트 형식: `<방 이름> 님과 카카오톡 대화` / `저장한 날짜 : YYYY-MM-DD HH:MM:SS` / `--------------- YYYY년 M월 D일 X요일 ---------------` / `[이름] [오전|오후 H:MM] 내용` (시스템 메시지는 내용만, 첨부 등은 미리보기 문구). 나에게서 삭제한 메시지는 뺀다. 비밀채팅은 이 PC에서 해독한 내용.

### 9.6 친구 소식 숨기기
- 설정 `hidden_story_users:[username]`. 숨긴 사람의 펑은 펑 줄에서 빠지고, 친구 관계·채팅은 그대로. 친구 우클릭 '소식 숨기기/소식 다시 보기', 펑 동그라미 우클릭 '소식 숨기기'.

### 9.7 보내지 못한 메시지 (클라이언트 전용, 프로토콜 변경 없음)
- `send`가 연결 없음으로 나가지 못하면(text·emoticon) 로컬 메시지 `{msg_id: 10^12+n, failed:true, ...}`를 만들어 대화 맨 아래에 표시하고 설정 `failed_messages`에 저장(앱 재시작 후 복원).
- 실패 메시지는 읽음 처리·안 읽은 수·이전 기록 요청에서 제외. 재전송 = 로컬 메시지 제거 후 일반 `send`(다시 실패하면 새 실패 메시지). 삭제 = 로컬에서만 제거.
- 파일·사진·비밀 메시지는 보존하지 않고 "서버 연결이 끊겨 … 보내지 못했습니다. 연결된 뒤 다시 보내 주세요." 안내.
