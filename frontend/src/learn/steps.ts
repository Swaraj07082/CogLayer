export type PathKind = 'read' | 'write'

export type NodeId =
  | 'user'
  | 'api'
  | 'qdrant'
  | 'conversation'
  | 'llm'
  | 'celery'
  | 'memory'

export type EdgeId =
  | 'user-api'
  | 'api-qdrant'
  | 'api-conversation'
  | 'api-llm'
  | 'llm-user'
  | 'api-celery'
  | 'celery-conversation'
  | 'celery-llm'
  | 'celery-qdrant'
  | 'celery-memory'

export type LearnStep = {
  id: string
  title: string
  caption: string
  why: string
  activeNodes: NodeId[]
  activeEdges: EdgeId[]
  /** Optional packet travel for motion */
  packet?: { from: NodeId; to: NodeId }
}

export const READ_STEPS: LearnStep[] = [
  {
    id: 'r1',
    title: 'User sends a query',
    caption: 'A chat message hits FastAPI /chat — this is the synchronous read path.',
    why: 'The reply must stay fast. Heavy memory maintenance waits for the write path.',
    activeNodes: ['user', 'api'],
    activeEdges: ['user-api'],
    packet: { from: 'user', to: 'api' },
  },
  {
    id: 'r2',
    title: 'Embed query + similarity search',
    caption: 'The query is embedded and Qdrant returns top-k memories scoped by user_id.',
    why: 'Embeddings give cheap recall across many facts without stuffing the whole store into the prompt.',
    activeNodes: ['api', 'qdrant'],
    activeEdges: ['api-qdrant'],
    packet: { from: 'api', to: 'qdrant' },
  },
  {
    id: 'r3',
    title: 'Load conversation context',
    caption: 'Recent turns are loaded from the conversation store for short-term context.',
    why: 'Memories are long-term facts; conversation turns are the immediate thread.',
    activeNodes: ['api', 'conversation'],
    activeEdges: ['api-conversation'],
    packet: { from: 'api', to: 'conversation' },
  },
  {
    id: 'r4',
    title: 'Build the prompt',
    caption: 'System instructions + retrieved memories + history + the user query become one prompt.',
    why: 'The model only sees what was retrieved — not the entire memory database.',
    activeNodes: ['api', 'qdrant', 'conversation', 'llm'],
    activeEdges: ['api-llm'],
    packet: { from: 'api', to: 'llm' },
  },
  {
    id: 'r5',
    title: 'LLM generates the reply',
    caption: 'Groq produces an answer grounded in that user’s memories and chat history.',
    why: 'Judgment for wording happens here; storage decisions wait for the write path.',
    activeNodes: ['llm'],
    activeEdges: [],
  },
  {
    id: 'r6',
    title: 'Reply sent to the user',
    caption: 'The HTTP response returns immediately so the UI stays snappy.',
    why: 'Users should not wait on EXTRACT + DECIDE + store updates.',
    activeNodes: ['llm', 'user', 'api'],
    activeEdges: ['llm-user'],
    packet: { from: 'llm', to: 'user' },
  },
  {
    id: 'r7',
    title: 'Fire the background job',
    caption: 'process_message_pair.delay(...) enqueues the write path on RabbitMQ → Celery.',
    why: 'This is the handoff: read path done, write path starts without blocking the reply.',
    activeNodes: ['api', 'celery'],
    activeEdges: ['api-celery'],
    packet: { from: 'api', to: 'celery' },
  },
]

