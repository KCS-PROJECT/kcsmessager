# -*- coding: utf-8 -*-
"""배경화면 설정/렌더링 테스트"""

import os
import tempfile
import unittest

from tests.kakao_fakes import app
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QImage, QPainter, QColor

from client.kakao import theme
from client.kakao.settings import LocalSettings
from client.kakao.wallpaper import (resolve_wallpaper, paint_wallpaper, is_dark_wallpaper,
                                    WallpaperDialog)


def render(spec, w=40, h=40):
    img = QImage(w, h, QImage.Format_ARGB32)
    img.fill(QColor('black'))
    p = QPainter(img)
    paint_wallpaper(p, QRectF(0, 0, w, h), spec)
    p.end()
    return img


class WallpaperTest(unittest.TestCase):
    def setUp(self):
        app()
        theme.set_dark(False)
        self.dir = tempfile.mkdtemp()
        self.settings = LocalSettings('tester', base_dir=self.dir)

    def test_resolve_order(self):
        self.assertIsNone(resolve_wallpaper(self.settings, 'r1'))
        self.settings.set('chat_wallpaper', {'type': 'color', 'value': '#112233'})
        self.assertEqual(resolve_wallpaper(self.settings, 'r1')['value'], '#112233')
        self.settings.set('room_wallpapers', {'r1': {'type': 'color', 'value': '#445566'}})
        self.assertEqual(resolve_wallpaper(self.settings, 'r1')['value'], '#445566')
        self.assertEqual(resolve_wallpaper(self.settings, 'r2')['value'], '#112233')

    def test_paint_kinds(self):
        self.assertEqual(render(None).pixelColor(5, 5).name(), theme.c('chat_bg').lower())
        self.assertEqual(render({'type': 'color', 'value': '#ff0000'}).pixelColor(5, 5).name(), '#ff0000')
        grad = render({'type': 'gradient', 'value': ['#000000', '#ffffff']})
        self.assertLess(grad.pixelColor(1, 1).lightness(), grad.pixelColor(38, 38).lightness())
        path = os.path.join(self.dir, 'bg.png')
        src = QImage(10, 10, QImage.Format_RGB32)
        src.fill(QColor('#00ff00'))
        src.save(path)
        self.assertGreater(render({'type': 'image', 'value': path}).pixelColor(5, 5).green(), 150)
        # 잘못된 이미지 경로 → 기본 배경
        self.assertEqual(render({'type': 'image', 'value': '/nope.png'}).pixelColor(5, 5).name(),
                         theme.c('chat_bg').lower())

    def test_dark_detection(self):
        self.assertTrue(is_dark_wallpaper({'type': 'color', 'value': '#1E1E1E'}))
        self.assertFalse(is_dark_wallpaper({'type': 'color', 'value': '#F5E1A4'}))

    def test_dialog_saves_global_and_room(self):
        changed = []
        self.settings.changed.connect(changed.append)
        dlg = WallpaperDialog(self.settings)
        dlg._choose({'type': 'gradient', 'value': ['#A1C4FD', '#C2E9FB']})
        dlg.accept()
        self.assertEqual(self.settings.get('chat_wallpaper')['type'], 'gradient')
        room = WallpaperDialog(self.settings, room_id='r9')
        self.assertFalse(room.choose_image('/does/not/exist.png'))
        room._choose({'type': 'color', 'value': '#C4D7B2'})
        room.accept()
        self.assertEqual(self.settings.get('room_wallpapers'), {'r9': {'type': 'color', 'value': '#C4D7B2'}})
        reset = WallpaperDialog(self.settings, room_id='r9')
        reset._use_global()
        self.assertEqual(self.settings.get('room_wallpapers'), {})
        self.assertIn('room_wallpapers', changed)
        # 설정 파일에 저장되어 재시작 후에도 유지
        again = LocalSettings('tester', base_dir=self.dir)
        self.assertEqual(again.get('chat_wallpaper')['type'], 'gradient')


if __name__ == '__main__':
    unittest.main()
