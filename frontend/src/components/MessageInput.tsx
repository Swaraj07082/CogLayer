import { useState, type FormEvent, type KeyboardEvent } from 'react'

type MessageInputProps = {
  disabled: boolean
  sending: boolean
  onSend: (message: string) => Promise<void>
}

export function MessageInput({ disabled, sending, onSend }: MessageInputProps) {
  const [text, setText] = useState('')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed || disabled || sending) return
    setText('')
    await onSend(trimmed)
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSubmit(e)
    }
  }

  return (
    <form className="message-input" onSubmit={handleSubmit}>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={disabled ? 'Unavailable' : 'Type a message…'}
        disabled={disabled || sending}
        rows={2}
      />
      <button
        type="submit"
        className="btn btn-primary"
        disabled={disabled || sending || !text.trim()}
      >
        {sending ? 'Sending…' : 'Send'}
      </button>
    </form>
  )
}
