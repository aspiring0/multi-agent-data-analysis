'use client'

import { useAppStore } from '@/lib/store'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import ReactMarkdown from 'react-markdown'

// ---- Code Preview (文件列表形式) ----

function CodePreview() {
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const sessions = useAppStore((s) => s.sessions)
  const code = currentSessionId ? sessions[currentSessionId]?.currentCode : ''
  const [showFullCode, setShowFullCode] = useState(false)

  const handleDownload = () => {
    if (!code) return
    const blob = new Blob([code], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '数据分析.py'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (!code) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        执行分析后，代码将在此显示
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* 文件列表 */}
      <div className="border-b">
        <div className="flex items-center justify-between px-3 py-2 hover:bg-muted/50 cursor-pointer"
             onClick={() => setShowFullCode(!showFullCode)}>
          <div className="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <span className="text-sm font-medium">数据分析.py</span>
            <span className="text-xs text-muted-foreground">{code.length} 字符</span>
          </div>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleDownload(); }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" x2="12" y1="15" y2="3"/>
              </svg>
            </Button>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform ${showFullCode ? 'rotate-180' : ''}`}>
              <path d="m6 9 6 6 6-6"/>
            </svg>
          </div>
        </div>
      </div>

      {/* 代码内容（可折叠） */}
      {showFullCode && (
        <ScrollArea className="flex-1">
          <SyntaxHighlighter
            language="python"
            style={oneDark}
            customStyle={{
              margin: 0,
              borderRadius: '0.5rem',
              fontSize: '0.8rem',
              maxHeight: '100%',
            }}
            showLineNumbers
          >
            {code}
          </SyntaxHighlighter>
        </ScrollArea>
      )}
    </div>
  )
}

// ---- Report View (文件列表形式) ----

function ReportView() {
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const sessions = useAppStore((s) => s.sessions)
  const report = currentSessionId ? sessions[currentSessionId]?.report : ''
  const [showFullReport, setShowFullReport] = useState(false)

  const handleDownload = () => {
    if (!report) return
    const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '分析报告.md'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  if (!report) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        分析完成后，报告将在此显示
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* 文件列表 */}
      <div className="border-b">
        <div className="flex items-center justify-between px-3 py-2 hover:bg-muted/50 cursor-pointer"
             onClick={() => setShowFullReport(!showFullReport)}>
          <div className="flex items-center gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <span className="text-sm font-medium">分析报告.md</span>
            <span className="text-xs text-muted-foreground">{report.length} 字符</span>
          </div>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleDownload(); }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" x2="12" y1="15" y2="3"/>
              </svg>
            </Button>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform ${showFullReport ? 'rotate-180' : ''}`}>
              <path d="m6 9 6 6 6-6"/>
            </svg>
          </div>
        </div>
      </div>

      {/* 报告内容（可折叠） */}
      {showFullReport && (
        <ScrollArea className="flex-1 p-4">
          <ReactMarkdown className="prose prose-sm dark:prose-invert max-w-none">
            {report}
          </ReactMarkdown>
        </ScrollArea>
      )}
    </div>
  )
}

// ---- Chart Gallery (文件列表形式) ----

function ChartGallery() {
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const sessions = useAppStore((s) => s.sessions)
  const figures = currentSessionId ? sessions[currentSessionId]?.figures : []
  const [selectedFigure, setSelectedFigure] = useState<string | null>(null)

  if (!figures || figures.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        图表将在此显示
      </div>
    )
  }

  const handleDownload = (figUrl: string) => {
    const a = document.createElement('a')
    a.href = `http://localhost:8000${figUrl}`
    a.download = figUrl.split('/').pop() || 'chart.png'
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }

  return (
    <div className="flex h-full flex-col">
      {/* 图表列表 */}
      <div className="border-b">
        {figures.map((fig: string, i: number) => (
          <div key={i} className="flex items-center justify-between px-3 py-2 hover:bg-muted/50 cursor-pointer border-b last:border-b-0"
               onClick={() => setSelectedFigure(selectedFigure === fig ? null : fig)}>
            <div className="flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
                <rect width="18" height="18" x="3" y="3" rx="2"/>
                <circle cx="9" cy="9" r="2"/>
                <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>
              </svg>
              <span className="text-sm font-medium">图表_{i + 1}.png</span>
            </div>
            <div className="flex items-center gap-1">
              <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleDownload(fig); }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" x2="12" y1="15" y2="3"/>
                </svg>
              </Button>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform ${selectedFigure === fig ? 'rotate-180' : ''}`}>
                <path d="m6 9 6 6 6-6"/>
              </svg>
            </div>
          </div>
        ))}
      </div>

      {/* 图表预览 */}
      {selectedFigure && (
        <div className="flex-1 p-4 overflow-auto">
          <img
            src={`http://localhost:8000${selectedFigure}`}
            alt="Chart preview"
            className="max-w-full rounded border"
          />
        </div>
      )}
    </div>
  )
}

// ---- Right Panel ----

export function RightPanel() {
  const currentSessionId = useAppStore((s) => s.currentSessionId)

  if (!currentSessionId) return null

  return (
    <div className="flex h-full w-96 flex-col border-l bg-background">
      <Tabs defaultValue="code" className="flex h-full flex-col">
        <TabsList className="mx-4 mt-2 grid w-auto grid-cols-3">
          <TabsTrigger value="code">代码</TabsTrigger>
          <TabsTrigger value="charts">图表</TabsTrigger>
          <TabsTrigger value="report">报告</TabsTrigger>
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
    </div>
  )
}
