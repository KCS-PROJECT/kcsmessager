# -*- coding: utf-8 -*-
"""LocalSettings 저장: 안전한 파일 이름 · 원자적 저장 · 깨진 파일 보관 · 키 단위 병합 · 계정→사용자 이름 전환"""

import json
import os
import shutil
import tempfile
import unittest

from tests.kakao_fakes import app  # noqa: F401  (sys.path 설정)
from client.kakao.settings import LocalSettings, settings_file_name


class SettingsStoreTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='kcs_settings_')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_file_name_cannot_escape_directory(self):
        self.assertEqual(settings_file_name('김명수'), '김명수.json')
        for bad in ('../../x', 'a:b', 'a/b', '..', 'a\\b'):
            name = settings_file_name(bad)
            self.assertNotIn('/', name)
            self.assertNotIn('\\', name)
            self.assertFalse(name.startswith('.'))
        s = LocalSettings('../../escape', base_dir=self.dir)
        self.assertTrue(s.set('dark_mode', True))
        self.assertEqual(os.path.dirname(s.path), self.dir)

    def test_corrupt_file_is_kept_as_backup(self):
        path = os.path.join(self.dir, '홍길동.json')
        with open(path, 'w', encoding='utf-8') as f:
            f.write('{"lock_pin_hash": "abc", ')            # 쓰다 만 JSON
        s = LocalSettings('홍길동', base_dir=self.dir)
        self.assertTrue(os.path.exists(path + '.bak'))
        s.set('dark_mode', True)
        with open(path + '.bak', encoding='utf-8') as f:
            self.assertIn('lock_pin_hash', f.read())       # 원본은 덮어쓰지 않았다
        self.assertFalse(os.path.exists(path + '.tmp'))

    def test_two_instances_do_not_revert_each_other(self):
        a = LocalSettings('홍길동', base_dir=self.dir)
        b = LocalSettings('홍길동', base_dir=self.dir)
        a.set('dark_mode', True)
        b.set('font_scale', 1.2)
        with open(a.path, encoding='utf-8') as f:
            data = json.load(f)
        self.assertEqual((data['dark_mode'], data['font_scale']), (True, 1.2))

    def test_use_user_switches_to_resolved_username(self):
        user = LocalSettings('김명수', base_dir=self.dir)
        user.set('lock_pin_hash', 'pinhash')
        by_account = LocalSettings('kmkim', base_dir=self.dir)
        self.assertEqual(by_account.get('lock_pin_hash'), '')
        by_account.use_user('김명수')                         # welcome 의 실제 사용자 이름
        self.assertEqual(by_account.get('lock_pin_hash'), 'pinhash')
        by_account.set('dark_mode', True)
        self.assertEqual(LocalSettings('김명수', base_dir=self.dir).get('dark_mode'), True)


if __name__ == '__main__':
    unittest.main()
