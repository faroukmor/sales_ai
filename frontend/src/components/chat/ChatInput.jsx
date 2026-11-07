import { Send } from 'lucide-react'
import { useState } from 'react'
export default function ChatInput({ onSend, loading }) {
  const [value, setValue] = useState('')
  const submit = () => { if (value.trim() && !loading) { onSend(value); setValue('') } }
  return <div className="input-area"><div className="composer"><textarea aria-label="Message" value={value} maxLength={2000} rows={1}
    placeholder="Ask about products, comparisons or promotions…" onChange={(event) => setValue(event.target.value)}
    onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() } }} />
    <button onClick={submit} disabled={!value.trim() || loading} aria-label="Send message"><Send size={19} /></button></div>
    <div className="input-meta"><span>Enter to send · Shift+Enter for a new line</span><span>{value.length}/2000</span></div></div>
}
