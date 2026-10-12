# I Failed a Memory-Layer System Design. So I Built One.

*How studying Mem0-style architecture led me to CogLayer — a hands-on lab for the read/write memory loop behind modern AI agents.*

---

A few weeks ago I sat in a system-design conversation with a NYC-based startup.

They asked about a **memory layer** for their product: not “add a vector DB and hope,” but how an agent should **remember**, **update**, and **forget** facts about a user over time — without blocking the chat reply, without stuffing the entire history into every prompt, and without treating every similar embedding as the same fact.

I knew the buzzwords. I did not have a crisp mental model.

That stung enough that I stopped treating “memory” as a slide and started treating it as a system I could run on my machine. I read how **Mem0-style** pipelines are described in the wild — hybrid **retrieval + LLM judgment** — and implemented a small but complete version: **CogLayer**.

This article is the write-up I wish I’d had before that interview: the *why*, the *architecture*, and a path you can click through yourself.

---

## What “memory” actually means in agent systems

In chatbots, people often mix three different things:

1. **Context window** — whatever fits in the current prompt  
2. **Conversation history** — raw turns (“User said… Assistant said…”)  
3. **Durable memory** — atomic facts you want to keep across sessions  
   (“Alex prefers dark roast coffee,” “User adopted a dog named Scout”)

Mem0-style systems focus on (3), while still using (2) as fuel for extraction.

The hard part is not storing text. The hard part is:

- Finding *candidate* related memories cheaply  
- Deciding whether a new fact is **new**, a **refinement**, a **contradiction**, or **already known**  
- Updating storage **without making the user wait** on that judgment

That last point is why the architecture splits into two paths.

---

## The core idea: hybrid recall + judgment

Vector search is excellent at **cheap recall**:  
“Given this sentence, what are the top-s similar memories for this user?”

It is terrible at **semantic judgment** on its own.  
“Likes X” and “hates X” can sit next to each other in embedding space. Similarity will happily retrieve both. Only a model (or careful rules) can say: *update*, *delete*, or *noop*.

So the hybrid loop is:

| Piece | Job |
|--------|-----|
| **Embeddings / Qdrant** | Narrow the world to a few relevant memories |
| **LLM EXTRACT** | Pull durable candidate facts from a message pair + recent context |
| **LLM DECIDE** | Pick exactly one tool: `ADD` / `UPDATE` / `DELETE` / `NOOP` |
| **Async worker** | Apply the tool to the store so chat stays snappy |

Mem0 popularized this style of thinking for production agents. CogLayer is a **learning implementation** of that loop — not a clone of Mem0 Cloud, and not a claim to replace it. The goal is understanding you can demo and explain.

---

## Two paths: Read (sync) and Write (async)

### Read path — answer now

Every `/chat` request:

1. User sends a query  
2. Embed the query → **Qdrant top-k**, filtered by `user_id`  
3. Load recent conversation turns  
4. Build a prompt (instructions + memories + history + query)  
5. LLM generates a reply  
6. Return the reply immediately  
7. **Fire a background job** (`Celery` / RabbitMQ) — do not block the HTTP response

If you only remember one sentence from this article:

> **Chat latency belongs to the read path. Memory maintenance belongs to the write path.**

### Write path — learn in the background

The worker receives the **message pair** (user query + assistant reply):

1. Save the pair to the conversation store  
2. Build extraction prompt **P**: rolling **summary S** + last ~10 turns + new pair  
3. **LLM #1 — EXTRACT** → candidate facts  
4. For each candidate: embed → **top-s similar** memories for that user  
5. **LLM #2 — DECIDE** → one tool call  
6. Apply ops to **JSON memory store** and **Qdrant** (re-embed on ADD/UPDATE)

Summary S in CogLayer is computed **when the write path runs** (on each new pair). Some production designs cache summary with a *periodic* summarizer to save LLM cost at scale. For learning and for short demos, on-write summarization is the honest default.

---

## CogLayer: what I actually built

**Stack (deliberately boring and inspectable):**

