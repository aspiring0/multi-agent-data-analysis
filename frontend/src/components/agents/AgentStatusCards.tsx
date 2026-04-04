'use client'

import { cn } from '@/lib/utils'
import { useAppStore } from '@/lib/store'

const AGENT_CONFIG = {
  coordinator: { icon: '🎯', name: 'Coordinator', color: 'bg-purple-500' },
  data_parser: { icon: '📄', name: 'Parser', color: 'bg-blue-500' },
  data_profiler: { icon: '🔍', name: 'Profiler', color: 'bg-cyan-500' },
  code_generator: { icon: '💻', name: 'Code Gen', color: 'bg-amber-500' },
  debugger: { icon: '🔧', name: 'Debugger', color: 'bg-orange-500' },
  visualizer: { icon: '📊', name: 'Visualizer', color: 'bg-pink-500' },
  report_writer: { icon: '📝', name: 'Reporter', color: 'bg-indigo-500' },
}

type AgentName = keyof typeof AGENT_CONFIG

interface AgentStatusCardsProps {
  activeAgents?: AgentName[]
  className?: string
}

export function AgentStatusCards({ activeAgents = [], className }: AgentStatusCardsProps) {
  const isStreaming = useAppStore((s) => s.isStreaming)

  // Show coordinator when streaming but no active agents specified
  const displayAgents: AgentName[] = isStreaming && activeAgents.length === 0
    ? ['coordinator']
    : activeAgents.length > 0
      ? activeAgents
      : []

  // Don't render if not streaming and no active agents
  if (!isStreaming && activeAgents.length === 0) {
    return null
  }

  return (
    <div className={cn('flex flex-wrap gap-2 px-4 py-2', className)}>
      {displayAgents.map((agent) => {
        const config = AGENT_CONFIG[agent]
        const isActive = activeAgents.includes(agent) || (isStreaming && agent === 'coordinator')

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
                isActive && 'animate-pulse-glow'
              )}
            />
          </div>
        )
      })}
    </div>
  )
}
