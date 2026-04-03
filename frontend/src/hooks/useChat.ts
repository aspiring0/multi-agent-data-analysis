'use client'

import { useCallback, useRef, useState } from 'react'
import { useAppStore } from '@/lib/store'
import { ChatWebSocket, type WsMessageHandler } from '@/lib/websocket'
import * as api from '@/lib/api'

export function useChat() {
  const wsRef = useRef<ChatWebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)

  const currentSessionId = useAppStore((s) => s.currentSessionId)
  const isStreaming = useAppStore((s) => s.isStreaming)
  const addMessage = useAppStore((s) => s.addMessage)
  const setStreamingContent = useAppStore((s) => s.setStreamingContent)
  const setStreaming = useAppStore((s) => s.setStreaming)
  const setWsConnected = useAppStore((s) => s.setWsConnected)
  const setCode = useAppStore((s) => s.setCode)
  const setReport = useAppStore((s) => s.setReport)
  const setFigures = useAppStore((s) => s.setFigures)
  const addExecutionLog = useAppStore((s) => s.addExecutionLog)
  const clearExecutionLog = useAppStore((s) => s.clearExecutionLog)

  // 建立 WebSocket 连接
  const connect = useCallback(
    async (sessionId: string) => {
      // 断开旧连接
      wsRef.current?.disconnect()

      const handler: WsMessageHandler = (data) => {
        switch (data.type) {
          case 'connected':
            setIsConnected(true)
            setWsConnected(true)
            break
          case 'start':
            setStreaming(true)
            clearExecutionLog()
            // 添加一个空的 assistant 消息占位
            addMessage(sessionId, {
              role: 'assistant',
              content: '',
              timestamp: Date.now(),
            })
            break
          case 'agent':
            // 记录 Agent 执行
            addExecutionLog({
              timestamp: Date.now(),
              type: 'agent',
              agent: data.agent,
              agentDisplay: data.agent_display,
            })
            break
          case 'skill':
            // 记录 Skill 调用
            addExecutionLog({
              timestamp: Date.now(),
              type: 'skill',
              skill: data.skill,
              skillDisplay: data.skill_display,
            })
            break
          case 'chunk':
            if (data.content) {
              setStreamingContent(sessionId, data.content)
              addExecutionLog({
                timestamp: Date.now(),
                type: 'chunk',
                content: data.content.substring(0, 100),
                agent: data.agent,
              })
            }
            break
          case 'code':
            if (data.content) {
              setCode(sessionId, data.content)
            }
            break
          case 'report':
            if (data.content) {
              setReport(sessionId, data.content)
            }
            break
          case 'figures':
            if (data.content && Array.isArray(data.content)) {
              setFigures(sessionId, data.content)
            }
            break
          case 'done':
            setStreaming(false)
            break
          case 'error':
            setStreaming(false)
            console.error('WebSocket error:', data.message)
            break
        }
      }

      const ws = new ChatWebSocket(sessionId, handler)
      wsRef.current = ws

      try {
        await ws.connect()
      } catch (err) {
        setIsConnected(false)
        setWsConnected(false)
        console.error('WebSocket connect failed:', err)
      }
    },
    [addMessage, setStreamingContent, setStreaming, setWsConnected, setCode, setReport, setFigures, addExecutionLog, clearExecutionLog],
  )

  // 发送消息
  const sendMessage = useCallback(
    async (content: string) => {
      if (!currentSessionId) return

      // 添加用户消息到 UI
      addMessage(currentSessionId, {
        role: 'user',
        content,
        timestamp: Date.now(),
      })

      // 优先用 WebSocket
      if (wsRef.current?.connected) {
        wsRef.current.send(content)
        return
      }

      // 降级为 HTTP
      setStreaming(true)
      addMessage(currentSessionId, {
        role: 'assistant',
        content: '',
        timestamp: Date.now(),
      })

      const res = await api.sendChat(currentSessionId, content)
      if (res.ok && res.data) {
        const responseText =
          res.data.response || res.data.content || JSON.stringify(res.data)
        setStreamingContent(currentSessionId, responseText)

        if (res.data.code) setCode(currentSessionId, res.data.code)
        if (res.data.report) setReport(currentSessionId, res.data.report)
      } else {
        setStreamingContent(
          currentSessionId,
          `Error: ${res.error || 'unknown'}`,
        )
      }
      setStreaming(false)
    },
    [
      currentSessionId,
      addMessage,
      setStreaming,
      setStreamingContent,
      setCode,
      setReport,
    ],
  )

  // 断开连接
  const disconnect = useCallback(() => {
    wsRef.current?.disconnect()
    wsRef.current = null
    setIsConnected(false)
    setWsConnected(false)
  }, [setWsConnected])

  return {
    isConnected,
    isStreaming,
    connect,
    disconnect,
    sendMessage,
  }
}
