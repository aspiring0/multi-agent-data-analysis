/**
 * WebSocket 客户端 - 实时聊天流式通信
 */

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

export type WsMessageHandler = (data: {
  type: string
  content?: string
  message?: string
}) => void

export class ChatWebSocket {
  private ws: WebSocket | null = null
  private sessionId: string
  private onMessage: WsMessageHandler
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private stopped = false

  constructor(sessionId: string, onMessage: WsMessageHandler) {
    this.sessionId = sessionId
    this.onMessage = onMessage
  }

  connect(): Promise<void> {
    this.stopped = false
    return new Promise((resolve, reject) => {
      const url = `${WS_BASE}/ws/chat/${this.sessionId}`
      this.ws = new WebSocket(url)

      this.ws.onopen = () => resolve()

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.onMessage(data)
        } catch {
          // ignore malformed messages
        }
      }

      this.ws.onerror = () => reject(new Error('WebSocket connection failed'))

      this.ws.onclose = () => {
        if (!this.stopped) {
          // Auto reconnect after 3s
          this.reconnectTimer = setTimeout(() => this.connect(), 3000)
        }
      }
    })
  }

  send(message: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'message', message }))
    }
  }

  disconnect() {
    this.stopped = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}
