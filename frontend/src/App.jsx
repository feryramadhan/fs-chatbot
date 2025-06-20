import { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const websocketRef = useRef(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.hostname
    const port = '8000' // Port FastAPI
    const wsUrl = `${protocol}//${host}:${port}/ws/bedrock-chat`

    // Create WebSocket connection
    const connectWebSocket = () => {
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        setIsLoading(false)

        if (data.error) {
          setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${data.error}` }])
        } else if (data.response) {
          setMessages(prev => [...prev, { role: 'assistant', content: data.response }])
        }
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)

        // Attempt to reconnect after 3 seconds
        setTimeout(() => {
          connectWebSocket()
        }, 3000)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        ws.close()
      }

      websocketRef.current = ws
    }

    connectWebSocket()

    // Clean up WebSocket connection when component unmounts
    return () => {
      if (websocketRef.current) {
        websocketRef.current.close()
      }
    }
  }, [])

  const handleSendMessage = (e) => {
    e.preventDefault()

    if (!inputMessage.trim() || !isConnected || isLoading) return

    const newMessage = { role: 'user', content: inputMessage }
    setMessages(prev => [...prev, newMessage])
    setIsLoading(true)

    // Send message to WebSocket server
    websocketRef.current.send(JSON.stringify({
      content: inputMessage
    }))

    setInputMessage('')
  }

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h1>AI Chatbot</h1>
        <div className={`connection-indicator ${isConnected ? 'connected' : 'disconnected'}`}></div>
      </header>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-message">
            <h2>Welcome to the AI Chatbot!</h2>
            <p>Send a message to start a conversation.</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={index} className={`message ${message.role}`}>
              <div className="message-content">{message.content}</div>
            </div>
          ))
        )}

        {isLoading && (
          <div className="message assistant loading">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <form className="input-form" onSubmit={handleSendMessage}>
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Type your message..."
          disabled={!isConnected || isLoading}
        />
        <button
          type="submit"
          disabled={!isConnected || isLoading || !inputMessage.trim()}
        >
          Send
        </button>
      </form>
    </div>
  )
}

export default App;
