'use client'

import { useAppStore, type ExecutionLogEntry } from '@/lib/store'
import { cn } from '@/lib/utils'

const AGENT_ICONS: Record<string, string> = {
  coordinator: '🎯',
  data_parser: '📄',
  data_profiler: '🔍',
  code_generator: '💻',
  debugger: '🔧',
  visualizer: '📊',
  report_writer: '📝',
  chat: '💬',
}

const AGENT_COLORS: Record<string, string> = {
  coordinator: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  data_parser: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  data_profiler: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  code_generator: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  debugger: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  visualizer: 'bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200',
  report_writer: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200',
  chat: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200',
}

function LogEntry({ entry, index }: { entry: ExecutionLogEntry; index: number }) {
  const isAgent = entry.type === 'agent'
  const isSkill = entry.type === 'skill'
  const isChunk = entry.type === 'chunk'

  return (
    <div
      className={cn(
        'flex items-start gap-2 py-2 px-3 text-sm rounded-lg mb-1',
        isAgent && 'bg-muted/50',
        isSkill && 'bg-accent/30',
        isChunk && 'opacity-60'
      )}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* 时间戳 */}
      <span className="text-xs text-muted-foreground shrink-0 font-mono">
        {new Date(entry.timestamp).toLocaleTimeString('zh-CN', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
        })}
      </span>

      {/* Agent 标记 */}
      {isAgent && (
        <span
          className={cn(
            'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
            AGENT_COLORS[entry.agent || 'chat']
          )}
        >
          <span>{AGENT_ICONS[entry.agent || 'chat']}</span>
          <span>{entry.agentDisplay || entry.agent}</span>
        </span>
      )}

      {/* Skill 标记 */}
      {isSkill && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-secondary text-secondary-foreground text-xs">
          <span>⚡</span>
          <span>{entry.skillDisplay || entry.skill}</span>
        </span>
      )}

      {/* Chunk 内容预览 */}
      {isChunk && entry.content && (
        <span className="text-muted-foreground truncate flex-1">
          {entry.content}...
        </span>
      )}
    </div>
  )
}

export function ExecutionPanel() {
  const isStreaming = useAppStore((s) => s.isStreaming)
  const executionLog = useAppStore((s) => s.executionLog)

  if (!isStreaming && executionLog.length === 0) {
    return null
  }

  return (
    <div className="border-b bg-background/95 backdrop-blur">
      <div className="flex items-center justify-between px-4 py-2 border-b">
        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="animate-spin text-primary">⏳</span>
          )}
          <span className="text-sm font-medium">执行过程</span>
          {isStreaming && (
            <span className="text-xs text-muted-foreground animate-pulse">
              处理中...
            </span>
          )}
        </div>
        <span className="text-xs text-muted-foreground">
          {executionLog.length} 条日志
        </span>
      </div>

      {/* 执行日志流 */}
      <div className="max-h-48 overflow-y-auto p-2">
        {executionLog.length === 0 && isStreaming ? (
          <div className="flex items-center justify-center py-4 text-sm text-muted-foreground">
            <span className="animate-pulse">等待 Agent 响应...</span>
          </div>
        ) : (
          executionLog.map((entry, index) => (
            <LogEntry key={entry.timestamp + index} entry={entry} index={index} />
          ))
        )}
      </div>
    </div>
  )
}
