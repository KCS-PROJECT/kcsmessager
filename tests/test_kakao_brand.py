# -*- coding: utf-8 -*-
"""회사 CI 브랜드 테마 테스트 - 로고 자산, 강조색 전환, 사이드바/로그인 적용, 목록 행 폭"""

import unittest

from tests.kakao_fakes import make_demo_state, app
from PyQt5.QtGui import QColor

from client.kakao import theme, brand


def pump(n=5):
    for _ in range(n):
        app().processEvents()


class BrandTest(unittest.TestCase):
    def setUp(self):
        app()
        theme.set_dark(False)
        theme.set_brand('kcs')

    def tearDown(self):
        theme.set_dark(False)
        theme.set_brand('kcs')

    def test_logo_assets_load_and_recolor(self):
        self.assertTrue(brand.has_logo())
        for kind in ('horizontal', 'vertical', 'mark'):
            pm = brand.logo_pixmap(kind, 40)
            self.assertFalse(pm.isNull(), kind)
            self.assertAlmostEqual(pm.height() / pm.devicePixelRatio(), 40, delta=1)
        mark = brand.logo_pixmap('mark', 60)
        self.assertLess(mark.width() / mark.height(), 3.5)  # 마크만 잘렸는지 (가로형 전체는 훨씬 넓음)
        white = brand.logo_pixmap('mark', 60, '#FFFFFF').toImage()
        opaque = [white.pixelColor(x, y) for x in range(0, white.width(), 3)
                  for y in range(0, white.height(), 3) if white.pixelColor(x, y).alpha() > 250]
        self.assertTrue(opaque)
        self.assertTrue(all(c.red() > 240 and c.green() > 240 and c.blue() > 240 for c in opaque))

    def test_app_icon(self):
        icon = brand.app_icon()
        self.assertFalse(icon.isNull())
        img = brand.app_icon_pixmap(64).toImage()
        center_bg = img.pixelColor(6, img.height() // 2)  # 왼쪽 가장자리 = 네이비 배경
        self.assertLess(center_bg.lightness(), 90)

    def test_accent_switch(self):
        self.assertEqual(theme.c('yellow'), theme.BRAND_NAVY)
        self.assertEqual(theme.c('on_accent'), '#FFFFFF')
        self.assertEqual(theme.c('bubble_mine_text'), '#FFFFFF')
        self.assertEqual(theme.c('sidebar'), theme.BRAND_NAVY)
        theme.set_brand('kakao')
        self.assertEqual(theme.c('yellow'), '#FEE500')
        self.assertEqual(theme.c('on_accent'), '#191919')
        self.assertEqual(theme.c('sidebar'), '#ECECED')
        theme.set_brand('unknown')
        self.assertEqual(theme.brand(), 'kcs')
        theme.set_dark(True)
        self.assertNotEqual(theme.c('yellow'), theme.BRAND_NAVY)  # 다크에서는 밝은 블루
        self.assertTrue(QColor(theme.c('chat_bg')).lightness() < 80)

    def test_brand_is_fixed_to_kcs(self):
        """회사 CI 앱: 설정에 예전 값('kakao')이 남아 있어도 KCS 블루로 고정"""
        from client.kakao.main_window import MainWindow, apply_app_theme
        state, _ = make_demo_state()
        state.settings.set('brand_theme', 'kakao')
        apply_app_theme(state.settings)
        self.assertEqual(theme.brand(), 'kcs')
        self.assertEqual(theme.c('yellow'), theme.BRAND_NAVY)
        win = MainWindow(state, state.settings)
        win.show()
        pump()
        self.assertFalse(win.sidebar.logo.pixmap().isNull())
        win.close()

    def test_app_icon_is_messenger_bubble(self):
        """앱 아이콘: 네이비 배경 + 흰 말풍선(중앙) + 말풍선 안 네이비 마크, 작은 크기는 점 세 개"""
        from PyQt5.QtGui import QImage, QPainter
        from PyQt5.QtCore import Qt as _Qt

        def render(size):
            img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
            img.fill(_Qt.transparent)
            p = QPainter(img)
            brand.paint_app_icon(p, size)
            p.end()
            return img
        big = render(256)
        self.assertLess(big.pixelColor(128, 8).lightness(), 130)          # 위쪽 가장자리 = 네이비
        self.assertGreater(big.pixelColor(int(256 * 0.2), int(256 * 0.47)).lightness(), 240)  # 말풍선 흰색
        center = [big.pixelColor(x, int(256 * 0.47)) for x in range(90, 170)]
        self.assertTrue(any(c.lightness() < 110 for c in center))          # 말풍선 안 마크
        self.assertEqual(big.pixelColor(0, 0).alpha(), 0)                  # 둥근 모서리 투명
        small = render(32)
        self.assertLess(small.pixelColor(16, 15).lightness(), 110)        # 가운데 점
        self.assertGreater(small.pixelColor(13, 15).lightness(), 200)     # 점 사이 흰 말풍선

    def test_login_uses_ci_logo(self):
        from client.kakao.login import LoginDialog
        dlg = LoginDialog()
        self.assertFalse(dlg.logo.pixmap().isNull())
        self.assertIn('케이씨에스', dlg.findChild(type(dlg.logo), 'loginFooter').text())

    def test_more_tab_has_no_brand_selector_but_social_toggle(self):
        from client.kakao.more_tab import MoreTab
        state, _ = make_demo_state()
        tab = MoreTab(state, state.settings)
        self.assertFalse(hasattr(tab, 'brand_combo'))
        self.assertFalse(tab.company_logo.pixmap().isNull())
        tab.social_toggle.setChecked(False)
        self.assertFalse(state.settings.get('social_features'))

    def test_brand_wallpaper(self):
        from PyQt5.QtGui import QImage, QPainter
        from PyQt5.QtCore import QRectF
        from client.kakao.wallpaper import paint_wallpaper, is_dark_wallpaper
        self.assertTrue(is_dark_wallpaper({'type': 'brand', 'value': 'dark'}))
        self.assertFalse(is_dark_wallpaper({'type': 'brand', 'value': 'light'}))
        img = QImage(200, 300, QImage.Format_ARGB32)
        p = QPainter(img)
        paint_wallpaper(p, QRectF(0, 0, 200, 300), {'type': 'brand', 'value': 'dark'})
        p.end()
        self.assertLess(img.pixelColor(5, 5).lightness(), 90)

    def test_rows_fit_viewport_when_tab_shown_later(self):
        """숨겨진 탭에서 만들어진 채팅 목록 행이 표시 후 뷰포트 폭에 맞춰져야 함 (시간·배지 잘림 회귀)"""
        from client.kakao.main_window import MainWindow, apply_app_theme
        from client.kakao.chats_tab import ChatsTab, RowList
        state, _ = make_demo_state()
        apply_app_theme(state.settings)
        win = MainWindow(state, state.settings)
        win.resize(400, 680)
        win.show()
        pump()
        win.set_tab('chats')
        pump()
        lst = win.findChild(ChatsTab).findChild(RowList)
        widths = {lst.itemWidget(lst.item(i)).width() for i in range(lst.count())}
        self.assertEqual(widths, {lst.viewport().width()})
        win.close()


if __name__ == '__main__':
    unittest.main()
