#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
회사 연락처/조직도 엑셀 → KCS Talk 서버 조직 파일(server_data/org.json, v2) 변환

    python3 scripts/import_org_xlsx.py "~/Downloads/연락처 및 조직도(20260901).xlsx"
    python3 scripts/import_org_xlsx.py 조직도.xlsx --company 케이씨에스 --out server_data/org.json

엑셀 형식('사내전화번호' 시트): 5열 블록(직급 | 이름 | 계정 | 내선 | 휴대폰)이 가로로 여러 개 있고,
블록 안에서 값이 첫 칸에만 있는 행은 조직 단위 제목이다(예: '영 업 부(t-sales)', '영업 1 본부(t-sale1)', '1팀(보안)').
이름·직급의 '(*)'는 겸직 표시다. 같은 계정이 여러 조직에 나오면 겸직이 아닌 곳을 주소속으로 하고,
나머지 조직은 모두 겸직으로 둔다(같은 부서의 다른 팀도 각각). 엑셀은 본부장·실장 같은 부서장을
첫 팀 블록 안에 적으므로, 부서장 직함이 팀 안에 있으면 부서 바로 아래(부서장 자리)와 그 팀 두 곳에 둔다.

org.json 에는 개인 연락처가 들어가므로 저장소에 커밋하지 않는다(server_data/ 는 .gitignore 대상).
계열사 목록은 한국지주 사업보고서(DART) '계열회사 현황' 13곳 기준이며 --affiliates 로 바꿀 수 있다.
"""

import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 그룹 구조: 한국지주(주) 2025 사업보고서(DART rcpNo 20260331001700, 2025-12-31 기준) '계열회사 현황' 13곳
# (상장 5 · 비상장 8, 지주사 자신은 목록에 없음). 연락처는 DART 기업정보 기준(그룹 홈페이지 계열사 안내는 오래됨),
# 비상장사는 확인된 사실(상장 여부 · 지분 관계)만 적는다 - 확인되지 않은 홈페이지·전화는 넣지 않는다.
HOLDING = {'name': '한국지주', 'business': '지주회사업', 'homepage': 'www.kchi.co.kr', 'phone': '02-398-1712'}
AFFILIATES = [
    # 상장 (코스닥)
    {'name': '한국컴퓨터', 'business': 'LCD 모듈·PDP 부품 · 코스닥', 'homepage': 'www.kci.co.kr', 'phone': '041-589-3320'},
    {'name': '한네트', 'business': '점외 CD/ATM 현금서비스 VAN · 코스닥', 'homepage': 'www.hannet.net', 'phone': '02-2125-6000'},
    {'name': '로지시스', 'business': '금융단말 유지보수·CD/ATM 운영대행 · 코스닥', 'homepage': 'www.logisys.co.kr',
     'phone': '02-2125-6300'},
    {'name': '케이씨티', 'business': '금융자동화 시스템 공급 사업 · 코스닥', 'homepage': 'www.kctinc.co.kr',
     'phone': '02-6377-5622'},
    {'name': '케이씨에스', 'business': '시스템 통합·정보보호·양자암호 솔루션', 'homepage': 'kcins.co.kr', 'phone': '02-6377-5001'},
    # 비상장 (국내)
    {'name': '한국문학사', 'business': '비상장 · 한국지주 100%'},
    {'name': '한국상역개발', 'business': '비상장 · 한국지주 40.03%'},
    {'name': '상화원', 'business': '비상장', 'homepage': 'www.sanghwawon.com'},
    {'name': '제주상화원', 'business': '비상장'},
    {'name': '한상개발', 'business': '비상장'},
    {'name': '상화공익', 'business': '비상장'},
    # 해외 현지법인 (한국컴퓨터 100% 자회사)
    {'name': 'KCI VINA', 'business': '해외 현지법인 (베트남) · 한국컴퓨터 100%'},
    {'name': 'Pacom International', 'business': '해외 현지법인 · 한국컴퓨터 100%'},
]

# 사내 그룹웨어 조직도 화면과 같은 부서 체계 (부서 1단계, 팀은 프로필에만)
# 조직도 탭에서는 그룹사(지주사) 아래 계열사 자리에 '케이씨에스' 한 단계로 표시한다 (법인명 단계 없음)
GROUPWARE_GROUP = '케이씨에스'           # 회사 이름
GROUPWARE_DEPTS = ['관리팀', '마케팅팀', '신사업팀', 'MICE사업팀', '영업1부', '영업2부', '영업3부',
                   '기술연구소1실', '기술연구소2실', '기술연구소3실']
GROUPWARE_ROOT_MEMBERS = ['김광묵', 'KCS관리자']   # 부서 없이 회사 바로 아래 표시
# 사내 그룹웨어 조직도(2026-10 화면) 기준 보정 - 엑셀(2026-09-01)과 다른 소속
# 그룹웨어 화면 숫자: 관리팀 5, 마케팅팀 3, 신사업팀 3, MICE사업팀 2, 영업1부 2, 영업2부 4, 영업3부 5,
# 기술연구소1실 8, 2실 13, 3실 10, 전체 52명. 엑셀 그대로면 관리팀 4 · MICE사업팀 3 으로 한 명씩 다르지만,
# 화면에는 숫자만 있어 MICE사업팀의 누구(정민정·김가연·류병두)가 관리팀으로 갔는지 알 수 없으므로 보정하지 않는다
# (예전에 근거 없이 류병두를 관리팀으로 옮겼던 보정은 2026-10-09 삭제 - 엑셀 두 버전 모두 MICE 사업팀).
# 실제 이동한 사람이 확인되면 여기에 {'이름': {'dept': '관리팀'}} 를 추가한다.
GROUPWARE_OVERRIDES = {
    '엄태식': {'dept': '신사업팀', 'keep_old': True},               # 주소속 신사업팀, 연구1실(실장·1팀·AI/AX)은 겸직으로
}
# 엑셀 조직 이름 → 실제 쓰는 이름 (엑셀은 예전 이름 그대로인 곳). 단계 판정(unit_level) 뒤에 바꾼다
UNIT_RENAMES = {
    '2팀(SI)': 'AI/AX 솔루션사업팀',          # 기술연구소 연구1실 (2026-10 변경)
}
# 부서장 직함: 엑셀에서 팀 블록 안에 있어도 부서(본부·실) 바로 아래에도 둔다 (부서장 + 팀 겸직)
HEAD_TITLES = ('본부장', '실장', '상무이사', '상무', '전무', '이사')

# 관리자 계정: 다른 사람의 조직도에는 숨기고(hidden_members), 관리자 본인으로 로그인하면 전체가 보인다
ADMIN_ACCOUNT = {'username': 'KCS관리자', 'title': '', 'account': 'kcs_administrator', 'extension': '', 'mobile': ''}

BLOCK = 5            # 직급 | 이름 | 계정 | 내선 | 휴대폰
MAX_BLOCKS = 3       # A-E, F-J, K-O (P열 이후는 팩스·출입문 등 부가 정보)
CONCURRENT = '(*)'


def clean_unit(text):
    """'영 업 부(t-sales)' → '영업부', '연구1실 (t-research1)' → '연구1실', '1팀(보안)' → '1팀(보안)'"""
    text = re.sub(r'\((?:t-[^)]*|-|event)\)', '', str(text)).strip()
    text = re.sub(r'\s+', ' ', text)
    # 글자 사이를 띄운 표기('임 원 실', '영 업 부')는 붙인다
    if re.fullmatch(r'(?:\S )+\S', text) and all(len(t) == 1 for t in text.split(' ')):
        text = text.replace(' ', '')
    text = re.sub(r'(\S)\s+(\d+)\s+(본부|실)', r'\1\2\3', text)   # '영업 1 본부' → '영업1본부'
    return text.replace(' (', '(').strip()


def unit_level(name):
    """조직 단위 깊이: 1=부/연구소/독립 팀, 2=본부/실, 3=하위 팀"""
    if re.search(r'(본부|\d실)$', name):
        return 2
    if re.match(r'^\d+팀', name):
        return 3
    return 1


def clean_phone(value):
    if value in (None, '-', ''):
        return ''
    return str(value).replace('ㆍ', '-').replace('·', '-').strip()


def parse_sheet(ws):
    """→ (entries, units)
    entries: [{'name','title','account','extension','mobile','path':[...],'concurrent':bool}]
    units: 조직도 읽는 순서(블록 왼쪽→오른쪽, 위→아래)의 조직 경로 목록"""
    entries, units = [], []
    stacks = [[] for _ in range(MAX_BLOCKS)]   # 블록별 현재 조직 경로 [(level, name)]
    last_top = [None] * MAX_BLOCKS              # 블록별 마지막 1단계 조직 (row, name)
    for r in range(1, ws.max_row + 1):
        for b in range(MAX_BLOCKS):
            cells = [ws.cell(r, b * BLOCK + i + 1).value for i in range(BLOCK)]
            first = cells[0]
            rest = [v for v in cells[1:] if v not in (None, '')]
            if first in (None, '') and not rest:
                continue
            if isinstance(first, str) and (first.strip().startswith('※') or ':' in first):
                continue  # 안내문·대표전화·주소 줄
            if first not in (None, '') and not rest:
                # 조직 단위 제목
                name = clean_unit(first)
                level = unit_level(name)          # '2팀(SI)' → 팀 단계로 판정한 뒤
                name = UNIT_RENAMES.get(name, name)   # 지금 쓰는 이름으로
                stack = stacks[b]
                while stack and stack[-1][0] >= level:
                    stack.pop()
                if level > 1 and (not stack or stack[0][0] != 1 or self_top_older(last_top, b, r)):
                    # 상위(1단계) 조직 제목이 왼쪽 블록에 걸쳐 있는 경우(예: 기술연구소 → 연구2실):
                    # 지금 행에서 가장 가까운(행 번호가 가장 큰) 1단계 제목을 부모로 삼는다
                    # (행, 블록) 순으로 비교 → 같은 행이면 바로 왼쪽 블록이 우선
                    candidates = [(last_top[k][0], k, last_top[k][1]) for k in range(b + 1) if last_top[k]]
                    if candidates:
                        row, _k, parent = max(candidates)
                        stack.clear()
                        stack.append((1, parent))
                        last_top[b] = (r, parent)
                stack.append((level, name))
                if level == 1:
                    last_top[b] = (r, name)
                units.append((b, r, [n for _, n in stack]))
                continue
            if len(rest) < 2 or not stacks[b]:
                continue
            title, person, account, ext, mobile = (cells + [None] * BLOCK)[:BLOCK]
            if not person:
                continue
            title, person = str(title or '').strip(), str(person).strip()
            concurrent = CONCURRENT in title or CONCURRENT in person
            entries.append({
                'name': person.replace(CONCURRENT, '').strip(),
                'title': title.replace(CONCURRENT, '').strip(),
                'account': str(account or '').strip(),
                'extension': '' if ext in (None, '-') else str(ext).strip(),
                'mobile': clean_phone(mobile),
                'path': [n for _, n in stacks[b]],
                'concurrent': concurrent,
            })
    units.sort(key=lambda u: (u[0], u[1]))
    return entries, [u[2] for u in units]


def self_top_older(last_top, b, r):
    """현재 블록의 1단계 제목보다 왼쪽 블록의 1단계 제목이 더 최근(아래쪽)이면 True"""
    mine = last_top[b]
    others = [last_top[k] for k in range(b) if last_top[k]]
    return bool(mine and others and max(others)[0] > mine[0])


def _natural(name):
    m = re.match(r'^\D*?(\d+)', name)
    return (int(m.group(1)) if m else 0, name)


def order_units(units):
    """1단계는 조직도 순서 그대로, 그 아래(본부·실·팀)는 번호 순으로 정렬한 전체 경로 목록(상위 경로 포함)"""
    first_seen, children = {}, {}
    for path in units:
        for depth in range(1, len(path) + 1):
            node = tuple(path[:depth])
            if node not in first_seen:
                first_seen[node] = len(first_seen)
                children.setdefault(node[:-1], []).append(node)
    ordered = []

    def walk(parent):
        kids = children.get(parent, [])
        if parent:
            kids = sorted(kids, key=lambda n: _natural(n[-1]))
        for node in kids:
            ordered.append(list(node))
            walk(node)
    walk(())
    return ordered


def build_users(entries, company):
    """계정별로 묶어 주소속 + 겸직 목록 생성. 동명이인은 '이름(계정)'으로 구분"""
    by_account, order = {}, []
    for e in entries:
        key = e['account'] or e['name']
        if key not in by_account:
            by_account[key] = {'primary': None, 'others': [], 'info': e}
            order.append(key)
        slot = by_account[key]
        if not e['concurrent'] and slot['primary'] is None:
            slot['primary'] = e
        else:
            slot['others'].append(e)
    names = {}
    for key in order:
        names.setdefault(by_account[key]['info']['name'], []).append(key)
    users = []
    for key in order:
        slot = by_account[key]
        primary = slot['primary'] or slot['others'].pop(0)
        name = primary['name']
        username = name if len(names[name]) == 1 else f'{name}({key})'
        seen = {tuple(primary['path'])}
        concurrent = []
        for e in slot['others']:
            if tuple(e['path']) not in seen:
                seen.add(tuple(e['path']))
                concurrent.append({'org_path': e['path'], 'title': e['title']})
        users.append({
            'username': username, 'company': company,
            'department': primary['path'][-1], 'org_path': primary['path'], 'title': primary['title'],
            'account': primary['account'], 'extension': primary['extension'], 'mobile': primary['mobile'],
            'concurrent': concurrent,
        })
    return users


def to_groupware_path(path):
    """엑셀 조직 경로 → 그룹웨어 부서 경로 [부서, (팀)]
    임원실 → [] (회사 바로 아래), 영업부›영업1본부›1팀(보안) → [영업1부, 1팀(보안)],
    기술연구소›연구1실›2팀(SI) → [기술연구소1실, 2팀(SI)], 'MICE 사업팀' → 'MICE사업팀'"""
    path = list(path)
    if not path or path[0] == '임원실':
        return []
    if path[0] == '영업부' and len(path) > 1:
        m = re.match(r'영업(\d+)본부', path[1])
        return [f'영업{m.group(1)}부' if m else path[1]] + path[2:]
    if path[0] == '기술연구소' and len(path) > 1:
        m = re.match(r'연구(\d+)실', path[1])
        return [f'기술연구소{m.group(1)}실' if m else path[1]] + path[2:]
    return [path[0].replace(' ', '')] + path[1:]


def place_department_heads(user):
    """부서장 직함이 팀 안에 있으면 부서 바로 아래에도 둔다: 주소속은 [부서](부서장), 팀은 겸직.
    겸직 목록은 주소속과 경로가 다른 것만, 경로마다 한 번씩 (같은 부서의 다른 팀은 각각 남는다)"""
    placements = [(list(user['org_path']), user['title'])] + [(list(c['org_path']), c['title'])
                                                             for c in user['concurrent']]
    expanded = []
    for path, title in placements:
        if title in HEAD_TITLES and len(path) >= 2:
            expanded.append((path[:1], title))
        expanded.append((path, title))
    primary_path, primary_title = expanded[0]
    seen, concurrent = {tuple(primary_path)}, []
    for path, title in expanded[1:]:
        if path and tuple(path) not in seen:
            seen.add(tuple(path))
            concurrent.append({'org_path': path, 'title': title})
    user['org_path'], user['title'] = primary_path, primary_title
    user['department'] = primary_path[0] if primary_path else ''
    user['concurrent'] = concurrent


def apply_groupware_layout(users):
    """사용자 조직 경로를 그룹웨어 체계로 바꾸고 관리자 계정을 더한다"""
    out = []
    for u in users:
        u = dict(u)
        u['org_path'] = to_groupware_path(u['org_path'])
        u['department'] = u['org_path'][0] if u['org_path'] else ''
        u['concurrent'] = [dict(c, org_path=to_groupware_path(c['org_path'])) for c in u['concurrent']]
        out.append(u)
    for u in out:
        fix = GROUPWARE_OVERRIDES.get(u['username'])
        if not fix:
            continue
        if fix.get('dept') and (u['org_path'][:1] != [fix['dept']]):
            if fix.get('keep_old') and u['org_path']:      # 옮기기 전 소속은 겸직으로 남긴다
                u['concurrent'] = [{'org_path': u['org_path'], 'title': u['title']}] + u['concurrent']
            team = u['org_path'][1:] if u['org_path'][:1] == [fix['dept']] else []
            u['org_path'] = [fix['dept']] + team
            u['department'] = fix['dept']
    for u in out:
        place_department_heads(u)
    if not any(u['username'] == ADMIN_ACCOUNT['username'] for u in out):
        company = out[0]['company'] if out else '케이씨에스'
        out.append(dict(ADMIN_ACCOUNT, company=company, department='', org_path=[], concurrent=[]))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description='연락처·조직도 엑셀 → server_data/org.json')
    ap.add_argument('xlsx')
    ap.add_argument('--company', default='케이씨에스', help='엑셀 구성원의 소속 계열사 이름')
    ap.add_argument('--sheet', default=None, help='시트 이름 (기본: 첫 시트)')
    ap.add_argument('--out', default=os.path.join(ROOT, 'server_data', 'org.json'))
    ap.add_argument('--layout', choices=['groupware', 'raw'], default='groupware',
                    help='groupware: 사내 그룹웨어 조직도와 같은 부서 1단계(기본) / raw: 엑셀 그대로 부›본부›팀')
    ap.add_argument('--affiliates', default=None,
                    help='계열사 이름을 쉼표로 (기본: 홈페이지 기준 한국컴퓨터,한네트,로지시스,케이씨티,케이씨에스)')
    args = ap.parse_args(argv)

    import warnings
    warnings.filterwarnings('ignore', category=UserWarning)  # wmf 이미지 경고
    import openpyxl
    wb = openpyxl.load_workbook(os.path.expanduser(args.xlsx), data_only=True)
    ws = wb[args.sheet] if args.sheet else wb.worksheets[0]
    entries, units = parse_sheet(ws)
    users = build_users(entries, args.company)
    unit_order = order_units(units)
    if args.layout == 'groupware':
        users = apply_groupware_layout(users)
        unit_order = [[d] for d in GROUPWARE_DEPTS]

    affiliates = [dict(a) for a in AFFILIATES]
    if args.affiliates:
        known = {a['name']: a for a in AFFILIATES}
        affiliates = [known.get(n.strip(), {'name': n.strip()}) for n in args.affiliates.split(',') if n.strip()]
    for a in affiliates:
        if a['name'] == args.company:
            a['units'] = unit_order
            if args.layout == 'groupware':
                a.update({'group_name': GROUPWARE_GROUP, 'depth': 1,
                          'root_members': GROUPWARE_ROOT_MEMBERS,
                          'hidden_members': [ADMIN_ACCOUNT['username']],
                          'count_excludes_root': True})   # 회사 인원 = 부서 소속 인원 (그룹웨어와 같게)
    org = {'version': 2, 'holding': HOLDING, 'companies': affiliates,
           'include_demo_users': False, 'admins': [ADMIN_ACCOUNT['username']], 'users': users}   # 관리자 권한 (명세 §4.2)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, 'w', encoding='utf-8') as f:
        json.dump(org, f, ensure_ascii=False, indent=2)
    concurrent = sum(len(u['concurrent']) for u in users)
    print(f'{args.out}: {args.company} 구성원 {len(users)}명, 조직 {len(unit_order)}개, 겸직 {concurrent}건, '
          f'계열사 {len(affiliates)}곳 (지주사 {HOLDING["name"]})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
