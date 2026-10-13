// ui-styling 스킬의 tailwind_config_gen.py 로 생성(KCS 색·한글 글꼴·플러그인) 후
// shadcn/ui 의미 색(CSS 변수, ../assets/design-tokens.css)과 KCS 글자·모서리 단계를 더했다.
import type { Config } from 'tailwindcss'
import animate from 'tailwindcss-animate'
import tokens from '../assets/design-tokens.json'

const fontSize = Object.fromEntries(
  Object.entries(tokens.type_scale).map(([name, px]) => [name, `${px}px`]),
)

const config: Config = {
  darkMode: ['class'],
  content: ['./src/**/*.{js,jsx,ts,tsx}', './index.html'],
  theme: {
    extend: {
      colors: {
        kcs: '#2A386C',
        'kcs-dark': '#1E2955',
        danger: '#B3261E',
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 4px)',
        sm: 'calc(var(--radius) - 6px)',
        bubble: `${tokens.radius.bubble}px`,
        pill: `${tokens.radius.pill}px`,
      },
      fontSize,
      fontFamily: {
        sans: ['Apple SD Gothic Neo', 'Malgun Gothic', 'Noto Sans KR', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [animate],
}

export default config
