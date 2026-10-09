# -*- coding: utf-8 -*-
"""사내 그룹웨어와 같은 조직도 구성 (케이씨에스 › 주식회사케이씨에스 › 직속 구성원 + 부서 10개)"""

import os
import sys
import unittest

from tests.kakao_fakes import make_demo_state, app

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'scripts'))
import import_org_xlsx as imp  # noqa: E402

from client.kakao.org_tab import OrgTab, MembersDialog, CompactMemberRow  # noqa: E402


def rows(lst):
    return [lst.item(i).data(0x0100) for i in range(lst.count())]


class GroupwarePathTest(unittest.TestCase):
    def test_flatten_to_departments(self):
        f = imp.to_groupware_path
        self.assertEqual(f(['임원실']), [])
        self.assertEqual(f(['관리팀']), ['관리팀'])
        self.assertEqual(f(['MICE 사업팀']), ['MICE사업팀'])
        self.assertEqual(f(['영업부', '영업1본부', '1팀(보안)']), ['영업1부', '1팀(보안)'])
        self.assertEqual(f(['기술연구소', '연구2실', '3팀(DB)']), ['기술연구소2실', '3팀(DB)'])

    def test_layout_adds_admin_and_dedupes_concurrent(self):
        users = [{'username': '테스트임원', 'company': '케이씨에스', 'department': '1팀(Oracle)', 'title': '상무이사',
                  'org_path': ['영업부', '영업3본부', '1팀(Oracle)'], 'account': 'smyoon', 'extension': '5142',
                  'mobile': '', 'concurrent': [{'org_path': ['기술연구소', '연구2실', '1팀(Oracle)'], 'title': '상무이사'},
                                               {'org_path': ['기술연구소', '연구2실', '3팀(DB)'], 'title': '상무이사'}]}]
        out = imp.apply_groupware_layout(users)
        ys = out[0]
        self.assertEqual(ys['org_path'][0], '영업3부')
        self.assertEqual([c['org_path'][0] for c in ys['concurrent']], ['기술연구소2실'])   # 같은 실 두 팀 → 한 번
        self.assertEqual(out[-1]['username'], 'KCS관리자')
        self.assertEqual(out[-1]['org_path'], [])

    def test_department_order_matches_groupware(self):
        self.assertEqual(imp.GROUPWARE_DEPTS, ['관리팀', '마케팅팀', '신사업팀', 'MICE사업팀', '영업1부', '영업2부',
                                               '영업3부', '기술연구소1실', '기술연구소2실', '기술연구소3실'])


IMAGE_COUNTS = {'관리팀': 5, '마케팅팀': 3, '신사업팀': 3, 'MICE사업팀': 2, '영업1부': 2, '영업2부': 4, '영업3부': 5,
                '기술연구소1실': 8, '기술연구소2실': 13, '기술연구소3실': 10}
XLSX = os.path.expanduser('~/Downloads/연락처 및 조직도(20260901).xlsx')


class GroupwareOverridesTest(unittest.TestCase):
    def test_overrides_move_and_drop(self):
        users = [
            {'username': '류병두', 'company': 'K', 'department': 'MICE 사업팀', 'title': '매니져',
             'org_path': ['MICE 사업팀'], 'account': 'rbd', 'extension': '', 'mobile': '', 'concurrent': []},
            {'username': '엄태식', 'company': 'K', 'department': '1팀(Tandem)', 'title': '실장',
             'org_path': ['기술연구소', '연구1실', '1팀(Tandem)'], 'account': 'tseom', 'extension': '', 'mobile': '',
             'concurrent': [{'org_path': ['신사업팀'], 'title': '실장'},
                            {'org_path': ['기술연구소', '연구1실', '2팀(SI)'], 'title': '실장'}]},
        ]
        out = {u['username']: u for u in imp.apply_groupware_layout(users)}
        self.assertEqual(out['류병두']['org_path'], ['관리팀'])
        self.assertEqual(out['엄태식']['org_path'][:1], ['신사업팀'])
        self.assertEqual(out['엄태식']['concurrent'], [])

    @unittest.skipUnless(os.path.isfile(XLSX), '원본 엑셀 없음')
    def test_real_excel_matches_groupware_image(self):
        """원본 엑셀을 변환하면 사내 그룹웨어 조직도 화면의 숫자(부서 10개 + 전체 52명)와 같아야 한다"""
        import warnings
        warnings.filterwarnings('ignore')
        import openpyxl
        from collections import Counter
        ws = openpyxl.load_workbook(XLSX, data_only=True).worksheets[0]
        entries, _units = imp.parse_sheet(ws)
        users = imp.apply_groupware_layout(imp.build_users(entries, '케이씨에스'))
        counts, in_depts = Counter(), set()
        for u in users:
            for path in [u['org_path']] + [c['org_path'] for c in u['concurrent']]:
                if path:
                    counts[path[0]] += 1
                    in_depts.add(u['username'])
        self.assertEqual(dict(counts), IMAGE_COUNTS)
        self.assertEqual(len(in_depts), 52)
        roots = [u['username'] for u in users if not u['org_path']]
        self.assertEqual(sorted(roots), sorted(['김광묵', 'KCS관리자']))


