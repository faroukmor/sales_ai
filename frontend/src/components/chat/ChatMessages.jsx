import { useEffect, useRef } from 'react'
import ChatMessage from './ChatMessage'
import TypingIndicator from './TypingIndicator'
export default function ChatMessages({ messages, loading }) {
  const end = useRef(null)
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])
  return <section className="messages" aria-live="polite">{messages.map((message) => <ChatMessage key={message.id} message={message} />)}
    {loading && <div className="message-row assistant"><div className="avatar">AI</div><TypingIndicator /></div>}<div ref={end} /></section>
}
