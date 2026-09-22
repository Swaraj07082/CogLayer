export type Message = {
  id: string
  user_message: string
  assistant_message: string
}

export type ChatRequest = {
  user_id: string
  user_message: string
}

export type ChatResponse = {
  response: string
}

export type DemoUser = {
  id: string
  label: string
}
