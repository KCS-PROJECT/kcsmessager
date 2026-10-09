# -*- coding: utf-8 -*-
"""
기능 둘러보기 (명세 §8.11) - 구현된 모든 기능의 검색 가능한 체크리스트

    FeatureTourDialog(state, settings, main_window, parent=None)
      - '기능 목록' 탭: 영역별로 묶인 기능 · 설명/사용법 · [해보기] (해본 기능은 체크, 설정 'tour_checked'에 저장)
      - '검증 결과' 탭: claudedocs/FEATURE_VERIFICATION.md (scripts/verify_features.py 결과)를 보여 준다

[해보기]는 가능한 한 실제 동작을 한다(탭 전환, 채팅방 열기, 대화상자 열기, 작성창 시작 …).
다른 모듈의 기능은 지연 import + try/except 로 불러오므로, 아직 없는 기능은 사용법 안내로 대신한다.
기능 목록(FEATURES)은 scripts/verify_features.py 의 기능 이름과 공유한다.
"""

import importlib
import os
import re

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget,
                             QTabWidget, QScrollArea, QFrame, QCheckBox, QTextBrowser, QApplication,
                             QSizePolicy)

from client.kakao import theme
from client.kakao.state import BOT_NAME

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VERIFICATION_PATH = os.path.join(ROOT, 'claudedocs', 'FEATURE_VERIFICATION.md')

GROUPS = ['친구·프로필', '채팅방', '메시지', '채팅방 기능', '통화', '캘린더', 'AI 비서', '조직도', '설정·브랜드']