- FastAPI chat API  
- Groq for LLM calls  
- Qdrant for vector search (user-scoped)  
- Celery + RabbitMQ for the write path  
- `memory_store.json` as the durable fact file (with 384-dim MiniLM embeddings)  
- React UI + an Excalidraw-style **Architecture lab** at `/learn`

**Demo users:** `alex`, `maya`, `jordan` — friendly keys mapped to stable UUIDs so one user’s coffee preference never leaks into another’s retrieval.

**Decide tools (the interesting part):**

- `ADD` — new fact; new UUID; embed; upsert Qdrant  
- `UPDATE` — refine an existing memory id; re-embed; upsert  
- `DELETE` — remove from JSON + Qdrant  
- `NOOP` — already covered; touch nothing  

That tool surface is what interviewers are often probing for when they say “memory layer,” even if they don’t use those four words.

---

## A concrete example

User (as Alex): *“I just adopted a golden retriever named Scout.”*

**Read path** might answer warmly using existing memories (coffee, Spanish practice, work habits) because those are already in Qdrant.

**Write path** then EXTRACTS something like:

- “The user adopted a golden retriever named Scout.”  
- “Scout is a golden retriever.”

Similar search finds nothing close enough → DECIDE returns **ADD** → JSON + Qdrant update.

Next query: *“What pet did I just adopt?”*  
Retrieval hits Scout. The reply is grounded. That’s the loop closing.

---

## Why system design interviews care about this

If you only say “we’ll use a vector database,” you miss:

- **Isolation** — every search scoped by user (and often agent/session)  
- **Non-blocking writes** — queue the maintenance job  
- **Idempotent identity** — stable memory IDs, not random duplicates every turn  
- **Contradiction handling** — DELETE / UPDATE, not infinite ADDs  
- **Dual stores** — searchable vectors *and* a source of truth for text/metadata  

Mem0-style design is a clean story for all of the above. Building even a thin version forces you to confront the failure modes: stale vectors after JSON updates, eager `.delay()` with no worker, EXTRACT inventing facts, DECIDE ADDing near-duplicates.

Those scars are better interview fuel than a perfect diagram.

---

## Learning it by seeing it

CogLayer includes an animated lab (Excalidraw-ish whiteboard UI) that steps through Read and Write:

- Play / Pause / Prev / Next  
- Nodes light up; arrows stay visible and highlight on the active hop  
- Each step has a short “what” and “why”

**Try it locally:**

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173/learn`  
Or open the standalone file `docs/architecture-lab.html` (same idea, no React build).

Repo: *[add your GitHub link]*  
Name: **CogLayer** — a memory *layer* you can reason about.

---

## What I would say in that interview now

If I walked back into that room, I’d sketch two boxes first: **Read** and **Write**.

I’d say:

> We retrieve top-k memories synchronously to answer.  
> After the reply, an async worker extracts facts, compares them to top-s neighbors, and applies ADD/UPDATE/DELETE/NOOP.  
> Embeddings are for recall. The LLM is for judgment.  
> Similarity alone can’t tell “loves” from “hates.”  
> The whole store never goes in the prompt.

Then I’d talk about user scoping, queues, and re-embedding on update.

That’s not a buzzword answer. That’s a system.

---

## Closing

I didn’t build CogLayer to compete with Mem0.  
I built it because I couldn’t *explain* a memory layer under pressure — and explanation without implementation is fragile.

If you’re learning agent memory, preparing for AI system design, or teaching the difference between RAG-for-documents and **memory-for-users**, walk the `/learn` path once. Then break it on purpose: kill the worker, skip Qdrant sync, force a contradictory fact. Watch what fails.

That’s how the diagram becomes intuition.

---

### Further reading / try next

- Mem0 docs and papers (product inspiration for the hybrid loop)  
- Qdrant filtering by payload (`user_id`)  
- Celery task boundaries: what must be sync vs async  
- Your own DECIDE prompt: favor `NOOP` over noisy `ADD`s  

*Built in public as a learning lab. Corrections and sharper interview questions welcome.*

---

**Suggested Medium tags:** Artificial Intelligence, System Design, LLM, Machine Learning, Software Engineering  

**Suggested subtitle:** A practical walkthrough of Mem0-style read/write memory — and the open learning build that came from failing the design once.
