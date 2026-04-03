'use client'

import { useRef, useEffect } from 'react'
import { useAppStore } from '@/lib/store'
import { useChat } from '@/hooks/useChat'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { cn } from '@/lib/utils'
import { useState, useCallback, KeyboardEvent } from 'react'

// ---- Code Block (可折叠) ----

function CodeBlock({ code, language = 'python' }: { code: string; language?: string }) {
  const [expanded, setExpanded] = useState(false)
  const lines = code.split('\n')
  const previewLines = 5
  const hasMore = lines.length > previewLines

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
  }

  return (
    <div className="my-2 rounded-lg border bg-slate-950 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-900 border-b border-slate-800">
        <span className="text-xs text-slate-400">{language}</span>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" className="h-6 px-2 text-xs text-slate-400 hover:text-white" onClick={handleCopy}>
            复制
          </Button>
          {hasMore && (
            <Button variant="ghost" size="sm" className="h-6 px-2 text-xs text-slate-400 hover:text-white" onClick={() => setExpanded(!expanded)}>
              {expanded ? '收起' : `展开 (${lines.length} 行)`}
            </Button>
          )}
        </div>
      </div>
      {/* Code */}
      <pre className="p-3 text-xs text-slate-50 overflow-x-auto">
        <code>
          {expanded ? code : lines.slice(0, previewLines).join('\n')}
          {!expanded && hasMore && '\n...'}
        </code>
      </pre>
    </div>
  )
}

// ---- Message Content Parser (解析文本和代码块) ----

function MessageContent({ content }: { content: string }) {
  // 解析代码块: ```language\ncode```
  const parts: Array<{ type: 'text' | 'code'; content: string; language?: string }> = []
  const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g
  let lastIndex = 0
  let match

  while ((match = codeBlockRegex.exec(content)) !== null) {
    // 添加代码块之前的文本
    if (match.index > lastIndex) {
      parts.push({ type: 'text', content: content.slice(lastIndex, match.index) })
    }
    // 添加代码块
    parts.push({ type: 'code', content: match[2].trim(), language: match[1] || 'python' })
    lastIndex = match.index + match[0].length
  }
  // 添加剩余文本
  if (lastIndex < content.length) {
    parts.push({ type: 'text', content: content.slice(lastIndex) })
  }

  if (parts.length === 0) {
    return <>{content}</>
  }

  return (
    <>
      {parts.map((part, i) => (
        part.type === 'code'
          ? <CodeBlock key={i} code={part.content} language={part.language} />
          : <span key={i} className="whitespace-pre-wrap">{part.content}</span>
      ))}
    </>
  )
}

// ---- Single message bubble ----

function MessageBubble({
  role,
  content,
  streaming,
}: {
  role: string
  content: string
  streaming?: boolean
}) {
  const isUser = role === 'user'

  return (
    <div className={cn('flex gap-3 px-4 py-3', isUser ? 'justify-end' : 'justify-start')}>
      {!isUser && (
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-primary text-primary-foreground text-xs">AI</AvatarFallback>
        </Avatar>
      )}
      <div
        className={cn(
          'max-w-[75%] rounded-lg px-4 py-2.5 text-sm leading-relaxed',
          isUser
            ? 'bg-primary text-primary-foreground whitespace-pre-wrap'
            : 'bg-muted text-foreground',
        )}
      >
        {isUser ? content : <MessageContent content={content} />}
        {streaming && <span className="animate-pulse">▊</span>}
      </div>
      {isUser && (
        <Avatar className="h-8 w-8 shrink-0">
          <AvatarFallback className="bg-secondary text-secondary-foreground text-xs">U</AvatarFallback>
        </Avatar>
      )}
    </div>
  )
}

// ---- Chat input area ----

function ChatInput({
  onSend,
  disabled,
}: {
  onSend: (msg: string) => void
  disabled?: boolean
}) {
  const [value, setValue] = useState('')

  const handleSend = useCallback(() => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }, [value, disabled, onSend])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        handleSend()
      }
    },
    [handleSend],
  )

  return (
    <div className="border-t bg-background p-4">
      <div className="mx-auto flex max-w-3xl gap-2">
        <Textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入你的分析需求..."
          disabled={disabled}
          className="min-h-[44px] max-h-[200px] resize-none"
          rows={1}
        />
        <Button onClick={handleSend} disabled={disabled || !value.trim()} size="icon" className="shrink-0">
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m5 12 7-7 7 7" /><path d="M12 19V5" />
          </svg>
        </Button>
      </div>
    </div>
  )
}

// ---- Main chat interface ----

export function ChatInterface() {
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const sessions = useAppStore((s) => s.sessions)
  const isStreaming = useAppStore((s) => s.isStreaming)
  const createSession = useAppStore((s) => s.createSession)
  const { sendMessage, connect, disconnect } = useChat()

  const bottomRef = useRef<HTMLDivElement>(null)

  const currentSession = currentSessionId ? sessions[currentSessionId] : null
  const messages = currentSession?.messages || []

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Auto-connect when session changes
  useEffect(() => {
    if (currentSessionId) {
      connect(currentSessionId)
    }
    return () => disconnect()
  }, [currentSessionId, connect, disconnect])

  // Welcome screen
  if (!currentSession) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 p-8">
        <div className="text-4xl">🤖</div>
        <h2 className="text-xl font-semibold">多 Agent 数据分析平台</h2>
        <p className="text-muted-foreground text-center max-w-md">
          上传你的数据文件，用自然语言描述分析需求，AI Agent 团队会自动协作完成分析。
        </p>
        <Button
          onClick={() => createSession(Date.now().toString(36), '新对话')}
        >
          开始新对话
        </Button>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b px-4 py-3 flex items-center justify-between">
        <h3 className="font-medium truncate">{currentSession.name}</h3>
        <span className="text-xs text-muted-foreground">
          {isStreaming ? '分析中...' : `${messages.length} 条消息`}
        </span>
      </div>

      {/* Messages */}
      <ScrollArea className="flex-1 h-0">
        <div className="py-4">
          {messages.map((msg, i) => (
            <MessageBubble
              key={i}
              role={msg.role}
              content={msg.content}
              streaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Input */}
      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  )
}