# (key, 영역, 기능 이름, 설명/사용법, 도입 버전, 해보기 동작)
# 동작 = (FeatureTourDialog 메서드 이름 접미사, 인자...) → do_<이름>(*인자)
FEATURES = [
    # ---- 친구·프로필 (명세 §1, §7.2, §8.3, §8.5, §8.6)
    ('friends', '친구·프로필', '친구 목록 · 검색', '친구 탭에서 온라인 여부와 상태메시지를 보고, 🔍로 이름을 검색합니다.', 'v1', ('tab', 'friends')),
    ('profile_edit', '친구·프로필', '내 프로필 편집', '프로필 사진·이름·상태메시지를 바꿉니다. 친구 탭 맨 위 내 프로필을 누르세요.', 'v2', ('profile_edit',)),
    ('presence', '친구·프로필', '상태 표시 (온라인·자리비움·다른 용무 중·회의 중)', '내 상태를 직접 고르면 모두에게 색 점으로 보입니다. 10분간 입력이 없으면 자동으로 자리비움이 됩니다.', 'v2', ('presence',)),
    ('friend_add', '친구·프로필', '친구 추가 (전화번호 · 이메일)', '친구 탭 위 👤+ 버튼 → 상대가 프로필에 등록한 휴대폰 번호나 이메일을 정확히 입력하면 친구로 추가됩니다. 내 번호·이메일은 프로필 편집에서 등록.', 'v3',
     ('ext_dialog', 'friends_tab', 'AddFriendDialog', '친구 탭 오른쪽 위 👤+ 버튼을 누르세요.')),
    ('favorites', '친구·프로필', '즐겨찾기 친구', '친구를 우클릭 → 즐겨찾기 추가. 즐겨찾기 섹션과 채팅 \'즐겨찾기\' 폴더에 모입니다.', 'v1', ('tab', 'friends', '친구를 우클릭해 즐겨찾기에 추가해 보세요.')),
    ('birthday', '친구·프로필', '생일인 친구', '오늘 생일인 친구가 친구 탭 위쪽에 보이고, 🎁 버튼으로 바로 축하 메시지를 보냅니다.', 'v1', ('tab', 'friends')),
    ('profile_view', '친구·프로필', '프로필 보기 (소속·내선·휴대폰·겸직)', '친구를 더블클릭하면 프로필 창이 열리고 1:1 채팅을 시작할 수 있습니다.', 'v2', ('profile_view',)),
    ('story_hide', '친구·프로필', '친구 소식 숨기기', '친구 우클릭(또는 펑 동그라미 우클릭) → 소식 숨기기. 친구 관계는 그대로 두고 내 화면에서만 감춥니다. 더보기 → 소식 기능이 켜져 있을 때 보입니다.', '2026',
     ('tab', 'friends', '친구를 우클릭 → 소식 숨기기')),
    ('multi_profile', '친구·프로필', '멀티프로필', '친구마다 다른 이름·상태메시지·사진을 보여 줍니다. 더보기 → 멀티프로필.', 'v3',
     ('ext_dialog', 'more_tab', 'MultiProfileDialog', '더보기 탭 → 멀티프로필에서 설정합니다.')),
    ('hide_block', '친구·프로필', '친구 숨김 · 차단', '숨긴 친구는 목록에서 빠지고, 차단한 사람의 메시지는 받지 않습니다(상대는 모름). 더보기 → 친구 관리.', 'v3',
     ('ext_dialog', 'more_tab', 'FriendManageDialog', '친구를 우클릭 → 숨김/차단, 더보기 → 친구 관리에서 해제합니다.')),
    ('story_post', '친구·프로필', '펑 올리기 (24시간 스토리)', '글이나 사진을 올리면 24시간 뒤 사라집니다. 누가 봤는지 확인할 수 있습니다.', 'v3',
     ('ext_dialog', 'story', 'StoryComposeDialog', '친구 탭 위쪽 펑 줄의 ＋ 버튼으로 올립니다.')),
    ('story_view', '친구·프로필', '펑 보기', '친구 탭 위쪽 펑 줄에서 친구 사진을 누르면 순서대로 넘겨 봅니다(안 본 펑은 테두리 강조).', 'v3', ('story_view',)),

    # ---- 채팅방 (명세 §1, §7.8, §8.1, §8.9, §8.11)
    ('direct', '채팅방', '1:1 채팅', '친구를 더블클릭하거나 새로운 채팅에서 한 명을 고릅니다.', 'v1', ('room', 'direct')),
    ('group', '채팅방', '그룹 채팅 만들기', '채팅 탭 ＋ 버튼 → 대화상대 2명 이상 선택 → 방 이름(선택).', 'v1', ('create_group',)),
    ('self_chat', '채팅방', '나와의 채팅', '메모장처럼 쓰는 나만의 채팅방입니다. 메시지 메뉴 \'나에게 보내기\'도 여기로 옵니다.', 'v1', ('room', 'self')),
    ('room_list', '채팅방', '채팅 목록 · 안 읽은 수', '마지막 메시지·시간·안 읽은 수 배지가 보이고, 사이드바와 창 제목에 합계가 표시됩니다.', 'v1', ('tab', 'chats')),
    ('rename', '채팅방', '채팅방 이름 변경', '채팅방 메뉴(☰) → 채팅방 이름 변경.', 'v1', ('room_call', 'group', ['rename_room'], '채팅방 메뉴 → 이름 변경')),
    ('invite', '채팅방', '대화상대 초대', '그룹방은 그 방에, 1:1 방에서 초대하면 새 그룹방이 만들어집니다.', 'v2', ('room_call', 'group', ['open_invite_dialog'], '채팅방 상단 👤+ 버튼')),
    ('leave', '채팅방', '채팅방 나가기', '채팅 목록에서 방을 우클릭 → 나가기. (해보기는 안전을 위해 안내만 합니다)', 'v1', ('tab', 'chats', '채팅방을 우클릭 → 나가기 (대화 내용이 삭제되니 주의하세요).')),
    ('pin_mute', '채팅방', '상단 고정 · 알림 끄기', '채팅 목록에서 방을 우클릭 → 채팅방 상단 고정 / 채팅방 알림 끄기.', 'v1', ('tab', 'chats', '채팅방을 우클릭해 상단 고정·알림 끄기를 해 보세요.')),
    ('alert_mode', '채팅방', '채팅방별 알림 모드 (전체·멘션만·끄기)', '채팅방 메뉴 → 알림 설정에서 방마다 알림 범위를 고릅니다.', 'v3',
     ('room_call', 'group', ['open_alert_mode_menu', 'open_alert_settings', 'open_alert_mode_dialog'], '채팅방 메뉴(☰) → 알림 설정')),
    ('folders', '채팅방', '채팅방 폴더', '전체·안읽음·즐겨찾기 기본 폴더 + 직접 만든 폴더. 칩 줄의 ＋로 만듭니다.', '2025', ('folder',)),
    ('keyboard', '채팅방', '키보드로 쓰기 (단축키)', 'Ctrl+1~5 탭 이동 · Ctrl+K 빠른 이동 · Ctrl+N 새 채팅 · 채팅방에서 Alt+↑/↓ 메시지 고르기 → Shift+F10 메시지 메뉴 · Esc 해제.', 'v4',
     ('room', 'group', '채팅방에서 Alt+↑ 를 누른 뒤 Shift+F10 을 눌러 보세요.')),
    ('call_folder', '채팅방', "'통화' 폴더 (통화 기록 · 부재중)", "채팅 탭 칩 줄의 '통화'. 보이스톡·페이스톡·보이스룸 기록과 부재중 통화를 모아 보고, 누르면 그 채팅방이 열립니다.", '2026', ('call_folder',)),
    ('peek', '채팅방', '읽지 않고 미리보기', '안 읽은 방을 우클릭 → 읽지 않고 미리보기. 상대에게 읽음으로 표시되지 않습니다.', '2025', ('peek',)),
    ('open_chat', '채팅방', '오픈채팅 (찾기·참여·만들기)', '채팅 탭 상단 # 버튼. 태그로 방을 찾아 닉네임으로 참여하거나 새 방을 엽니다. 목록에 \'오픈\' 배지가 붙습니다.', 'v3', ('open_chat',)),
    ('secret', '채팅방', '비밀채팅 (종단간 암호화)', '친구 우클릭 → 비밀채팅. 내용은 두 사람 PC에서만 풀리고 서버는 읽을 수 없습니다.', 'v3', ('room', 'secret')),
    ('lock', '채팅방', '잠금모드 (PIN)', '4자리 PIN을 정하면 N분 무입력 시 또는 직접 잠글 수 있고, 잠금 중 알림은 \'새 메시지\'로만 보입니다.', 'v3', ('lock',)),

    # ---- 메시지 (명세 §1, §7.1, §7.8, §8.11)
    ('text_emoticon', '메시지', '텍스트 · 이모티콘', 'Enter 전송, Shift+Enter 줄바꿈, 😊 버튼으로 이모티콘.', 'v1', ('room_call', 'any', ['open_emoticons'], '입력창 왼쪽 😊 버튼')),
    ('attach', '메시지', '사진 · 파일 보내기 (10MB)', '📎 버튼, 드래그&드롭, 클립보드 이미지 붙여넣기(⌘V) 모두 됩니다. 받은 파일은 저장/열기.', 'v2', ('room_call', 'any', ['pick_file'], '입력창의 📎 버튼')),
    ('voice_msg', '메시지', '음성메시지 (최대 5분)', '입력창 ＋ → 음성메시지. 녹음을 멈추고 보내기를 누르면 전송되고, 받은 말풍선의 ▶로 재생합니다.', 'v4',
     ('room_call', 'group', ['open_voice_recorder'], '입력창 ＋ → 음성메시지')),
    ('contact_share', '메시지', '연락처 보내기', '입력창 ＋ → 연락처 보내기. 받은 사람은 카드에서 바로 1:1 채팅을 하거나 프로필을 봅니다.', 'v4',
     ('room_call', 'group', ['open_contact_picker'], '입력창 ＋ → 연락처 보내기')),
    ('failed_resend', '메시지', '보내지 못한 메시지 (재전송 · 삭제)', '연결이 끊긴 동안 보낸 글은 사라지지 않고 빨간 ! 와 \'전송 실패\'로 남습니다. ! 를 눌러 재전송하거나 삭제하세요. 앱을 다시 켜도 남아 있습니다.', 'v4',
     ('room', 'group', '서버 연결이 끊긴 상태에서 메시지를 보내 보세요.')),
    ('read_count', '메시지', '읽음 숫자', '말풍선 옆 노란 숫자 = 아직 안 읽은 사람 수. 읽을수록 줄어듭니다.', 'v1', ('room', 'group')),
    ('reply', '메시지', '답장', '말풍선 우클릭 → 답장. 원문이 인용되어 함께 보내집니다.', 'v1', ('room_msg', 'group', 'start_reply', 'other')),
    ('reaction', '메시지', '공감', '말풍선 우클릭 → 공감(👍❤️😂😮😢). 다시 누르면 취소됩니다.', 'v1', ('room', 'group', '말풍선을 우클릭해 공감을 눌러 보세요.')),
    ('reaction_more', '메시지', '공감 72종 (말풍선당 30종)', '말풍선 우클릭 → 공감 → 더 많은 공감…. 6종이 넘으면 말풍선 아래 +N 으로 접힙니다.', '2026',
     ('room', 'group', '말풍선을 우클릭 → 공감 → 더 많은 공감…')),
    ('edit', '메시지', '메시지 수정 (24시간)', '내가 보낸 텍스트를 우클릭 → 수정. \'수정됨\'이 표시되고 검색·AI 색인도 바뀝니다.', '2025', ('room_msg', 'group', 'start_edit', 'mine')),
    ('delete', '메시지', '메시지 삭제 (24시간, 모두/나에게서)', '우클릭 → 삭제. 모두에게서 삭제하면 \'메시지가 삭제되었습니다\'만 남습니다.', '2025', ('room', 'group', '내 메시지를 우클릭 → 삭제를 골라 보세요.')),
    ('copy_forward', '메시지', '복사 · 전달 · 나에게 보내기', '말풍선 우클릭 메뉴에서 고릅니다.', 'v1', ('room', 'group', '말풍선을 우클릭 → 전달/나에게 보내기.')),
    ('mention', '메시지', '멘션 (@이름)', '입력창에 @를 치면 대화상대 목록이 뜹니다. 멘션된 사람은 강조 표시됩니다.', 'v1', ('room', 'group', '입력창에 @ 를 입력해 보세요.')),
    ('scheduled', '메시지', '예약 메시지', '전송 시각을 정해 두면 그 시각에 보내집니다.', 'v1', ('room_call', 'group', ['open_schedule_dialog'], '입력창 메뉴 → 예약 메시지')),
    ('silent', '메시지', '조용히 보내기', '전송 버튼 우클릭 또는 Ctrl(⌘)+Shift+Enter. 상대에게 알림 없이 안 읽은 수에만 반영됩니다.', '2025', ('room', 'group', '전송 버튼을 우클릭 → 조용히 보내기.')),
    ('link_preview', '메시지', 'URL 미리보기', 'http(s) 주소를 보내면 서버가 제목·설명을 가져와 카드로 보여 줍니다.', '2025', ('room', 'group', 'https://로 시작하는 주소를 보내 보세요.')),
    ('keyword_alert', '메시지', '키워드 알림', '정한 단어가 들어간 메시지는 알림 끈 방에서도 알려 주고 말풍선을 강조합니다.', 'v3',
     ('ext_dialog', 'more_tab', 'KeywordAlertDialog', '더보기 → 키워드 알림')),
    ('bubble_style', '메시지', '말풍선 꾸미기', '내 말풍선 색·모서리 스타일(기본·동글동글·파스텔·모노…)을 고릅니다.', 'v3',
     ('ext_dialog', 'more_tab', 'BubbleStyleDialog', '더보기 → 말풍선 꾸미기')),

    # ---- 채팅방 기능 (명세 §1, §7.5, §8.7, §8.8, §8.10)
    ('notice', '채팅방 기능', '공지', '말풍선 우클릭 → 공지로 등록하면 방 상단 배너에 고정됩니다.', 'v1', ('room', 'group', '말풍선을 우클릭 → 공지 등록.')),
    ('poll', '채팅방 기능', '투표', '단일/복수 선택 투표를 만들고, 만든 사람이 마감합니다.', 'v1', ('room_call', 'group', ['open_poll_dialog'], '입력창 메뉴 → 투표')),
    ('search', '채팅방 기능', '대화 검색', '채팅방 🔍 → 검색어 입력, ↑↓로 결과 사이를 이동합니다.', 'v1', ('room_call', 'group', ['open_search', 'toggle_search'], '채팅방 상단 🔍')),
    ('room_drawer', '채팅방 기능', '채팅방 서랍 (사진·파일·링크·일정)', '그 방에서 오간 사진·파일·링크와 방에서 만든 일정을 모아 봅니다.', 'v1', ('room_call', 'group', ['open_drawer'], '채팅방 메뉴 → 서랍')),
    ('wallpaper', '채팅방 기능', '배경화면', '색·그라데이션·사진·KCS 브랜드 배경. 전체 기본값과 방별 배경을 따로 정합니다.', 'v2', ('wallpaper',)),
    ('ladder', '채팅방 기능', '사다리 게임', '참가자와 결과를 넣으면 서버가 무작위 사다리를 만들어 모두에게 보여 줍니다.', 'v3',
     ('room_call', 'group', ['open_ladder_dialog', 'open_ladder', 'start_ladder'], '입력창 메뉴 → 사다리 게임', ('chat_room', 'LadderDialog'))),
    ('board', '채팅방 기능', '톡게시판', '방의 공지성 글을 게시판에 올리고 댓글을 답니다.', 'v3',
     ('room_call', 'group', ['open_board_dialog', 'open_board', 'show_board'], '채팅방 메뉴 → 톡게시판', ('chat_room', 'BoardDialog'))),
    ('chat_export', '채팅방 기능', '대화 내보내기 (.txt)', '채팅방 메뉴(☰) → 대화 내보내기. 카카오톡 PC와 같은 형식(날짜 구분선, [이름] [시각] 내용)의 텍스트로 저장합니다.', 'v4',
     ('room_call', 'group', ['export_chat'], '채팅방 메뉴 → 대화 내보내기')),
    ('talk_drawer', '채팅방 기능', '톡서랍 (모든 채팅방)', '채팅 탭 상단 서랍 버튼. 모든 방의 사진·파일·링크를 모아 보고, 더블클릭하면 그 메시지로 갑니다.', 'v3', ('talk_drawer',)),
    ('retention', '채팅방 기능', '받은 파일 보관 기간', '첨부 파일은 서버에 90일 보관됩니다. 기간이 지나면 \'보관 기간이 지난 파일\'로 표시됩니다.', 'v3', ('talk_drawer', '파일 탭에서 \'만료\' 표시를 확인할 수 있습니다.')),

    # ---- 통화 (명세 §8.2)
    ('voice_call', '통화', '보이스톡', '1:1 또는 그룹 방 상단 📞 버튼. 음소거를 켜고 끌 수 있습니다.', 'v3', ('call', 'direct', 'voice')),
    ('face_call', '통화', '페이스톡 (그룹 최대 10명)', '채팅방 상단 🎥 버튼. 카메라를 켜고 끌 수 있습니다.', 'v3', ('call', 'group', 'video')),
    ('voiceroom', '통화', '보이스룸', '진행자·스피커·리스너 역할이 있는 음성방. 리스너는 손을 들어 발언을 요청합니다. 48시간 뒤 자동 종료.', 'v3', ('call', 'group', 'voiceroom')),
    ('screen_share', '통화', '화면 공유', '통화 창에서 화면 공유 버튼을 누르면 내 화면을 참여자에게 보여 줍니다.', 'v3', ('room', 'group', '통화를 시작한 뒤 통화 창의 화면 공유 버튼을 누르세요.')),

    # ---- 캘린더 (명세 §1, §7.8)
    ('calendar', '캘린더', '톡캘린더 월간 보기', '캘린더 탭에서 달을 넘기고 날짜를 눌러 그날 일정을 봅니다.', 'v1', ('tab', 'calendar')),
    ('event_crud', '캘린더', '일정 만들기 · 수정 · 삭제', '캘린더 ＋ 버튼 또는 날짜 더블클릭. 종일·장소·색·알림을 정합니다.', 'v1', ('tab_call', 'calendar', 'open_new_event')),
    ('event_share', '캘린더', '채팅방 일정 공유 + 참석 응답', '채팅방에서 일정을 만들면 카드가 올라가고 참석/불참/미정으로 응답합니다.', 'v1', ('room_call', 'group', ['open_event_dialog'], '입력창 메뉴 → 일정')),
    ('event_remind', '캘린더', '일정 알림 (N분 전)', '일정에 알림을 정하면 시작 전에 트레이 알림이 옵니다.', 'v1', ('tab', 'calendar', '일정을 만들 때 \'알림\'을 정해 보세요.')),
    ('event_changed', '캘린더', '일정 변경 알림', '다른 사람이 일정의 제목·시간·장소를 바꾸면 \'일정이 변경되었습니다\' 알림이 옵니다.', '2025', ('tab', 'calendar')),
    ('room_events', '캘린더', '채팅방 서랍 \'일정\' 탭', '채팅방 서랍의 일정 탭에서 그 방에서 만든 일정을 모아 봅니다.', '2025', ('room_call', 'group', ['open_drawer'], '채팅방 메뉴 → 서랍 → 일정')),
    ('todo', '캘린더', '할 일', '캘린더 탭의 \'할 일\'에서 추가·완료·마감일을 관리합니다.', 'v1', ('tab_call', 'calendar', 'set_section', 1)),
    ('birthday_cal', '캘린더', '생일 표시', '친구 생일이 달력에 🎂로 표시됩니다.', 'v1', ('tab', 'calendar')),

    # ---- AI 비서 (명세 §7.6, §7.8)
    ('ai_chat', 'AI 비서', 'AI 비서와 대화', '채팅 탭 ✨ 버튼. 내 대화와 문서에서 찾아 출처와 함께 답합니다.', 'v2', ('room', 'bot')),
    ('ai_invite', 'AI 비서', '그룹방에 AI 비서 부르기 (@AI 비서)', '채팅방 메뉴 → AI 비서 부르기 후 @AI 비서 로 질문합니다.', '2025', ('room_call', 'group', ['invite_bot'], '채팅방 메뉴 → AI 비서 부르기')),
    ('ai_docs', 'AI 비서', 'AI 지식베이스 (문서 학습)', 'AI 비서 1:1 방에 txt·md·csv·pdf를 보내거나 더보기 → AI 지식베이스에서 올립니다.', 'v2', ('rag_docs',)),
    ('ai_summary', 'AI 비서', '채팅방 대화 요약', "채팅방 메뉴(☰) → 대화 요약. 안 읽은 메시지가 20개 이상이면 방 위에 '대화 요약 보기' 칩이 뜹니다. Claude를 쓸 수 없으면 결정·요청·질문 문장을 뽑아 요약합니다.", '2026',
     ('room_call', 'group', ['show_summary'], '채팅방 메뉴 → 대화 요약')),
    ('briefing', 'AI 비서', '오늘의 브리핑', '하루 첫 접속 때 AI 비서가 오늘 일정·응답 필요한 일정·마감 할 일·안 읽은 수를 먼저 알려 줍니다.', '2025', ('room', 'bot', 'AI 비서 방 맨 아래의 브리핑 메시지를 확인하세요.')),

    # ---- 조직도 (명세 §7.3, §7.7)
    ('org_chart', '조직도', '그룹사 조직도', '지주사 → 계열사 → 부서 → 구성원. 구성원을 더블클릭하면 바로 대화합니다.', 'v2', ('tab', 'org')),
    ('company_chip', '조직도', '다른 회사 표시 칩', '다른 계열사 사람에게는 회사명 칩이 붙습니다(친구·채팅 목록, 채팅방 헤더).', 'v2', ('tab', 'friends')),
    ('org_dock', '조직도', '넓은 창에서 조직도 패널', '창을 860px 이상으로 넓히면 왼쪽에 조직도가 항상 펼쳐집니다.', 'v2', ('org_dock',)),

    # ---- 설정·브랜드 (명세 §1, §7.5, 브랜드)
    ('dark_mode', '설정·브랜드', '다크 모드', '더보기 → 다크 모드. 해보기를 누를 때마다 켜고 끕니다.', 'v1', ('toggle_setting', 'dark_mode')),
    ('font_size', '설정·브랜드', '글자 크기', '더보기 → 글자 크기 (작게~아주 크게).', 'v1', ('tab', 'more')),
    ('brand_theme', '설정·브랜드', '소식 기능 (펑 · 생일 · 선물하기)', '회사 메신저는 업무 우선이라 기본으로 꺼져 있습니다. 해보기를 누를 때마다 켜고 끕니다 (더보기 → 소식 기능).', 'v3', ('toggle_brand',)),
    ('brand_ci', '설정·브랜드', '회사 CI 로고', '로그인 화면, 사이드바, 앱·트레이 아이콘, 더보기 정보에 ㈜케이씨에스 CI가 들어갑니다.', 'v2', ('tab', 'more')),
    ('notifications', '설정·브랜드', '새 메시지 알림 (트레이)', '창을 보고 있지 않을 때 트레이 알림을 띄웁니다. 더보기에서 끌 수 있습니다.', 'v1', ('tab', 'more')),
    ('feature_tour', '설정·브랜드', '기능 둘러보기 · 데모 · 검증', '지금 이 창. python3 scripts/demo.py 로 데모 데이터와 클라이언트를, scripts/verify_features.py 로 기능별 테스트 결과를 만듭니다.', 'v3', ('verification',)),
]

