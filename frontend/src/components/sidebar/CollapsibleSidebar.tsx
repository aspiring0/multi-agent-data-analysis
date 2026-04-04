'use client'

import { useState, useCallback, useMemo } from 'react'
import { useAppStore, type DatasetMeta } from '@/lib/store'
import * as api from '@/lib/api'
import { cn } from '@/lib/utils'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

function SessionList({ collapsed }: { collapsed: boolean }) {
  const sessions = useAppStore((s) => s.sessions)
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const setCurrentSession = useAppStore((s) => s.setCurrentSession)
  const deleteSession = useAppStore((s) => s.deleteSession)
  const [searchQuery, setSearchQuery] = useState('')

  const sessionList = useMemo(() => {
    const list = Object.values(sessions).sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
    )
    if (!searchQuery.trim()) return list
    return list.filter(s => s.name.toLowerCase().includes(searchQuery.toLowerCase()))
  }, [sessions, searchQuery])

  if (collapsed) {
    return (
      <div className="flex flex-col items-center gap-2 py-2">
        {sessionList.slice(0, 5).map((session) => (
          <button
            key={session.id}
            onClick={() => setCurrentSession(session.id)}
            className={cn(
              'w-10 h-10 rounded-xl flex items-center justify-center text-lg',
              'backdrop-blur-md border transition-all duration-200',
              session.id === currentSessionId
                ? 'bg-purple-500/30 border-purple-500/50'
                : 'bg-white/30 dark:bg-white/5 border-white/20 hover:bg-white/50 dark:hover:bg-white/10'
            )}
          >
            💬
          </button>
        ))}
      </div>
    )
  }

  if (Object.keys(sessions).length === 0) {
    return (
      <div className="px-4 py-8 text-center text-sm text-muted-foreground">
        暂无会话
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="p-2">
        <div className="relative">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
          </svg>
          <Input
            placeholder="搜索会话..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 h-8 text-sm bg-white/30 dark:bg-white/5 border-white/20"
          />
        </div>
      </div>

      <ScrollArea className="flex-1">
        {sessionList.map((session) => (
          <div
            key={session.id}
            className={cn(
              'group flex items-center gap-2 px-3 py-2 text-sm cursor-pointer',
              'transition-all duration-200',
              session.id === currentSessionId
                ? 'bg-purple-500/20 text-purple-700 dark:text-purple-300'
                : 'hover:bg-white/30 dark:hover:bg-white/5'
            )}
            onClick={() => setCurrentSession(session.id)}
          >
            <span className="truncate flex-1">{session.name}</span>
            <button
              className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive"
              onClick={(e) => { e.stopPropagation(); deleteSession(session.id) }}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
              </svg>
            </button>
          </div>
        ))}
      </ScrollArea>
    </div>
  )
}

function FileUploader({ collapsed }: { collapsed: boolean }) {
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const addDataset = useAppStore((s) => s.addDataset)
  const [uploading, setUploading] = useState(false)

  const handleUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !currentSessionId) return
    setUploading(true)
    try {
      const res = await api.uploadFile(currentSessionId, file)
      if (res.ok && res.data) {
        addDataset(currentSessionId, res.data as DatasetMeta)
      }
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }, [currentSessionId, addDataset])

  if (collapsed) {
    return (
      <div className="p-2">
        <input type="file" accept=".csv,.tsv,.xlsx,.xls,.json" className="hidden" id="file-upload-collapsed" onChange={handleUpload} />
        <button
          disabled={!currentSessionId || uploading}
          onClick={() => document.getElementById('file-upload-collapsed')?.click()}
          className="w-10 h-10 rounded-xl flex items-center justify-center bg-white/30 dark:bg-white/5 border border-white/20 hover:bg-white/50 dark:hover:bg-white/10 transition-all"
        >
          📁
        </button>
      </div>
    )
  }

  return (
    <div className="p-3">
      <input type="file" accept=".csv,.tsv,.xlsx,.xls,.json" className="hidden" id="file-upload" onChange={handleUpload} />
      <Button
        variant="outline"
        size="sm"
        className="w-full bg-white/30 dark:bg-white/5 border-white/20"
        disabled={!currentSessionId || uploading}
        onClick={() => document.getElementById('file-upload')?.click()}
      >
        {uploading ? '上传中...' : '上传数据文件'}
      </Button>
    </div>
  )
}

export function CollapsibleSidebar() {
  const [collapsed, setCollapsed] = useState(true)
  const createSession = useAppStore((s) => s.createSession)

  const handleNewSession = useCallback(async () => {
    const id = Date.now().toString(36)
    try {
      const res = await api.createSession('新对话')
      if (res.ok && res.data?.id) {
        createSession(res.data.id, res.data.name)
        return
      }
    } catch {}
    createSession(id, '新对话')
  }, [createSession])

  return (
    <div
      className={cn(
        'flex h-full flex-col border-r transition-all duration-300 ease-in-out',
        'bg-gradient-to-b from-purple-500/5 to-indigo-500/5',
        'backdrop-blur-xl border-white/10 dark:border-white/5',
        collapsed ? 'w-16' : 'w-64'
      )}
      onMouseEnter={() => setCollapsed(false)}
      onMouseLeave={() => setCollapsed(true)}
    >
      {/* Header */}
      <div className={cn('flex items-center p-3', collapsed ? 'justify-center' : 'justify-between')}>
        {!collapsed && <h2 className="text-sm font-semibold">会话</h2>}
        <button
          onClick={handleNewSession}
          className="w-9 h-9 rounded-xl flex items-center justify-center bg-purple-500/20 hover:bg-purple-500/30 text-purple-600 dark:text-purple-400 transition-all"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 5v14"/><path d="M5 12h14"/>
          </svg>
        </button>
      </div>

      <div className={cn('h-px bg-white/10 dark:bg-white/5', collapsed && 'mx-2')} />

      {/* Session list */}
      <SessionList collapsed={collapsed} />

      <div className={cn('h-px bg-white/10 dark:bg-white/5', collapsed && 'mx-2')} />

      {/* File upload */}
      <FileUploader collapsed={collapsed} />
    </div>
  )
}
