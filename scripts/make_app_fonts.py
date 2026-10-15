# -*- coding: utf-8 -*-
"""
KCS Talk 영문 글꼴 'KCS Talk Mono' 만들기 - JetBrains Mono(NL · Nerd Font Propo 판) 파생

왜 파생 글꼴인가: 앱 글꼴 순서는 영문 JetBrains Mono → 한글 KoPub 돋움이다. JetBrains Mono 를 그대로 쓰면
공백(U+0020)도 고정폭 0.6em 이라 한글 문장의 띄어쓰기가 두 칸처럼 벌어진다. 그래서 JetBrains Mono 에서
  - 공백 · 줄바꿈 없는 공백(U+00A0)을 빼서 공백은 다음 글꼴(KoPub 돋움, 0.29em)로 내려가게 하고
  - Nerd Font 아이콘(사용자 영역 U+E000~, 1만여 자)을 빼서 2.4MB → 수백 KB 로 줄이고
  - SIL OFL 1.1 의 '수정판은 예약 글꼴 이름(JetBrains Mono)을 쓸 수 없다' 규칙대로 이름을 'KCS Talk Mono' 로 바꾼다.

사용: python3 scripts/make_app_fonts.py [JetBrainsMono Nerd Font 폴더]   (기본 /home/kcs-dgx/JetBrainsMono)
출력: assets/fonts/KCSTalkMono-{Light,Regular,Medium,SemiBold,Bold}.ttf
필요: pip install fonttools
"""

import os
import sys

from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter, Options

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'assets', 'fonts')
SOURCE = 'JetBrainsMonoNLNerdFontPropo-{weight}.ttf'
WEIGHTS = ('Light', 'Regular', 'Medium', 'SemiBold', 'Bold')
FAMILY = 'KCS Talk Mono'
PS_FAMILY = 'KCSTalkMono'
DROP = {0x20, 0xA0}   # 공백은 한글 글꼴(KoPub 돋움)이 그린다
RENAMES = (('JetBrainsMonoNL Nerd Font Propo', FAMILY), ('JetBrainsMonoNL NFP', FAMILY), ('JetBrainsMonoNLNFP', PS_FAMILY))
NOTE = (' KCS Talk Mono is a Modified Version (subset: Nerd Font icons and the space glyph removed; renamed per '
        'SIL OFL 1.1 Reserved Font Name rule) of JetBrainsMonoNL Nerd Font Propo, itself a Nerd Fonts patch of '
        'JetBrains Mono NL. Licensed under the SIL Open Font License 1.1.')


def is_private_use(cp):
    return 0xE000 <= cp <= 0xF8FF or 0xF0000 <= cp <= 0x10FFFF


def build(src, dst):
    font = TTFont(src)
    keep = [cp for cp in font.getBestCmap() if not is_private_use(cp) and cp not in DROP]
    opts = Options()
    opts.layout_features = ['*']
    opts.name_IDs = ['*']
    opts.name_legacy = True
    opts.name_languages = ['*']
    opts.glyph_names = True
    opts.notdef_outline = True
    opts.hinting = True
    sub = Subsetter(options=opts)
    sub.populate(unicodes=keep)
    sub.subset(font)
    for rec in font['name'].names:
        text = rec.toUnicode()
        for old, new in RENAMES:
            text = text.replace(old, new)
        if rec.nameID == 0:
            text += NOTE
        rec.string = text
    font.save(dst)
    return len(keep), os.path.getsize(dst)


def main():
    src_dir = sys.argv[1] if len(sys.argv) > 1 else '/home/kcs-dgx/JetBrainsMono'
    os.makedirs(OUT_DIR, exist_ok=True)
    for weight in WEIGHTS:
        src = os.path.join(src_dir, SOURCE.format(weight=weight))
        dst = os.path.join(OUT_DIR, f'{PS_FAMILY}-{weight}.ttf')
        glyphs, size = build(src, dst)
        print(f'{os.path.relpath(dst, ROOT)}  {glyphs} 글자  {size // 1024} KB')


if __name__ == '__main__':
    main()
