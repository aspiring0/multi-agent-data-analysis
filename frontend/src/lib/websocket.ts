/**
 * WebSocket 客户端 - 实时聊天流式通信
 *
 * 特性：
 * - 指数退避重连 (1s → 2s → 4s → 8s, 最大 30s)
 * - 心跳检测 (30s)
 * - 消息队列缓存（离线时缓存，重连后重发）
 */

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export type WsMessageHandler = (data: {
  type: string
  content?: string
  message?: string
}) => void

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

export interface WebSocketOptions {
  heartbeatInterval?: number  // 心跳间隔 (ms)
  maxReconnectDelay?: number  // 最大重连延迟 (ms)
  initialReconnectDelay?: number  // 初始重连延迟 (ms)
}

export class ChatWebSocket {
  private ws: WebSocket | null = null
  private sessionId: string
  private onMessage: WsMessageHandler
  private stopped = false

  // 重连相关
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectAttempts = 0
  private reconnectDelay: number

  // 心跳相关
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null

  // 消息队列
  private messageQueue: string[] = []

  // 配置
  private options: Required<WebSocketOptions>

  constructor(sessionId: string, onMessage: WsMessageHandler, options?: WebSocketOptions) {
    this.sessionId = sessionId
    this.onMessage = onMessage
    this.options = {
      heartbeatInterval: options?.heartbeatInterval ?? 30000,
      maxReconnectDelay: options?.maxReconnectDelay ?? 30000,
      initialReconnectDelay: options?.initialReconnectDelay ?? 1000,
    }
    this.reconnectDelay = this.options.initialReconnectDelay
  }

  connect(): Promise<void> {
    this.stopped = false
    return new Promise((resolve, reject) => {
      const url = `${WS_BASE}/ws/chat/${this.sessionId}`
      this.ws = new WebSocket(url)

      // 连接超时
      const timeout = setTimeout(() => {
        if (this.ws?.readyState !== WebSocket.OPEN) {
          this.ws?.close()
          reject(new Error('Connection timeout'))
        }
      }, 10000)

      this.ws.onopen = () => {
        clearTimeout(timeout)
        this.reconnectAttempts = 0
        this.reconnectDelay = this.options.initialReconnectDelay
        this.startHeartbeat()
        this.flushMessageQueue()
        resolve()
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          // 处理心跳响应
          if (data.type === 'pong') return
          this.onMessage(data)
        } catch {
          // ignore malformed messages
        }
      }

      this.ws.onerror = () => {
        clearTimeout(timeout)
        reject(new Error('WebSocket connection failed'))
      }

      this.ws.onclose = () => {
        clearTimeout(timeout)
        this.stopHeartbeat()
        if (!this.stopped) {
          this.scheduleReconnect()
        }
      }
    })
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)

    this.reconnectAttempts++
    console.log(`[WS] 重连中... 尝试 ${this.reconnectAttempts}, 延迟 ${this.reconnectDelay}ms`)

    this.reconnectTimer = setTimeout(() => {
      this.connect().catch(() => {
        // 重连失败，继续下一次
      })
    }, this.reconnectDelay)

    // 指数退避
    this.reconnectDelay = Math.min(
      this.reconnectDelay * 2,
      this.options.maxReconnectDelay
    )
  }

  private startHeartbeat() {
    this.stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }))
      }
    }, this.options.heartbeatInterval)
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer)
      this.heartbeatTimer = null
    }
  }

  private flushMessageQueue() {
    while (this.messageQueue.length > 0 && this.ws?.readyState === WebSocket.OPEN) {
      const message = this.messageQueue.shift()
      if (message) {
        this.ws.send(JSON.stringify({ type: 'message', message }))
      }
    }
  }

  send(message: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'message', message }))
    } else {
      // 连接断开时缓存消息
      this.messageQueue.push(message)
      console.log('[WS] 消息已缓存，等待重连')
    }
  }

  disconnect() {
    this.stopped = true
    this.stopHeartbeat()
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  get status(): ConnectionStatus {
    if (this.stopped) return 'disconnected'
    if (!this.ws) return 'disconnected'
    if (this.ws.readyState === WebSocket.CONNECTING) return 'connecting'
    if (this.ws.readyState === WebSocket.OPEN) return 'connected'
    return 'reconnecting'
  }
}

// 兼容旧版 API
export type { ChatWebSocket as WebSocket }
