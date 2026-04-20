import { useState, useCallback } from 'react'
import { v4 as uuidv4 } from 'uuid'
import Sidebar from './components/Sidebar.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import './App.css'

const SESSION_ID_KEY = 'flight_agent_session_id'

function getOrCreateSessionId() {
  let id = sessionStorage.getItem(SESSION_ID_KEY)
  if (!id) {
    id = uuidv4()
    sessionStorage.setItem(SESSION_ID_KEY, id)
  }
  return id
}

export default function App() {
  const [messages, setMessages] = useState([
    {
      id: uuidv4(),
      role: 'assistant',
      text: "Hello! I'm your AI flight assistant. I can help you:\n\n- **Query Flights** – Search available flights\n- **Book a Flight** – Purchase tickets\n- **Check In** – Check in for your flight\n\nHow can I assist you today?",
      timestamp: new Date()
    }
  ])
  const [loading, setLoading] = useState(false)
  const [sessionId] = useState(getOrCreateSessionId)

  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || loading) return

    const userMsg = { id: uuidv4(), role: 'user', text, timestamp: new Date() }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: sessionId })
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `Server error ${res.status}`)
      }

      const data = await res.json()
      const assistantMsg = {
        id: uuidv4(),
        role: 'assistant',
        text: data.response,
        toolCalls: data.tool_calls,
        timestamp: new Date()
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      setMessages(prev => [...prev, {
        id: uuidv4(),
        role: 'assistant',
        text: `Sorry, something went wrong: ${err.message}`,
        isError: true,
        timestamp: new Date()
      }])
    } finally {
      setLoading(false)
    }
  }, [loading, sessionId])

  const handleQuickAction = useCallback((action) => {
    const prompts = {
      query: 'I want to search for available flights.',
      book: 'I would like to book a flight ticket.',
      checkin: 'I need to check in for my flight.'
    }
    sendMessage(prompts[action])
  }, [sendMessage])

  const handleNewChat = useCallback(() => {
    sessionStorage.removeItem(SESSION_ID_KEY)
    window.location.reload()
  }, [])

  return (
    <div className="app-layout">
      <Sidebar onQuickAction={handleQuickAction} onNewChat={handleNewChat} />
      <ChatWindow messages={messages} loading={loading} onSend={sendMessage} />
    </div>
  )
}
