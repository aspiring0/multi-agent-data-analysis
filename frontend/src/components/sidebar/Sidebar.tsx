'use client'

import { useAppStore, type DatasetMeta } from '@/lib/store'
import * as api from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { useState, useCallback, useRef, useMemo, ChangeEvent } from 'react'

// ---- Session list with search ----

function SessionList() {
  const sessions = useAppStore((s) => s.sessions)
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const setCurrentSession = useAppStore((s) => s.setCurrentSession)
  const deleteSession = useAppStore((s) => s.deleteSession)
  const updateSessionName = useAppStore((s) => s.updateSessionName)
  const [searchQuery, setSearchQuery] = useState('')

  const sessionList = useMemo(() => {
    const list = Object.values(sessions).sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
    )
    if (!searchQuery.trim()) return list
    const query = searchQuery.toLowerCase()
    return list.filter(s => s.name.toLowerCase().includes(query))
  }, [sessions, searchQuery])

  // Group by date
  const groupedSessions = useMemo(() => {
    const groups: { label: string; sessions: typeof sessionList }[] = []
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)
    const weekAgo = new Date(today)
    weekAgo.setDate(weekAgo.getDate() - 7)

    const todaySessions: typeof sessionList = []
    const yesterdaySessions: typeof sessionList = []
    const weekSessions: typeof sessionList = []
    const olderSessions: typeof sessionList = []

    for (const session of sessionList) {
      const date = new Date(session.updatedAt)
      date.setHours(0, 0, 0, 0)
      if (date >= today) todaySessions.push(session)
      else if (date >= yesterday) yesterdaySessions.push(session)
      else if (date >= weekAgo) weekSessions.push(session)
      else olderSessions.push(session)
    }

    if (todaySessions.length) groups.push({ label: '今天', sessions: todaySessions })
    if (yesterdaySessions.length) groups.push({ label: '昨天', sessions: yesterdaySessions })
    if (weekSessions.length) groups.push({ label: '本周', sessions: weekSessions })
    if (olderSessions.length) groups.push({ label: '更早', sessions: olderSessions })
    return groups
  }, [sessionList])

  if (Object.keys(sessions).length === 0) {
    return (
      <div className="px-4 py-8 text-center text-sm text-muted-foreground">
        暂无会话，点击上方按钮创建
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Search */}
      <div className="p-2">
        <div className="relative">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>
          </svg>
          <Input
            placeholder="搜索会话..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 h-8 text-sm"
          />
        </div>
      </div>

      {/* Session groups */}
      <ScrollArea className="flex-1">
        {groupedSessions.map((group) => (
          <div key={group.label} className="mb-2">
            <p className="px-3 py-1.5 text-xs font-medium text-muted-foreground">{group.label}</p>
            {group.sessions.map((session) => (
              <div
                key={session.id}
                className={cn(
                  'group flex items-center gap-2 px-3 py-2 text-sm cursor-pointer hover:bg-muted',
                  session.id === currentSessionId && 'bg-muted font-medium',
                )}
                onClick={() => setCurrentSession(session.id)}
              >
                <span className="truncate flex-1">{session.name}</span>
                <span className="text-xs text-muted-foreground shrink-0">
                  {session.messages.length}
                </span>
                <button
                  className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive shrink-0"
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteSession(session.id)
                  }}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 6h18" /><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" /><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        ))}
        {sessionList.length === 0 && searchQuery && (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">
            未找到匹配的会话
          </div>
        )}
      </ScrollArea>
    </div>
  )
}

// ---- File uploader ----

function FileUploader() {
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const addDataset = useAppStore((s) => s.addDataset)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
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
        if (fileInputRef.current) fileInputRef.current.value = ''
      }
    },
    [currentSessionId, addDataset],
  )

  return (
    <div className="p-3">
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.tsv,.xlsx,.xls,.json"
        className="hidden"
        onChange={handleUpload}
      />
      <Button
        variant="outline"
        size="sm"
        className="w-full"
        disabled={!currentSessionId || uploading}
        onClick={() => fileInputRef.current?.click()}
      >
        {uploading ? '上传中...' : '上传数据文件'}
      </Button>
      <p className="mt-1 text-xs text-muted-foreground text-center">
        CSV, Excel, JSON
      </p>
    </div>
  )
}

// ---- Dataset list ----

function DatasetList() {
  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const sessions = useAppStore((s) => s.sessions)
  const datasets = currentSessionId ? sessions[currentSessionId]?.datasets || [] : []

  if (datasets.length === 0) return null

  return (
    <div className="p-3">
      <Separator className="mb-3" />
      <p className="text-xs font-medium text-muted-foreground mb-2">数据集</p>
      <div className="space-y-1">
        {datasets.map((ds, i) => (
          <div key={i} className="rounded-md bg-muted/50 px-3 py-2 text-xs">
            <p className="font-medium truncate">{ds.file_name}</p>
            <p className="text-muted-foreground">
              {ds.num_rows} 行 x {ds.num_cols} 列
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---- Sidebar ----

export function Sidebar() {
  const createSession = useAppStore((s) => s.createSession)

  const handleNewSession = useCallback(async () => {
    const id = Date.now().toString(36)
    try {
      const res = await api.createSession('新对话')
      if (res.ok && res.data?.id) {
        createSession(res.data.id, res.data.name)
        return
      }
    } catch {
      // Fallback: local only
    }
    createSession(id, '新对话')
  }, [createSession])

  return (
    <div className="flex h-full w-72 flex-col border-r bg-background">
      {/* Header */}
      <div className="flex items-center justify-between p-4">
        <h2 className="text-sm font-semibold">会话</h2>
        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleNewSession}>
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 5v14" /><path d="M5 12h14" />
          </svg>
        </Button>
      </div>

      <Separator />

      {/* Session list */}
      <SessionList />

      <Separator />

      {/* File upload */}
      <FileUploader />

      {/* Dataset list */}
      <DatasetList />
    </div>
  )
}
