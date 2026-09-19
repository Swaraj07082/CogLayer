export type Message = {
  id: string
  user_message: string
  assistant_message: string
}

export type Conversation = {
  id: string
  user_id: string
  conversation_name: string
  conversation_messages: Message[]
}

export type ConversationSummary = {
  id: string
  user_id: string
  conversation_name: string
}

export type CreateConversationRequest = {
  user_id: string
  conversation_name: string
}

export type ChatRequest = {
  conversation_id: string
  user_id: string
  user_message: string
}
