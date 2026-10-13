# KCS Talk 디자인 시스템 (웹 문서)

ui-styling 스킬(shadcn/ui + Tailwind)로 만든 KCS Talk 디자인 시스템 문서입니다.
색·글자·모서리 값은 데스크톱 앱 `client/kakao/theme.py`에서 자동 생성한 토큰을 그대로 씁니다.

```bash
# 1) 토큰 다시 만들기 (theme.py 를 바꾼 뒤)
python3 ../scripts/make_design_board.py     # → ../assets/design-tokens.css / .json, docs/design/*.png

# 2) 문서 보기
npm install
npm run dev        # http://localhost:5173
npm run build      # dist/
```

- 탭: **색**(라이트/다크, 배경 대비) · **글자**(단계 11개, `theme.TYPE_SCALE`) · **부품**(버튼 변형, 대화 요약 태그, 연락처 카드, 음성메시지, 전송 실패) · **접근성**(단축키)
- 만든 방법 (ui-styling 스크립트)
  - `tailwind_config_gen.py --framework react --colors kcs:#2A386C kcs-dark:#1E2955 danger:#B3261E --fonts "sans:Apple SD Gothic Neo,…" --plugins` → `tailwind.config.ts` (이후 shadcn CSS 변수·KCS 글자 단계 추가)
  - `shadcn_add.py button card badge tabs separator switch` (shadcn 2.3.0, `components.json` new-york)
- 참고: 사용자 `~/.npmrc` 의 `allow-scripts` 전역 설정이 프로젝트 안 설치와 충돌하면
  `npm_config_userconfig=<빈 파일> python3 …/shadcn_add.py …` 처럼 이 명령에만 빈 설정을 쓰면 됩니다.
