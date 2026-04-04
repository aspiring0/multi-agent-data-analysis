'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useAppStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import ReactMarkdown from 'react-markdown'

interface Position {
  x: number
  y: number
}

function CodePreview() {
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const sessions = useAppStore((s) => s.sessions)
  const code = currentSessionId ? sessions[currentSessionId]?.currentCode : ''

  const handleDownload = () => {
    if (!code) return
    const blob = new Blob([code], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '数据分析.py'
    a.click()
    URL.revokeObjectURL(url)
  }

  if (!code) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground p-4">
        执行分析后，代码将在此显示
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/10">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">数据分析.py</span>
          <span className="text-xs text-muted-foreground">{code.length} 字符</span>
        </div>
        <Button variant="ghost" size="sm" onClick={handleDownload}>下载</Button>
      </div>
      <ScrollArea className="flex-1">
        <SyntaxHighlighter
          language="python"
          style={oneDark}
          customStyle={{ margin: 0, fontSize: '0.75rem', background: 'transparent' }}
          showLineNumbers
        >
          {code}
        </SyntaxHighlighter>
      </ScrollArea>
    </div>
  )
}

function ChartGallery() {
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const sessions = useAppStore((s) => s.sessions)
  const figures = currentSessionId ? sessions[currentSessionId]?.figures : []
  const [selected, setSelected] = useState<string | null>(null)

  if (!figures || figures.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground p-4">
        图表将在此显示
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1 p-2">
        <div className="grid grid-cols-2 gap-2">
          {figures.map((fig: string, i: number) => (
            <button
              key={i}
              onClick={() => setSelected(selected === fig ? null : fig)}
              className={cn(
                'aspect-square rounded-lg overflow-hidden border-2 transition-all',
                selected === fig ? 'border-purple-500' : 'border-transparent hover:border-white/30'
              )}
            >
              <img
                src={`http://localhost:8000${fig}`}
                alt={`Chart ${i + 1}`}
                className="w-full h-full object-cover"
              />
            </button>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

function ReportView() {
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const sessions = useAppStore((s) => s.sessions)
  const report = currentSessionId ? sessions[currentSessionId]?.report : ''

  if (!report) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground p-4">
        分析完成后，报告将在此显示
      </div>
    )
  }

  return (
    <ScrollArea className="flex-1 p-4">
      <ReactMarkdown className="prose prose-sm dark:prose-invert max-w-none">
        {report}
      </ReactMarkdown>
    </ScrollArea>
  )
}

export function FloatingDrawer() {
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const [expanded, setExpanded] = useState(true)
  const [position, setPosition] = useState<Position>({ x: 20, y: 60 })
  const [isDragging, setIsDragging] = useState(false)
  const dragRef = useRef<{ startX: number; startY: number; startPos: Position } | null>(null)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return
    setIsDragging(true)
    dragRef.current = { startX: e.clientX, startY: e.clientY, startPos: position }
  }, [position])

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      if (!dragRef.current) return
      const dx = e.clientX - dragRef.current.startX
      const dy = e.clientY - dragRef.current.startY
      setPosition({
        x: Math.max(0, dragRef.current.startPos.x + dx),
        y: Math.max(0, dragRef.current.startPos.y + dy),
      })
    }

    const handleMouseUp = () => setIsDragging(false)

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging])

  if (!currentSessionId) return null

  return (
    <div
      className={cn(
        'fixed z-50 transition-all duration-300',
        'backdrop-blur-2xl bg-white/70 dark:bg-white/10',
        'border border-white/30 dark:border-white/10 rounded-2xl shadow-2xl',
        isDragging && 'cursor-grabbing'
      )}
      style={{
        right: position.x,
        top: position.y,
        width: expanded ? 360 : 200,
        height: expanded ? 480 : 48,
      }}
    >
      {/* Drag header */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b border-white/10 cursor-grab"
        onMouseDown={handleMouseDown}
      >
        <div className="flex gap-1">
          <div className="w-3 h-3 rounded-full bg-red-400/60" />
          <div className="w-3 h-3 rounded-full bg-yellow-400/60" />
          <div className="w-3 h-3 rounded-full bg-green-400/60" />
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-muted-foreground hover:text-foreground"
        >
          {expanded ? '收起' : '展开'}
        </button>
      </div>

      {expanded && (
        <Tabs defaultValue="code" className="flex flex-col h-[calc(100%-40px)]">
          <TabsList className="mx-2 mt-2 grid w-auto grid-cols-3 bg-white/30 dark:bg-white/5">
            <TabsTrigger value="code" className="text-xs">代码</TabsTrigger>
            <TabsTrigger value="charts" className="text-xs">图表</TabsTrigger>
            <TabsTrigger value="report" className="text-xs">报告</TabsTrigger>
          </TabsList>
          <TabsContent value="code" className="flex-1 overflow-hidden m-0">
            <CodePreview />
          </TabsContent>
          <TabsContent value="charts" className="flex-1 overflow-hidden m-0">
            <ChartGallery />
          </TabsContent>
          <TabsContent value="report" className="flex-1 overflow-hidden m-0">
            <ReportView />
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
