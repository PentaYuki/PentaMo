# 🧠 State Schema & Conversation Context

This document explains the structured state management within the PentaMo AI Agent. Following the principle of **"Deterministic Logic + Generative Flexibility"**, our state schema ensures that the agent maintains a consistent understanding of buyer needs while allowing for natural conversation.

## 1. Schema Rationale

An AI Agent for a marketplace must distinguish between **Unstructured Chat History** (raw text) and **Structured Intent & Constraints** (normalized data). We chose a hierarchical JSON structure stored in a `JSONB` column (PostgreSQL) for the following reasons:

- **Evolvability**: We can add new constraints (e.g., "insurance preference") without migrating database columns.
- **Contextual Awareness**: The schema maps directly to the LLM's prompt, allowing for "Zero-Inference" context retrieval.
- **Audition & Logging**: Every state transition is traceable, enabling precise error analysis.

---

## 2. Core Schema Structure

```json
{
  "conversation_id": "c1",
  "participants": {
    "buyer_id": "uuid-123",
    "seller_id": "uuid-456",
    "agent_id": "an"
  },
  "lead_stage": "MATCHING",
  "constraints": {
    "budget": { "min": 23000000, "max": 25000000, "currency": "VND" },
    "location": "Ho Chi Minh City",
    "brands": ["Honda", "Yamaha"],
    "odo_max": 20000,
    "year_min": 2020
  },
  "listing_context": {
    "id": "listing-789",
    "price": 32000000,
    "paperwork_status": "Pending"
  },
  "risk_signals": [
    { "type": "PRICE_MISMATCH", "severity": "MEDIUM", "gap": 0.28 }
  ],
  "open_questions": [
    "Is the price negotiable?",
    "When is the paperwork ready?"
  ],
  "next_best_action": {
    "action": "detect_risks",
    "tool": "ActionPlanner",
    "reason": "Price gap of 28% exceeds 15% threshold."
  }
}
```

---

## 3. Key Components

### 🚦 Lead Stages
The `lead_stage` enum guides the Agent's behavior and tool access:
- `DISCOVERY`: Identifying needs and gathering constraints.
- `MATCHING`: Proposing specific listings from the database.
- `NEGOTIATION`: Handling price gaps or term disagreements.
- `APPOINTMENT`: Scheduling viewing sessions.
- `CLOSING`: final check on paperwork and payment.

### 🔍 Constraints (Entity Extraction)
Signals are extracted from chat history using a hybrid approach (Regex for speed + LLM for nuance). 
- **Stored**: Quantifiable filters (budget, year, ODO).
- **Not Stored**: Passing sentimental comments or generic greetings (kept in raw logs only).

### 🚩 Risk Signals
Proactive detection of "deal-breakers":
- **Price Mismatch**: Automatically triggered if (Asking Price - Budget) / Asking Price > 15%.
- **Paperwork Risk**: Triggered by keywords like "pending docs" or "unclear ownership".
- **Safety**: Out-of-scope topics are caught by the `SafetyGuard` component.

---

## 4. State vs. Memory
| Feature | State Schema | Memory (FAISS) | Raw Logs |
| :--- | :--- | :--- | :--- |
| **Purpose** | Immediate Action & Context | Experience & Learning | Legal Audit & Detail |
| **Persistence** | Relational DB (JSONB) | Vector DB (Semantic) | Log Files / JSONL |
| **Accessibility** | Real-time (Low Latency) | K-Nearest Search | Background Analysis |

> [!TIP]
> This "Three-Tier Memory Architecture" allows the agent to be incredibly fast while maintaining long-term awareness of user preferences.
