import { create } from 'zustand'
import { persist } from 'zustand/middleware'

// ---- Types ----

export interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
}

export interface DatasetMeta {
  file_name: string
  file_path: string
  num_rows: number
  num_cols: number
  columns: string[]
  dtypes: Record<string, string>
  preview: string[][]
}

export interface Session {
  id: string
  name: string
  messages: Message[]
  datasets: DatasetMeta[]
  currentCode: string
  report: string
  figures: string[]
  createdAt: string
  updatedAt: string
}

export interface AppStore {
  // State
  sessions: Record<string, Session>
  currentSessionId: string | null
  isStreaming: boolean
  wsConnected: boolean
  // Agent execution tracking
  currentAgent: string | null
  currentAgentDisplay: string | null
  currentSkill: string | null
  currentSkillDisplay: string | null
  executionLog: ExecutionLogEntry[]

  // Session actions
  createSession: (id: string, name: string) => void
  deleteSession: (id: string) => void
  setCurrentSession: (id: string | null) => void
  updateSessionName: (id: string, name: string) => void

  // Message actions
  addMessage: (sessionId: string, message: Message) => void
  setStreamingContent: (sessionId: string, content: string) => void

  // Dataset actions
  addDataset: (sessionId: string, dataset: DatasetMeta) => void

  // Artifact actions
  setCode: (sessionId: string, code: string) => void
  setReport: (sessionId: string, report: string) => void
  setFigures: (sessionId: string, figures: string[]) => void

  // Connection state
  setStreaming: (streaming: boolean) => void
  setWsConnected: (connected: boolean) => void

  // Agent execution tracking
  setCurrentAgent: (agent: string | null, display: string | null) => void
  setCurrentSkill: (skill: string | null, display: string | null) => void
  addExecutionLog: (entry: ExecutionLogEntry) => void
  clearExecutionLog: () => void

  // Hydration from API
  loadSessionFromApi: (session: Session) => void
}

export interface ExecutionLogEntry {
  timestamp: number
  type: 'agent' | 'skill' | 'chunk' | 'error'
  agent?: string
  agentDisplay?: string
  skill?: string
  skillDisplay?: string
  content?: string
}

export const useAppStore = create<AppStore>()(
  persist(
    (set, get) => ({
      sessions: {},
      currentSessionId: null,
      isStreaming: false,
      wsConnected: false,
      executionLog: [],
      currentAgent: null,
      currentAgentDisplay: null,
      currentSkill: null,
      currentSkillDisplay: null,

      // ---- Session actions ----

      createSession: (id, name) =>
        set((state) => ({
          sessions: {
            ...state.sessions,
            [id]: {
              id,
              name,
              messages: [],
              datasets: [],
              currentCode: '',
              report: '',
              figures: [],
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            },
          },
          currentSessionId: id,
        })),

      deleteSession: (id) =>
        set((state) => {
          const { [id]: _, ...rest } = state.sessions
          return {
            sessions: rest,
            currentSessionId:
              state.currentSessionId === id
                ? Object.keys(rest)[0] || null
                : state.currentSessionId,
          }
        }),

      setCurrentSession: (id) => set({ currentSessionId: id }),

      updateSessionName: (id, name) =>
        set((state) => ({
          sessions: {
            ...state.sessions,
            [id]: { ...state.sessions[id], name, updatedAt: new Date().toISOString() },
          },
        })),

      // ---- Message actions ----

      addMessage: (sessionId, message) =>
        set((state) => {
          const session = state.sessions[sessionId]
          if (!session) return state
          return {
            sessions: {
              ...state.sessions,
              [sessionId]: {
                ...session,
                messages: [...session.messages, message],
                updatedAt: new Date().toISOString(),
              },
            },
          }
        }),

      setStreamingContent: (sessionId, content) =>
        set((state) => {
          const session = state.sessions[sessionId]
          if (!session) return state
          const messages = [...session.messages]
          const lastMsg = messages[messages.length - 1]
          if (lastMsg?.role === 'assistant') {
            messages[messages.length - 1] = { ...lastMsg, content }
          }
          return {
            sessions: {
              ...state.sessions,
              [sessionId]: { ...session, messages },
            },
          }
        }),

      // ---- Dataset actions ----

      addDataset: (sessionId, dataset) =>
        set((state) => {
          const session = state.sessions[sessionId]
          if (!session) return state
          return {
            sessions: {
              ...state.sessions,
              [sessionId]: {
                ...session,
                datasets: [...session.datasets, dataset],
                updatedAt: new Date().toISOString(),
              },
            },
          }
        }),

      // ---- Artifact actions ----

      setCode: (sessionId, code) =>
        set((state) => {
          const session = state.sessions[sessionId]
          if (!session) return state
          return {
            sessions: {
              ...state.sessions,
              [sessionId]: { ...session, currentCode: code },
            },
          }
        }),

      setReport: (sessionId, report) =>
        set((state) => {
          const session = state.sessions[sessionId]
          if (!session) return state
          return {
            sessions: {
              ...state.sessions,
              [sessionId]: { ...session, report },
            },
          }
        }),

      setFigures: (sessionId, figures) =>
        set((state) => {
          const session = state.sessions[sessionId]
          if (!session) return state
          return {
            sessions: {
              ...state.sessions,
              [sessionId]: { ...session, figures },
            },
          }
        }),

      // ---- Connection state ----

      setStreaming: (streaming) => set({ isStreaming: streaming }),
      setWsConnected: (connected) => set({ wsConnected: connected }),

      // ---- Agent Execution Tracking ----

      setCurrentAgent: (agent, display) =>
        set({ currentAgent: agent, currentAgentDisplay: display }),
      setCurrentSkill: (skill, display) =>
        set({ currentSkill: skill, currentSkillDisplay: display }),

      // ---- Execution Log ----

      addExecutionLog: (entry) =>
        set((state) => ({
          executionLog: [...state.executionLog, entry],
        })),
      clearExecutionLog: () => set({ executionLog: [] }),

      // ---- Hydration ----

      loadSessionFromApi: (session) =>
        set((state) => ({
          sessions: {
            ...state.sessions,
            [session.id]: session,
          },
        })),
    }),
    {
      name: 'multi-agent-storage',
      partialize: (state) => ({
        sessions: state.sessions,
        currentSessionId: state.currentSessionId,
      }),
    },
  ),
)
