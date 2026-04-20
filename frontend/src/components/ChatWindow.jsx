import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import './ChatWindow.css'

function ToolBadge({ toolCalls }) {
  if (!toolCalls || toolCalls.length === 0) return null
  const icons = { query_flights: '🔍', buy_ticket: '✈️', check_in: '✅' }
  const labels = { query_flights: 'Searched flights', buy_ticket: 'Booked ticket', check_in: 'Checked in' }
  return (
    <div className="tool-badges">
      {toolCalls.map((tc, i) => (
        <span key={i} className="tool-badge">
          {icons[tc.tool] || '⚙️'} {labels[tc.tool] || tc.tool}
        </span>
      ))}
    </div>
  )
}

function Message({ msg }) {
  const isUser = msg.role === 'user'
  const time = msg.timestamp?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div className={`message-row ${isUser ? 'message-row--user' : 'message-row--assistant'}`}>
      {!isUser && (
        <div className="avatar avatar--assistant">✈</div>
      )}
      <div className={`bubble ${isUser ? 'bubble--user' : 'bubble--assistant'} ${msg.isError ? 'bubble--error' : ''}`}>
        {isUser ? (
          <p>{msg.text}</p>
        ) : (
          <ReactMarkdown>{msg.text}</ReactMarkdown>
        )}
        <ToolBadge toolCalls={msg.toolCalls} />
        <span className="message-time">{time}</span>
      </div>
      {isUser && (
        <div className="avatar avatar--user">You</div>
      )}
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="message-row message-row--assistant">
      <div className="avatar avatar--assistant">✈</div>
      <div className="bubble bubble--assistant typing-bubble">
        <span className="dot" /><span className="dot" /><span className="dot" />
      </div>
    </div>
  )
}

export default function ChatWindow({ messages, loading, onSend }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim()) return
    onSend(input.trim())
    setInput('')
    inputRef.current?.focus()
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <main className="chat-window">
      <header className="chat-header">
        <div className="chat-header-info">
          <h2>AI Flight Assistant</h2>
          <span className="status-dot" /> Online
        </div>
      </header>

      <div className="messages-area">
        {messages.map(msg => <Message key={msg.id} msg={msg} />)}
        {loading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      <form className="input-bar" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask me about flights, bookings, or check-in..."
          disabled={loading}
          autoFocus
        />
        <button
          type="submit"
          className="send-btn"
          disabled={loading || !input.trim()}
        >
          {loading ? '...' : '➤'}
        </button>
      </form>
    </main>
  )
}
