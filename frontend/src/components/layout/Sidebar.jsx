import { MessageSquarePlus, ShoppingBag, Sparkles, X } from 'lucide-react'

export default function Sidebar({ open, onClose, onNewChat, sessionId }) {
  return <aside className={`sidebar ${open ? 'sidebar-open' : ''}`} aria-label="Sidebar">
    <button className="mobile-close" onClick={onClose} aria-label="Close navigation"><X /></button>
    <div className="brand-mark"><ShoppingBag /><div><strong>GEANT</strong><span>Chat UI</span></div></div>
    <button className="new-chat" onClick={onNewChat}><MessageSquarePlus size={18} /> New conversation</button>
    <nav><span className="nav-label">Assistant</span><div className="nav-active"><Sparkles size={17} /> Product advisor</div></nav>
    <div className="session-card"><span>Current session</span><code>{sessionId ? `${sessionId.slice(0, 8)}…` : 'New session'}</code></div>
    <p className="privacy-note">Session IDs are stored in this browser. They are not authentication credentials.</p>
  </aside>
}
