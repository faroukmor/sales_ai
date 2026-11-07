import { Menu, ShieldCheck } from 'lucide-react'
export default function ChatHeader({ onMenu }) {
  return <header className="chat-header"><button className="menu-button" onClick={onMenu} aria-label="Open navigation"><Menu /></button>
    <div><h1>Product assistant</h1><p><span className="online-dot" /> Grounded in catalog data</p></div>
    <div className="grounded-badge"><ShieldCheck size={16} /> Verified results</div>
  </header>
}
