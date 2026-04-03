'use client'

import { Sidebar } from '@/components/sidebar/Sidebar'
import { ChatInterface } from '@/components/chat/ChatInterface'
import { RightPanel } from '@/components/panel/RightPanel'

export default function Home() {
  return (
    <div className="flex h-full overflow-hidden">
      {/* Left sidebar: sessions + file upload */}
      <Sidebar />

      {/* Center: chat */}
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <ChatInterface />
      </main>

      {/* Right panel: code / charts / report */}
      <RightPanel />
    </div>
  )
}