export const WRITE_STEPS: LearnStep[] = [
  {
    id: 'w1',
    title: 'New message pair arrives',
    caption: 'Celery picks up user query + assistant reply as one write-path unit.',
    why: 'Facts are extracted from the exchange, not from the query alone.',
    activeNodes: ['celery', 'api'],
    activeEdges: ['api-celery'],
    packet: { from: 'api', to: 'celery' },
  },
  {
    id: 'w2',
    title: 'Save to conversation store',
    caption: 'The pair is appended to conversations_store.json for that user UUID.',
    why: 'Later EXTRACT calls need history for summary S and last-m messages.',
    activeNodes: ['celery', 'conversation'],
    activeEdges: ['celery-conversation'],
    packet: { from: 'celery', to: 'conversation' },
  },
  {
    id: 'w3',
    title: 'Build extraction prompt P',
    caption: 'Summary S of past messages + last ~10 turns + the new pair.',
    why: 'Summary compresses old context; recent turns keep detail for new facts.',
    activeNodes: ['celery', 'conversation', 'llm'],
    activeEdges: ['celery-conversation', 'celery-llm'],
    packet: { from: 'conversation', to: 'llm' },
  },
  {
    id: 'w4',
    title: 'LLM call #1 — EXTRACT',
    caption: 'The model emits candidate memory facts (atomic sentences).',
    why: 'Not every sentence is a durable memory — EXTRACT filters for lasting facts.',
    activeNodes: ['llm', 'celery'],
    activeEdges: ['celery-llm'],
  },
  {
    id: 'w5',
    title: 'Similar search per candidate',
    caption: 'Each fact is embedded and matched against that user’s top-s memories in Qdrant.',
    why: 'Similarity = cheap recall of possible duplicates, updates, or contradictions.',
    activeNodes: ['celery', 'qdrant'],
    activeEdges: ['celery-qdrant'],
    packet: { from: 'celery', to: 'qdrant' },
  },
  {
    id: 'w6',
    title: 'LLM call #2 — DECIDE',
    caption: 'Given a candidate + top-s matches, the model picks one tool: ADD, UPDATE, DELETE, or NOOP.',
    why: '“Likes X” vs “hates X” embed similarly — only an LLM can judge the relationship.',
    activeNodes: ['llm', 'celery', 'qdrant'],
    activeEdges: ['celery-llm'],
  },
  {
    id: 'w7',
    title: 'Apply operations',
    caption: 'ADD/UPDATE write (and re-embed) into memory_store.json + upsert Qdrant. DELETE removes both. NOOP skips.',
    why: 'JSON is the durable record; Qdrant must stay in sync for the next read path.',
    activeNodes: ['celery', 'memory', 'qdrant'],
    activeEdges: ['celery-memory', 'celery-qdrant'],
    packet: { from: 'celery', to: 'memory' },
  },
  {
    id: 'w8',
    title: 'Ready for the next query',
    caption: 'The next /chat read path will retrieve the updated memories automatically.',
    why: 'That closes the loop: chat → learn → store → chat again.',
    activeNodes: ['memory', 'qdrant', 'user', 'api'],
    activeEdges: ['user-api', 'api-qdrant'],
  },
]

export const NODE_META: Record<
  NodeId,
  { label: string; sub: string; x: number; y: number; kind: 'actor' | 'store' | 'compute' | 'queue' }
> = {
  user: { label: 'User', sub: 'Chat UI', x: 8, y: 18, kind: 'actor' },
  api: { label: 'FastAPI', sub: '/chat', x: 28, y: 18, kind: 'compute' },
  llm: { label: 'LLM', sub: 'Groq', x: 52, y: 8, kind: 'compute' },
  qdrant: { label: 'Qdrant', sub: 'Vector search', x: 52, y: 32, kind: 'store' },
  conversation: { label: 'Conversation', sub: 'Turns + summary S', x: 28, y: 48, kind: 'store' },
  celery: { label: 'Celery', sub: 'Write worker', x: 72, y: 48, kind: 'queue' },
  memory: { label: 'Memory store', sub: 'JSON facts', x: 88, y: 28, kind: 'store' },
}

/** Edge paths as percent coords for SVG overlay */
export const EDGE_PATHS: Record<EdgeId, { x1: number; y1: number; x2: number; y2: number }> = {
  'user-api': { x1: 14, y1: 22, x2: 22, y2: 22 },
  'api-qdrant': { x1: 36, y1: 24, x2: 46, y2: 32 },
  'api-conversation': { x1: 32, y1: 28, x2: 32, y2: 42 },
  'api-llm': { x1: 36, y1: 16, x2: 46, y2: 12 },
  'llm-user': { x1: 46, y1: 10, x2: 14, y2: 16 },
  'api-celery': { x1: 36, y1: 28, x2: 66, y2: 46 },
  'celery-conversation': { x1: 66, y1: 52, x2: 40, y2: 52 },
  'celery-llm': { x1: 72, y1: 42, x2: 58, y2: 18 },
  'celery-qdrant': { x1: 72, y1: 42, x2: 58, y2: 36 },
  'celery-memory': { x1: 80, y1: 46, x2: 86, y2: 36 },
}
