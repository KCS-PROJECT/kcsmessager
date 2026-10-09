import { useEffect, useMemo, useState } from 'react'
import { AlertCircle, Keyboard, MessageSquare, Moon, Palette, Play, Sun, Type } from 'lucide-react'

import tokens from '../../assets/design-tokens.json'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

type Mode = 'light' | 'dark'

const SWATCH_LABELS: Record<string, string> = {
  yellow: '주 강조', yellow_dark: '강조 진하게', on_accent: '강조 위 글자', bg: '배경', bg_alt: '보조 배경',
  chat_bg: '채팅 배경', text: '글자', text_sub: '보조 글자', text_hint: '안내 글자', border: '선',
  badge: '배지', danger_text: '경고 글자',
}

// WCAG 상대 휘도 대비 (데스크톱 tests/test_kakao_layout.contrast 와 같은 식)
function luminance(hex: string) {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((v) => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
function contrast(a: string, b: string) {
  const [x, y] = [luminance(a), luminance(b)].sort((p, q) => q - p)
  return (x + 0.05) / (y + 0.05)
}

const SHORTCUTS: [string, string][] = [
  ['Ctrl+1 ~ 5', '탭 이동 (친구 · 채팅 · 조직도 · 캘린더 · 더보기)'],
  ['Ctrl+K', '빠른 이동 (채팅방 · 사람 검색)'],
  ['Alt+↑ / Alt+↓', '채팅방에서 메시지 고르기'],
  ['Shift+F10', '고른 메시지의 메뉴 (답장 · 공감 · 전달 · 삭제)'],
  ['F6', '어디서든 메시지 입력창으로'],
  ['Esc', '선택 · 답장 · 수정 취소'],
]

function Swatch({ name, hex, bg }: { name: string; hex: string; bg: string }) {
  const ratio = contrast(hex, bg)
  return (
    <div className="flex flex-col gap-2">
      <div className="h-20 rounded-lg border" style={{ background: hex }} aria-hidden />
      <div className="text-meta font-medium">{SWATCH_LABELS[name] ?? name}</div>
      <div className="flex items-center justify-between text-caption text-muted-foreground">
        <span className="font-mono uppercase">{hex}</span>
        <span>{ratio.toFixed(1)}:1</span>
      </div>
    </div>
  )
}

function VoiceBubble() {
  const bars = useMemo(() => Array.from({ length: 22 }, (_, i) => 0.25 + 0.75 * Math.abs(Math.sin(i * 0.7 + 1.3))), [])
  return (
    <div className="flex w-[230px] items-center gap-2.5 rounded-bubble bg-primary px-3 py-2 text-primary-foreground">
      <button className="grid size-8 shrink-0 place-items-center rounded-full bg-primary-foreground text-primary"
        aria-label="음성메시지 재생">
        <Play className="size-3.5 fill-current" aria-hidden />
      </button>
      <div className="flex h-6 flex-1 items-center gap-0.5" aria-hidden>
        {bars.map((h, i) => (
          <span key={i} className="w-0.5 flex-1 rounded-full bg-primary-foreground"
            style={{ height: `${h * 100}%`, opacity: i < 8 ? 1 : 0.5 }} />
        ))}
      </div>
      <span className="text-meta opacity-80">0:12</span>
    </div>
  )
}

export default function App() {
  const [mode, setMode] = useState<Mode>(() =>
    window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  useEffect(() => { document.documentElement.classList.toggle('dark', mode === 'dark') }, [mode])
  const palette = tokens[mode] as Record<string, string>
  const tags = tokens.summary_tags[mode] as Record<string, string[]>

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-8">
      <header className="flex flex-wrap items-end justify-between gap-6 border-l-4 border-primary pl-5">
        <div>
          <h1 className="text-[40px] font-light leading-tight tracking-[-0.02em]">KCS Talk</h1>
          <p className="mt-1 text-body text-muted-foreground">
            ㈜케이씨에스 사내 메신저 디자인 시스템 — 값은 데스크톱 앱 <code className="font-mono">theme.py</code>에서 자동 생성
          </p>
        </div>
        <label className="flex items-center gap-2 text-meta text-muted-foreground">
          <Sun className="size-4" aria-hidden />
          <Switch checked={mode === 'dark'} onCheckedChange={(on) => setMode(on ? 'dark' : 'light')}
            aria-label="다크 모드" />
          <Moon className="size-4" aria-hidden />
        </label>
      </header>

      <Tabs defaultValue="color" className="mt-10">
        <TabsList>
          <TabsTrigger value="color"><Palette className="mr-1.5 size-4" aria-hidden />색</TabsTrigger>
          <TabsTrigger value="type"><Type className="mr-1.5 size-4" aria-hidden />글자</TabsTrigger>
          <TabsTrigger value="components"><MessageSquare className="mr-1.5 size-4" aria-hidden />부품</TabsTrigger>
          <TabsTrigger value="a11y"><Keyboard className="mr-1.5 size-4" aria-hidden />접근성</TabsTrigger>
        </TabsList>

        <TabsContent value="color" className="mt-6">
          <p className="mb-5 text-body text-muted-foreground">
            오른쪽 숫자는 배경({palette.bg.toUpperCase()}) 대비. 글자로 쓰는 색은 4.5:1 이상이고, 배경·선 색은 면을 나누는 용도라 글자 대비 기준 대상이 아닙니다.
          </p>
          <div className="grid grid-cols-2 gap-5 sm:grid-cols-4 lg:grid-cols-6">
            {Object.entries(palette).map(([name, hex]) => (
              <Swatch key={name} name={name} hex={hex} bg={palette.bg} />
            ))}
          </div>
        </TabsContent>

        <TabsContent value="type" className="mt-6 space-y-3">
          {Object.entries(tokens.type_scale).map(([name, px]) => (
            <div key={name} className="flex items-baseline gap-6 border-b pb-3">
              <span className="w-28 shrink-0 text-caption text-muted-foreground">{name} · {px}px</span>
              <span style={{ fontSize: px }}>회의는 오후 2시로 확정했습니다 Aa</span>
            </div>
          ))}
          <p className="pt-2 text-meta text-muted-foreground">
            데스크톱은 글자 크기 설정(작게 ~ 최대 200%)에 따라 모든 단계가 함께 커집니다.
          </p>
        </TabsContent>

        <TabsContent value="components" className="mt-6 grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader><CardTitle className="text-emphasis">버튼 변형</CardTitle></CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              <Button>1:1 채팅</Button>
              <Button variant="secondary">프로필 보기</Button>
              <Button variant="outline">취소</Button>
              <Button variant="ghost">더보기</Button>
              <Button variant="destructive">삭제</Button>
              <Button disabled>보내는 중</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-emphasis">대화 요약 태그</CardTitle></CardHeader>
            <CardContent className="space-y-2.5 text-body">
              {Object.entries(tags).map(([label, [fg, bg]]) => (
                <div key={label} className="flex items-center gap-2.5">
                  <Badge className="rounded-sm border-0 font-bold shadow-none" style={{ color: fg, background: bg }}>
                    {label}
                  </Badge>
                  <span className="text-caption text-muted-foreground">{contrast(fg, bg).toFixed(1)}:1</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-emphasis">연락처 카드</CardTitle></CardHeader>
            <CardContent>
              <div className="w-[230px] rounded-lg border bg-card p-3.5">
                <div className="text-meta text-muted-foreground">연락처</div>
                <div className="mt-2 flex items-center gap-2.5">
                  <div className="grid size-10 place-items-center rounded-full bg-[#2E8B57] text-meta font-bold text-white">박</div>
                  <div>
                    <div className="text-emphasis font-bold">박민수</div>
                    <div className="text-meta text-muted-foreground">케이씨에스 · 영업1부 · 부장</div>
                  </div>
                </div>
                <div className="mt-3 flex gap-1.5">
                  <Button size="sm" className="flex-1">1:1 채팅</Button>
                  <Button size="sm" variant="secondary" className="flex-1">프로필 보기</Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-emphasis">음성메시지 · 전송 실패</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <VoiceBubble />
              <div className="flex items-end gap-1.5">
                <div className="flex flex-col items-center">
                  <AlertCircle className="size-5 fill-destructive text-white" aria-label="보내지 못한 메시지" />
                  <span className="text-micro font-bold text-danger dark:text-[#FF8A80]">전송 실패</span>
                </div>
                <div className="rounded-bubble bg-primary px-3 py-2 text-body text-primary-foreground">
                  회의 자료 지금 올립니다
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="a11y" className="mt-6">
          <Card>
            <CardHeader><CardTitle className="text-emphasis">키보드로 쓰기</CardTitle></CardHeader>
            <CardContent>
              <dl className="divide-y">
                {SHORTCUTS.map(([key, desc]) => (
                  <div key={key} className="flex gap-6 py-2.5">
                    <dt className="w-36 shrink-0"><kbd className="rounded border bg-muted px-1.5 py-0.5 font-mono text-meta">{key}</kbd></dt>
                    <dd className="text-body">{desc}</dd>
                  </div>
                ))}
              </dl>
              <Separator className="my-4" />
              <p className="text-meta text-muted-foreground">
                대화상자는 열리면 첫 입력칸, 닫히면 연 곳으로 포커스를 돌려줍니다 · 토스트는 스크린리더가 읽습니다 ·
                움직임은 더보기 › 동작 줄이기로 멈출 수 있습니다.
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
