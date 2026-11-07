import { useCallback, useState } from 'react'
import { chatApi } from '../services/api'
import { createClientId, readSessionValue, removeSessionValue, writeSessionValue } from '../utils/browser'

const SESSION_KEY = 'geant-chat-session'

export function useChat() {
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState(() => readSessionValue(SESSION_KEY))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastPrompt, setLastPrompt] = useState('')

  const sendMessage = useCallback(async (rawMessage) => {
    const message = rawMessage.trim()
    if (!message || loading || message.length > 2000) return
    const userEntry = { id: createClientId(), role: 'user', text: message, at: new Date() }
    setMessages((current) => [...current, userEntry])
    setLoading(true)
    setError('')
    setLastPrompt(message)
    try {
      const response = await chatApi.send(message, sessionId)
      setSessionId(response.session_id)
      writeSessionValue(SESSION_KEY, response.session_id)
      setMessages((current) => [...current, {
        id: createClientId(), role: 'assistant', text: response.answer,
        response, at: new Date(),
      }])
    } catch (requestError) {
      setError(requestError.message || 'Unable to reach the assistant.')
    } finally {
      setLoading(false)
    }
  }, [loading, sessionId])

  const newChat = useCallback(() => {
    removeSessionValue(SESSION_KEY)
    setSessionId(null)
    setMessages([])
    setError('')
    setLastPrompt('')
  }, [])

  return { messages, sessionId, loading, error, lastPrompt, sendMessage, newChat }
}