FEATURE_KEYS = [f[0] for f in FEATURES]
FEATURE_NAMES = {f[0]: f[2] for f in FEATURES}
SINCE_LABELS = {'v1': '기본', 'v2': 'v2', '2025': '2025 개편', 'v3': 'v3', '2026': '2026 업데이트', 'v4': 'v4'}


def load_verification(path=None):
    """(마크다운 원문, {기능 이름: 'PASS'|'FAIL'}) - 파일이 없으면 ('', {})"""
    path = path or VERIFICATION_PATH
    try:
        with open(path, encoding='utf-8') as f:
            text = f.read()
    except OSError:
        return '', {}
    status = {}
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) >= 3:
            result = next((c for c in cells if re.fullmatch(r'(✅ )?PASS|(❌ )?FAIL', c)), None)
            if result:
                status[cells[1]] = 'PASS' if 'PASS' in result else 'FAIL'
    return text, status


# ================================================================ 행 위젯
class FeatureRow(QFrame):
    try_clicked = pyqtSignal(str)
    check_changed = pyqtSignal(str, bool)

    def __init__(self, feature, checked, verdict='', parent=None):
        super().__init__(parent)
        key, _group, name, desc, since, _action = feature
        self.key, self.name, self.desc = key, name, desc
        self.setObjectName('featureRow')
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)
        self.check = QCheckBox()
        self.check.setChecked(checked)
        self.check.setToolTip('해 본 기능 표시')
        row.addWidget(self.check, 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(2)
        top = QHBoxLayout()
        top.setSpacing(6)
        self.name_label = QLabel(name)
        self.name_label.setObjectName('featureName')
        self.name_label.setWordWrap(True)
        top.addWidget(self.name_label, 1)
        self.since_label = QLabel(SINCE_LABELS.get(since, since))
        self.since_label.setObjectName('since_' + since)
        top.addWidget(self.since_label, 0, Qt.AlignTop)
        self.verdict_label = QLabel({'PASS': '검증 ✓', 'FAIL': '검증 ✗'}.get(verdict, ''))
        self.verdict_label.setObjectName('verdictPass' if verdict == 'PASS' else 'verdictFail')
        self.verdict_label.setVisible(bool(verdict))
        top.addWidget(self.verdict_label, 0, Qt.AlignTop)
        col.addLayout(top)
        self.desc_label = QLabel(desc)
        self.desc_label.setObjectName('featureDesc')
        self.desc_label.setWordWrap(True)
        self.desc_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        col.addWidget(self.desc_label)
        row.addLayout(col, 1)
        self.try_button = QPushButton('해보기')
        self.try_button.setObjectName('primary')
        self.try_button.setCursor(Qt.PointingHandCursor)
        row.addWidget(self.try_button, 0, Qt.AlignVCenter)
        self.try_button.clicked.connect(lambda: self.try_clicked.emit(self.key))
        self.check.toggled.connect(lambda on: self.check_changed.emit(self.key, on))

    def matches(self, query, group=''):
        q = query.lower()
        return not q or q in self.name.lower() or q in self.desc.lower() or q in group.lower()


class GroupHeader(QLabel):
    def __init__(self, group, parent=None):
        super().__init__(group, parent)
        self.group = group
        self.setObjectName('groupHeader')


# ================================================================ 다이얼로그
class FeatureTourDialog(QDialog):
    """기능 둘러보기. 모달리스로 띄우는 것을 권장(해보기가 다른 창을 연다)"""

    def __init__(self, state, settings, main_window, parent=None):
        super().__init__(parent if parent is not None else (main_window if isinstance(main_window, QWidget) else None))
        self.state = state
        self.settings = settings
        self.main_window = main_window
        self.opened = []            # 해보기로 연 다이얼로그 (가비지 컬렉션 방지)
        self.last_message = ''
        self._checked = set(self._load_checked())
        self.setWindowTitle('기능 둘러보기')
        self.setModal(False)
        self.setMinimumSize(420, 520)
        self.resize(620, 760)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(8)
        head = QHBoxLayout()
        title = QLabel('기능 둘러보기')
        title.setObjectName('panelTitle')
        head.addWidget(title)
        head.addStretch(1)
        self.progress_label = QLabel('')
        self.progress_label.setObjectName('panelHint')
        head.addWidget(self.progress_label)
        layout.addLayout(head)
        hint = QLabel('KCS Talk에 들어 있는 기능을 하나씩 해 보세요. [해보기]를 누르면 해당 화면이 열립니다.')
        hint.setObjectName('panelHint')
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        # ---- 기능 목록
        page = QWidget()
        pcol = QVBoxLayout(page)
        pcol.setContentsMargins(0, 10, 0, 0)
        pcol.setSpacing(8)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('기능 검색 (예: 투표, 비밀, 캘린더)')
        self.search_edit.setClearButtonEnabled(True)
        pcol.addWidget(self.search_edit)
        self.banner = QLabel('')
        self.banner.setObjectName('infoBanner')
        self.banner.setWordWrap(True)
        self.banner.hide()
        pcol.addWidget(self.banner)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        inner.setObjectName('scrollInner')
        col = QVBoxLayout(inner)
        col.setContentsMargins(0, 0, 6, 0)
        col.setSpacing(6)
        _md, verdicts = load_verification()
        self.rows = {}
        self.headers = {}
        for group in GROUPS:
            items = [f for f in FEATURES if f[1] == group]
            if not items:
                continue
            header = GroupHeader(group)
            self.headers[group] = header
            col.addWidget(header)
            for feature in items:
                row = FeatureRow(feature, feature[0] in self._checked, verdicts.get(feature[2], ''))
                row.try_clicked.connect(self.try_feature)
                row.check_changed.connect(self._on_check)
                self.rows[feature[0]] = row
                col.addWidget(row)
        self.no_match = QLabel('찾는 기능이 없습니다.')
        self.no_match.setObjectName('emptyLabel')
        self.no_match.setAlignment(Qt.AlignCenter)
        self.no_match.hide()
        col.addWidget(self.no_match)
        col.addStretch(1)
        self.scroll.setWidget(inner)
        pcol.addWidget(self.scroll, 1)
        self.tabs.addTab(page, f'기능 목록 {len(FEATURES)}')

        # ---- 검증 결과
        vpage = QWidget()
        vcol = QVBoxLayout(vpage)
        vcol.setContentsMargins(0, 10, 0, 0)
        self.verify_view = QTextBrowser()
        self.verify_view.setOpenExternalLinks(True)
        vcol.addWidget(self.verify_view, 1)
        vrow = QHBoxLayout()
        self.verify_hint = QLabel('')
        self.verify_hint.setObjectName('panelHint')
        self.verify_hint.setWordWrap(True)
        vrow.addWidget(self.verify_hint, 1)
        self.reload_button = QPushButton('다시 읽기')
        vrow.addWidget(self.reload_button)
        vcol.addLayout(vrow)
        self.tabs.addTab(vpage, '검증 결과')

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.close_button = QPushButton('닫기')
        bottom.addWidget(self.close_button)
        layout.addLayout(bottom)

        self.search_edit.textChanged.connect(self.filter)
        self.reload_button.clicked.connect(self.load_verification)
        self.close_button.clicked.connect(self.reject)
        self.apply_theme()
        self.load_verification()
        self._update_progress()

    # ---- 표시
    def apply_theme(self):
        from client.kakao.chats_tab import panel_dialog_qss
        c = theme.c
        self.setStyleSheet(panel_dialog_qss() + f"""
            QFrame#featureRow {{ background: {c('bg_alt')}; border: 1px solid {c('border')}; border-radius: 10px; }}
            QLabel#featureName {{ font-size: {theme.fs('body')}px; font-weight: bold; }}
            QLabel#featureDesc {{ color: {c('text_sub')}; font-size: {theme.fs('meta')}px; }}
            QLabel#groupHeader {{ font-size: {theme.fs('emphasis')}px; font-weight: bold; color: {c('text')};
                                  padding: 10px 2px 2px 2px; }}
            QLabel[objectName^="since_"] {{ font-size: {theme.fs('micro')}px; color: {c('text_sub')};
                border: 1px solid {c('border')}; border-radius: 4px; padding: 1px 5px; }}
            QLabel#since_v3, QLabel#since_2025 {{ color: {c('link')}; border-color: {c('link')}; }}
            QLabel#verdictPass {{ font-size: {theme.fs('micro')}px; color: #FFFFFF; background: #3DA35D;
                                  border-radius: 4px; padding: 1px 5px; }}
            QLabel#verdictFail {{ font-size: {theme.fs('micro')}px; color: #FFFFFF; background: {c('badge')};
                                  border-radius: 4px; padding: 1px 5px; }}
            QPushButton#primary {{ padding: 6px 12px; }}
        """)

    def feature_keys(self):
        return list(self.rows)

    def visible_keys(self):
        return [k for k, row in self.rows.items() if not row.isHidden()]

    def filter(self, text=''):
        text = (text or '').strip()
        any_visible = False
        for group, header in self.headers.items():
            shown = False
            for f in FEATURES:
                if f[1] != group:
                    continue
                row = self.rows[f[0]]
                ok = row.matches(text, group)
                row.setVisible(ok)
                shown = shown or ok
            header.setVisible(shown)
            any_visible = any_visible or shown
        self.no_match.setVisible(not any_visible)

    def load_verification(self, _checked=False):
        md, verdicts = load_verification()
        if md:
            self.verify_view.setMarkdown(md)
            passed = sum(1 for v in verdicts.values() if v == 'PASS')
            self.verify_hint.setText(f'기능 {len(verdicts)}개 중 {passed}개 통과 · {os.path.relpath(VERIFICATION_PATH, ROOT)}')
        else:
            self.verify_view.setMarkdown(
                '## 아직 검증 결과가 없습니다\n\n터미널에서 다음을 실행하면 기능별 테스트 결과가 여기에 표시됩니다.\n\n'
                '```\npython3 scripts/verify_features.py\n```\n')
            self.verify_hint.setText('검증 결과 파일이 없습니다.')
        for key, row in self.rows.items():
            verdict = verdicts.get(FEATURE_NAMES[key], '')
            row.verdict_label.setText({'PASS': '검증 ✓', 'FAIL': '검증 ✗'}.get(verdict, ''))
            row.verdict_label.setObjectName('verdictPass' if verdict == 'PASS' else 'verdictFail')
            row.verdict_label.setVisible(bool(verdict))
            row.verdict_label.style().unpolish(row.verdict_label)
            row.verdict_label.style().polish(row.verdict_label)
        return verdicts

    # ---- 체크 상태 (설정 'tour_checked')
    def _load_checked(self):
        try:
            return list(self.settings.get('tour_checked') or []) if self.settings is not None else []
        except Exception:
            return []

    def _on_check(self, key, on):
        (self._checked.add if on else self._checked.discard)(key)
        if self.settings is not None:
            try:
                self.settings.set('tour_checked', [k for k in FEATURE_KEYS if k in self._checked])
            except Exception:
                pass
        self._update_progress()

    def _update_progress(self):
        self.progress_label.setText(f'{len(self._checked & set(FEATURE_KEYS))} / {len(FEATURES)} 해봄')

    def explain(self, text):
        self.last_message = text or ''
        self.banner.setText(self.last_message)
        self.banner.setVisible(bool(self.last_message))
        return self.last_message

    # ---- 해보기
    def try_feature(self, key):
        """기능 실행. 안내/결과 문구를 돌려준다 (예외는 배너로 보여 주고 삼킨다)"""
        feature = next((f for f in FEATURES if f[0] == key), None)
        if feature is None:
            return ''
        self._ensure_modeless()
        action, args = feature[5][0], feature[5][1:]
        try:
            message = getattr(self, f'do_{action}')(*args)
        except Exception as e:  # 다른 모듈이 아직 준비되지 않았어도 둘러보기는 계속 동작해야 한다
            message = f"'{feature[2]}'을(를) 열지 못했습니다 ({e.__class__.__name__}). 사용법: {feature[3]}"
        row = self.rows.get(key)
        if row is not None and not row.check.isChecked():
            row.check.setChecked(True)
        return self.explain(message or f"{feature[2]}: {feature[3]}")

    def _ensure_modeless(self):
        """exec_()로 열린 경우 다른 창(채팅방 등)을 조작할 수 있게 모달리스로 다시 띄운다"""
        if self.isVisible() and QApplication.activeModalWidget() is self:
            self.hide()
            self.setWindowModality(Qt.NonModal)
            self.show()

    def _defer(self, fn, delay=0):
        def run():
            try:
                fn()
            except Exception as e:
                self.explain(f'실행 중 오류: {e.__class__.__name__}: {e}')
        QTimer.singleShot(delay, run)

    def _show_dialog(self, dlg):
        self.opened = [d for d in self.opened if _alive(d)]
        self.opened.append(dlg)
        dlg.setAttribute(Qt.WA_DeleteOnClose, True)
        dlg.show()
        dlg.raise_()
        return dlg

    def _mw(self, name):
        fn = getattr(self.main_window, name, None) if self.main_window is not None else None
        return fn if callable(fn) else None

    def _parent_widget(self):
        return self.main_window if isinstance(self.main_window, QWidget) else self

    def _values(self, **extra):
        values = {'state': self.state, 'settings': self.settings, 'parent': self._parent_widget(),
                  'main_window': self.main_window}
        values.update(extra)
        return values

    def _tab_widget(self, key):
        tabs = getattr(self.main_window, 'tabs', None) if self.main_window is not None else None
        return tabs.get(key) if isinstance(tabs, dict) else None

    # 방 찾기
    def find_room(self, kind):
        st = self.state
        rooms = st.sorted_rooms()

        def others(r):
            return [m for m in r.get('members', []) if m != st.me]
        tests = {
            'group': lambda r: r['type'] == 'group',
            'direct': lambda r: r['type'] == 'direct' and others(r) and not st.is_bot(others(r)[0]),
            'self': lambda r: r['type'] == 'self',
            'secret': lambda r: r['type'] == 'secret',
            'open': lambda r: r['type'] == 'open',
            'bot': lambda r: r['type'] == 'direct' and BOT_NAME in r.get('members', []),
        }
        if kind == 'any':
            for k in ('group', 'direct', 'open', 'self'):
                rid = self.find_room(k)
                if rid:
                    return rid
            return None
        return next((r['room_id'] for r in rooms if tests[kind](r)), None)

    def _first_friend(self):
        friends = self.state.friends()
        online = [u for u in friends if u.get('online')]
        return (online or friends or [None])[0]

    def open_room(self, rid):
        """방 창 열기 → 창 객체(없으면 None)"""
        fn = self._mw('open_room')
        if fn is not None:
            return fn(rid)
        self.state.room_opened.emit(rid)
        return None

    def _open_kind(self, kind):
        """(창, 방 id, 안내문). 방이 없으면 만들거나 만드는 화면을 연다"""
        rid = self.find_room(kind)
        if rid:
            return self.open_room(rid), rid, f"'{self.state.room_title(rid)}' 채팅방을 열었습니다."
        st = self.state
        if kind == 'self':
            st.open_direct(st.me)
            return None, None, '나와의 채팅방을 만드는 중입니다.'
        if kind == 'bot':
            st.open_direct(BOT_NAME)
            return None, None, 'AI 비서와의 채팅방을 여는 중입니다.'
        if kind == 'open':
            self.do_open_chat()
            return None, None, '오픈채팅방이 없어 오픈채팅 찾기를 열었습니다.'
        friend = self._first_friend()
        if friend is None:
            return None, None, '대화할 친구가 없습니다. 다른 사용자로도 접속해 보세요.'
        if kind == 'secret':
            st.open_secret(friend['username'])
            return None, None, f"{st.display_name(friend['username'])}님과 비밀채팅방을 여는 중입니다."
        if kind == 'direct':
            st.open_direct(friend['username'])
            return None, None, f"{st.display_name(friend['username'])}님과의 1:1 채팅을 여는 중입니다."
        self.do_create_group()
        return None, None, '그룹 채팅방이 없어 대화상대 선택 창을 열었습니다. 2명 이상 골라 방을 만드세요.'

    # ---- 동작들 (do_<이름>) : 안내문을 돌려준다
    def do_tab(self, key, note=''):
        fn = self._mw('set_tab')
        if fn is None:
            return note or '메인 창이 없어 탭을 열 수 없습니다.'
        fn(key)
        label = {'friends': '친구', 'chats': '채팅', 'org': '조직도', 'calendar': '캘린더', 'more': '더보기'}.get(key, key)
        return f"{label} 탭을 열었습니다." + (f" {note}" if note else '')

    def do_tab_call(self, key, method, *args):
        msg = self.do_tab(key)
        tab = self._tab_widget(key)
        if tab is not None and callable(getattr(tab, method, None)):
            self._defer(lambda: getattr(tab, method)(*args))
        return msg

    def do_room(self, kind, note=''):
        _win, _rid, msg = self._open_kind(kind)
        return msg + (f" {note}" if note else '')

    def do_room_call(self, kind, methods, hint, fallback=None):
        win, rid, msg = self._open_kind(kind)
        if rid is None:
            return msg
        for name in methods:
            if win is not None and callable(getattr(win, name, None)):
                self._defer(lambda w=win, n=name: getattr(w, n)())
                return f'{msg} (메뉴 위치: {hint})'
        if fallback is not None:
            cls = _lazy(*fallback)
            if cls is not None:
                dlg = _construct(cls, self._values(win=win, window=win, room_window=win, room_id=rid))
                if dlg is not None:
                    self._show_dialog(dlg)
                    return f'{msg} (메뉴 위치: {hint})'
        return f"{msg} 사용법: {hint}"

    def do_room_msg(self, kind, method, which):
        """방을 열고 메시지에 대해 작성창 동작 시작 (답장/수정)"""
        win, rid, msg = self._open_kind(kind)
        if rid is None:
            return msg
        st = self.state

        def pick():
            msgs = [m for m in st.room_messages(rid) if m.get('kind') == 'text' and not m.get('deleted')]
            if which == 'mine':
                msgs = [m for m in msgs if st.can_edit(m)]
            else:
                msgs = [m for m in msgs if m.get('sender') not in ('', st.me)]
            return msgs[-1] if msgs else None

        def run():
            m = pick()
            if m is None:
                self.explain(msg + (' 최근 24시간 안에 내가 보낸 텍스트가 없어 수정할 메시지가 없습니다. 메시지를 보낸 뒤 우클릭 → 수정.'
                                    if which == 'mine' else ' 답장할 메시지가 없습니다. 말풍선을 우클릭 → 답장.'))
            elif win is not None and callable(getattr(win, method, None)):
                getattr(win, method)(m)
        self._defer(run, 300)   # 히스토리를 받을 시간을 준다
        return msg + (' 내 마지막 메시지로 수정을 시작합니다.' if which == 'mine' else ' 마지막 메시지에 답장을 시작합니다.')

    def do_call(self, kind, mode):
        from client.kakao.state import CALL_MODE_LABELS as names
        win, rid, msg = self._open_kind(kind)
        if rid is None:
            return msg
        call = self.state.call_for_room(rid) if hasattr(self.state, 'call_for_room') else None
        show_call = getattr(_lazy_module('call'), 'show_call', None)
        if call is not None:
            if show_call is not None:
                _construct(show_call, self._values(call_id=call['call_id']))
            return f"{msg} 이미 진행 중인 통화가 있어 통화 창을 엽니다."
        for name in (f'start_{mode}_call', 'start_call'):
            fn = getattr(win, name, None) if win is not None else None
            if callable(fn):
                self._defer(lambda f=fn, n=name: f(mode) if n == 'start_call' else f())
                return f"{msg} {names[mode]}을 시작합니다."
        if show_call is not None:
            self.state.start_call(rid, mode)
            return f"{msg} {names[mode]}을 시작했습니다. 통화 창이 곧 열립니다."
        return f"{msg} 채팅방 상단의 통화 버튼으로 {names[mode]}을 시작하세요."

    def do_create_group(self):
        from client.kakao.chats_tab import CreateGroupDialog
        self._show_dialog(CreateGroupDialog(self.state, self._parent_widget()))
        return '대화상대를 2명 이상 고르면 그룹 채팅방이 만들어집니다.'

    def do_folder(self):
        from client.kakao.chats_tab import ChatFolderDialog
        self.do_tab('chats')
        self._show_dialog(ChatFolderDialog(self.state, None, self._parent_widget()))
        return '폴더 이름과 넣을 채팅방을 고르세요. 채팅 탭 위쪽 칩으로 폴더를 오갑니다.'

    def do_call_folder(self):
        self.do_tab('chats')
        tab = self._tab_widget('chats')
        if tab is not None and callable(getattr(tab, 'select_folder', None)):
            tab.select_folder('통화')
        missed = self.state.missed_call_count() if hasattr(self.state, 'missed_call_count') else 0
        return "채팅 탭의 '통화' 폴더를 열었습니다." + (f' 부재중 통화 {missed}건이 있습니다.' if missed else '')

    def do_peek(self):
        rid = next((r['room_id'] for r in self.state.sorted_rooms() if self.state.room_unread(r['room_id'])), None)
        if rid is None:
            self.do_tab('chats')
            return '지금은 안 읽은 채팅방이 없습니다. 새 메시지가 오면 채팅방을 우클릭 → 읽지 않고 미리보기.'
        from client.kakao.chats_tab import PeekDialog
        self._show_dialog(PeekDialog(self.state, rid, self._parent_widget()))
        return f"'{self.state.room_title(rid)}'의 안 읽은 메시지를 읽음 처리 없이 보여 줍니다."

    def do_open_chat(self):
        from client.kakao.chats_tab import OpenChatDialog
        self._show_dialog(OpenChatDialog(self.state, self._parent_widget()))
        return '오픈채팅방을 검색해 닉네임으로 참여하거나 \'만들기\' 탭에서 새 방을 여세요.'

    def do_talk_drawer(self, note=''):
        from client.kakao.drawer import TalkDrawerDialog
        self._show_dialog(TalkDrawerDialog(self.state, self._parent_widget(), main_window=self.main_window))
        return '모든 채팅방의 사진·파일·링크를 모았습니다. 더블클릭하면 그 채팅방의 메시지로 이동합니다.' + (
            f' {note}' if note else '')

    def do_profile_edit(self):
        from client.kakao.friends_tab import ProfileEditDialog
        self.do_tab('friends')
        self._show_dialog(ProfileEditDialog(self.state, self._parent_widget()))
        return '사진·이름·상태메시지를 바꾸고 저장하면 모두에게 반영됩니다.'

    def do_profile_view(self):
        friend = self._first_friend()
        if friend is None:
            return self.do_tab('friends')
        from client.kakao.friends_tab import ProfileDialog
        self._show_dialog(ProfileDialog(self.state, friend['username'], self._parent_widget()))
        return f"{self.state.display_name(friend['username'])}님의 프로필입니다. 1:1 채팅 버튼으로 바로 대화합니다."

    def do_presence(self):
        from client.kakao.friends_tab import presence_menu
        from PyQt5.QtGui import QCursor
        self.do_tab('friends')
        menu = presence_menu(self.state, self._parent_widget())
        self.opened.append(menu)
        menu.popup(QCursor.pos())
        return '상태를 고르면 친구들에게 색 점으로 보입니다. 10분간 입력이 없으면 자동으로 자리비움이 됩니다.'

    def do_story_view(self):
        owners = [u for u in self.state.story_owners() if u != self.state.me] if hasattr(self.state, 'story_owners') else []
        cls = _lazy('story', 'StoryViewer')
        if owners and cls is not None:
            dlg = _construct(cls, self._values(username=owners[0], owner=owners[0]))
            if dlg is not None:
                self._show_dialog(dlg)
                return f"{self.state.display_name(owners[0])}님의 펑을 봅니다."
        self.do_tab('friends')
        return '친구 탭 위쪽 펑 줄에서 친구 사진을 누르세요.' + ('' if owners else ' 지금은 올라온 펑이 없습니다.')

    def do_ext_dialog(self, module, name, hint):
        cls = _lazy(module, name)
        if cls is not None:
            dlg = _construct(cls, self._values())
            if dlg is not None:
                self._show_dialog(dlg)
                return f'화면을 열었습니다. 다음부터는 {hint}'
        return f'사용법: {hint}'

    def do_lock(self):
        has_pin = bool(self.settings is not None and self.settings.get('lock_pin_hash'))
        lock = self._mw('lock')
        if has_pin and lock is not None:
            self._defer(lock)
            return '잠금모드로 전환합니다. PIN 4자리로 풀 수 있습니다.'
        msg = self.do_ext_dialog('more_tab', 'LockSettingsDialog', '더보기 → 잠금모드')
        return msg + ('' if has_pin else ' 먼저 PIN을 정해야 잠글 수 있습니다.')

    def do_wallpaper(self):
        from client.kakao.wallpaper import WallpaperDialog
        self._show_dialog(WallpaperDialog(self.settings, None, self._parent_widget()))
        return '기본 배경화면을 고릅니다. 방별 배경은 채팅방 메뉴 → 배경화면에서 정합니다.'

    def do_rag_docs(self):
        from client.kakao.more_tab import RagDocsDialog
        self._show_dialog(RagDocsDialog(self.state, self._parent_widget()))
        return 'AI 비서가 참고할 문서를 올리거나 지웁니다.'

    def do_org_dock(self):
        msg = self.do_tab('chats')
        mw = self.main_window
        if isinstance(mw, QWidget) and mw.width() < 860:
            mw.resize(900, max(mw.height(), 680))
            return '창을 넓혀 왼쪽에 조직도 패널을 펼쳤습니다.'
        return msg + ' 창 폭이 860px 이상이면 왼쪽에 조직도가 펼쳐집니다.'

    def do_toggle_setting(self, key):
        if self.settings is None:
            return '설정을 바꿀 수 없습니다.'
        value = not bool(self.settings.get(key))
        self.settings.set(key, value)
        self.apply_theme()
        return f"{'다크 모드를 켰습니다' if value else '다크 모드를 껐습니다'}. 한 번 더 누르면 되돌립니다."

    def do_toggle_brand(self):
        if self.settings is None:
            return '설정을 바꿀 수 없습니다.'
        value = not bool(self.settings.get('social_features'))
        self.settings.set('social_features', value)
        self.apply_theme()
        return f"{'소식 기능(펑·생일·선물하기)을 켰습니다' if value else '소식 기능을 껐습니다'}. 한 번 더 누르면 되돌립니다."

    def do_verification(self):
        self.tabs.setCurrentIndex(1)
        return '검증 결과 탭입니다. python3 scripts/verify_features.py 로 갱신하고, python3 scripts/demo.py 로 데모를 실행합니다.'

    def done(self, result):
        for d in self.opened:
            if _alive(d) and hasattr(d, 'close'):
                try:
                    d.close()
                except RuntimeError:
                    pass
        self.opened = []
        super().done(result)


# ================================================================ 지연 import 헬퍼
def _alive(obj):
    try:
        obj.objectName()
        return True
    except RuntimeError:
        return False


def _lazy_module(module):
    try:
        return importlib.import_module(f'client.kakao.{module}')
    except Exception:
        return None


def _lazy(module, name):
    mod = _lazy_module(module)
    return getattr(mod, name, None) if mod is not None else None


def _construct(cls, values):
    """다른 모듈의 다이얼로그를 생성자 매개변수 이름(state/settings/parent/username/room_id/win…)에 맞춰 만든다.
    필요한 값이 없거나 생성에 실패하면 None"""
    import inspect
    try:
        params = list(inspect.signature(cls).parameters.values())
    except (TypeError, ValueError):
        return None
    args = []
    for p in params:
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            continue
        if p.name in values and values[p.name] is not None:
            args.append(values[p.name])
        elif p.default is p.empty:
            return None
        else:
            break
    try:
        return cls(*args)
    except Exception:
        return None


__all__ = ['FeatureTourDialog', 'FEATURES', 'FEATURE_KEYS', 'FEATURE_NAMES', 'GROUPS', 'load_verification',
           'VERIFICATION_PATH']
