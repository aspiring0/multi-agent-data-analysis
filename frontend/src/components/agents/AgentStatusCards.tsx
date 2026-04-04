'use client'

import { cn } from '@/lib/utils'
import { useAppStore } from '@/lib/store'

const AGENT_CONFIG = {
  coordinator: { icon: '🎯', name: 'Coordinator', color: 'bg-purple-500' },
  coordinator_v2: { icon: '🎯', name: '调度中心', color: 'bg-violet-500' },
  data_parser: { icon: '📄', name: 'Parser', color: 'bg-blue-500' },
  data_profiler: { icon: '🔍', name: 'Profiler', color: 'bg-cyan-500' },
  code_generator: { icon: '💻', name: 'Code Gen', color: 'bg-amber-500' },
  debugger: { icon: '🔧', name: 'Debugger', color: 'bg-orange-500' },
  visualizer: { icon: '📊', name: 'Visualizer', color: 'bg-pink-500' },
  report_writer: { icon: '📝', name: 'Reporter', color: 'bg-indigo-500' },
  chat: { icon: '💬', name: 'Chat', color: 'bg-green-500' },
}

type AgentName = keyof typeof AGENT_CONFIG

interface AgentStatusCardsProps {
  activeAgents?: AgentName[]
  className?: string
}

export function AgentStatusCards({ activeAgents = [], className }: AgentStatusCardsProps) {
  const isStreaming = useAppStore((s) => s.isStreaming)
  const executionLog = useAppStore((s) => s.executionLog)

  // 从执行日志中提取活跃的 agent
  const activeAgentsFromLog = executionLog
    .filter((log) => log.type === 'agent')
    .map((log) => log.agent)
    .filter((agent): agent is AgentName => agent !== undefined && agent in AGENT_CONFIG)

  // 去重并保留顺序
  const uniqueActiveAgents = [...new Set(activeAgentsFromLog)]

  // 显示的 agent 列表
  const displayAgents: AgentName[] = isStreaming && uniqueActiveAgents.length === 0
    ? ['coordinator_v2']
    : uniqueActiveAgents.length > 0
      ? uniqueActiveAgents
      : activeAgents

  // 不渲染条件
  if (!isStreaming && activeAgents.length === 0 && executionLog.length === 0) {
    return null
  }

  return (
    <div className={cn('flex flex-wrap gap-2 px-4 py-2', className)}>
      {displayAgents.map((agent) => {
        const config = AGENT_CONFIG[agent]
        if (!config) return null

        const isActive = uniqueActiveAgents.includes(agent) ||
          (isStreaming && (agent === 'coordinator_v2' || agent === 'coordinator'))

        return (
          <div
            key={agent}
            className={cn(
              'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium',
              'backdrop-blur-md border transition-all duration-300',
              isActive
                ? 'bg-purple-500/20 border-purple-500/40 text-purple-700 dark:text-purple-300'
                : 'bg-white/30 dark:bg-white/5 border-white/20 dark:border-white/10 text-gray-500 dark:text-gray-400'
            )}
          >
            <span className="text-sm">{config.icon}</span>
            <span>{config.name}</span>
            <span
              className={cn(
                'w-2 h-2 rounded-full',
                isActive ? config.color : 'bg-gray-400',
                isActive && 'animate-pulse'
              )}
            />
          </div>
        )
      })}
    </div>
  )
}
