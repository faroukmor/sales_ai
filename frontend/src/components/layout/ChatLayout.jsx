import { useState } from 'react'
import Sidebar from './Sidebar'
import ChatHeader from './ChatHeader'
export default function ChatLayout({ children, onNewChat, sessionId }) {
  const [open, setOpen] = useState(false)
  return <div className="app-shell"><Sidebar open={open} onClose={() => setOpen(false)} onNewChat={onNewChat} sessionId={sessionId} />
    {open && <button className="sidebar-scrim" onClick={() => setOpen(false)} aria-label="Close navigation overlay" />}
    <main className="chat-main"><ChatHeader onMenu={() => setOpen(true)} />{children}</main></div>
}
