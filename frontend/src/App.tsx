import { useCallback, useEffect, useState } from 'react'
import {
  createConversation,
  getConversation,
  listConversations,
  sendChat,
} from './api/client'
import { ChatWindow } from './components/ChatWindow'
import { ConversationList } from './components/ConversationList'
import { MessageInput } from './components/MessageInput'
import type { ConversationSummary, Message } from './types'
import './App.css'

const USER_ID = '1'

function App() {
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [conversationName, setConversationName] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [listLoading, setListLoading] = useState(true)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshList = useCallback(async () => {
    setListLoading(true)
    setError(null)
    try {
      const items = await listConversations(USER_ID)
      setConversations(items)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversations')
    } finally {
      setListLoading(false)
    }
  }, [])

  useEffect(() => {
    void refreshList()
  }, [refreshList])

  async function handleSelect(id: string) {
    setSelectedId(id)
    setMessagesLoading(true)
    setError(null)
    try {
      const conversation = await getConversation(id)
      setConversationName(conversation.conversation_name)
      setMessages(conversation.conversation_messages ?? [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load conversation')
      setConversationName(null)
      setMessages([])
    } finally {
      setMessagesLoading(false)
    }
  }

  async function handleNew() {
    setCreating(true)
    setError(null)
    try {
      const name = `Conversation ${conversations.length + 1}`
      const created = await createConversation({
        user_id: USER_ID,
        conversation_name: name,
      })
      setConversations((prev) => [
        {
          id: created.id,
          user_id: created.user_id,
          conversation_name: created.conversation_name,
        },
        ...prev,
      ])
      setSelectedId(created.id)
      setConversationName(created.conversation_name)
      setMessages(created.conversation_messages ?? [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create conversation')
    } finally {
      setCreating(false)
    }
  }

  async function handleSend(userMessage: string) {
    if (!selectedId) return
    setSending(true)
    setError(null)
    try {
      const reply = await sendChat({
        conversation_id: selectedId,
        user_id: USER_ID,
        user_message: userMessage,
      })
      setMessages((prev) => [...prev, reply])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="app">
      <ConversationList
        conversations={conversations}
        selectedId={selectedId}
        onSelect={(id) => void handleSelect(id)}
        onNew={() => void handleNew()}
        creating={creating}
      />
      <main className="main">
        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}
        {listLoading && !selectedId ? (
          <div className="chat-window empty">
            <p>Loading conversations…</p>
          </div>
        ) : (
          <>
            <ChatWindow
              conversationName={conversationName}
              messages={messages}
              loading={messagesLoading}
            />
            <MessageInput
              disabled={!selectedId}
              sending={sending}
              onSend={handleSend}
            />
          </>
        )}
      </main>
    </div>
  )
}

export default App