class GroupwareOrgTabTest(unittest.TestCase):
    def setUp(self):
        app()
        self.state, self.conn = make_demo_state()
        self.state.org = {'holding': {'name': '한국지주'},
                          'companies': [{'name': '한네트'},
                                        {'name': '케이씨에스', 'group_name': '케이씨에스', 'legal_name': '주식회사케이씨에스',
                                         'depth': 1, 'root_members': ['홍길동', 'KCS관리자'],
                                         'count_excludes_root': True,
                                         'units': [[d] for d in imp.GROUPWARE_DEPTS]}]}
        people = (('홍길동', [], '대표이사', []), ('김철수', ['관리팀'], '팀장', []),
                  ('이영희', ['기술연구소1실', '2팀(SI)'], '수석', [{'org_path': ['신사업팀'], 'title': '수석'}]),
                  ('박민수', ['영업1부', '1팀(보안)'], '부장', []))
        for name, path, title, extra in people:
            self.conn.push('user_updated', user=dict(self.state.user(name), company='케이씨에스', org_path=path,
                                                    department=path[0] if path else '', title=title,
                                                    concurrent=extra, extension='5100', account=name))
        self.tab = OrgTab(self.state, self.state.settings)

    def test_tree_shape_like_groupware(self):
        data = rows(self.tab.list)
        self.assertEqual(data[0], ('group', '케이씨에스'))
        self.assertEqual(data[1], ('company', '케이씨에스'))
        self.assertEqual(data[2], ('member', '홍길동'))                       # 회사 직속(대표이사) 먼저
        depts = [d[2][0] for d in data if d[0] == 'unit']
        self.assertEqual(depts, imp.GROUPWARE_DEPTS)                         # 10개 부서, 그룹웨어 순서
        self.assertNotIn(('member', '김철수'), data)                          # 부서는 처음에 접혀 있음
        self.assertIn(('holding', '한국지주'), data)                           # 계열사는 아래 '그룹사'
        names = self.tab.list.itemWidget(self.tab.list.item(1)).title.text()
        self.assertEqual(names, '주식회사케이씨에스')

    def test_expand_department_and_concurrent(self):
        item = self.tab.list.find_data(('unit', '케이씨에스', ('관리팀',)))
        self.tab.list.itemClicked.emit(item)
        self.assertIn(('member', '김철수'), rows(self.tab.list))
        row = self.tab.list.itemWidget(self.tab.list.find_data(('member', '김철수')))
        self.assertIsInstance(row, CompactMemberRow)
        self.assertEqual(row.name.text(), '김철수 팀장')
        self.tab.list.itemClicked.emit(self.tab.list.find_data(('unit', '케이씨에스', ('신사업팀',))))
        data = rows(self.tab.list)
        idx = data.index(('unit', '케이씨에스', ('신사업팀',)))
        self.assertEqual(data[idx + 1], ('member', '이영희'))                  # 겸직자도 그 부서에 표시

    def test_company_count_excludes_root_accounts(self):
        company = self.tab.list.itemWidget(self.tab.list.find_data(('company', '케이씨에스')))
        self.assertEqual(company.chip.count, 3)    # 김철수·이영희·박민수 (직속 홍길동 제외) - 그룹웨어 방식

    def test_count_chip_opens_member_list(self):
        node = self.tab.list.itemWidget(self.tab.list.find_data(('unit', '케이씨에스', ('기술연구소1실',))))
        self.assertEqual(node.chip.count, 1)
        dlg = self.tab.show_members('기술연구소1실', ['이영희'], exec_=False)
        self.assertIsInstance(dlg, MembersDialog)
        self.assertEqual(dlg.rows(), ['이영희'])
        dlg.search.setText('없는사람')
        self.assertEqual(dlg.rows(), [])

    def test_search_by_phone_or_id_expands(self):
        self.tab.search_edit.setText('박민수')
        data = rows(self.tab.list)
        self.assertIn(('member', '박민수'), data)
        self.assertEqual(self.tab.search_edit.placeholderText(), '이름, 직위, 직책, 직급, 부서, 전화, 아이디')


if __name__ == '__main__':
    unittest.main()
