# PentaMo AI Agent: High-Level Architecture (V3)

This document provides an accurate, code-backed overview of how the PentaMo AI Agent (An) operates in the current V3 implementation. Unlike previous conceptual designs, this guide reflects the actual files and logic present in the repository.

---

## 1. Core AI Components (The "Real" Files)

The AI logic is consolidated into four pillars:

| Component | File Path | Responsibility |
| :--- | :--- | :--- |
| **The Brain** | `backend/orchestrator_v3.py` | Manages the 8-step processing pipeline and conversation state. |
| **The Memory** | `services/faiss_memory.py` | Vector-based storage for Q&A cache and intent classification. |
| **The Skills** | `tools/handlers_v2.py` | Python functions for DB search, booking, and risk detection. |
| **The Planner** | `backend/action_planner.py` | Decides which tool to call based on the message. |

---

## 2. The Message Processing Pipeline (Step-by-Step)

When a user sends a message to `/api/conversations/{id}/messages`, the `AgentOrchestrator` executes the following sequence:

1.  **Safety Check** (`_check_safety`): Filters out-of-scope topics (e.g., cooking, politics).
2.  **State Update** (`_update_state`): Uses Regex and keywords to extract **Budget**, **Brands**, and **Location** into the session state.
3.  **Risk Detection** (`detect_risks`): Scans for fraud patterns, firm price signals, or document concerns.
4.  **Action Planning** (`planner.decide_next_action`): Determines if a specific action (like `book_appointment`) is required immediately.
5.  **Search Logic** (`_perform_search`): 
    *   Calls `parse_user_intent_for_search` to turn natural language into query params.
    *   Queries the `SellerListings` DB table.
    *   If results are found, it returns a formatted list of bikes immediately.
6.  **Mode Detection** (`_detect_mode`):
    *   Uses a FAISS-based classifier to decide between **Consultant** (advisory) and **Trader** (transactional).
    *   Falls back to keyword matching if FAISS confidence is low.
7.  **Cache Lookup** (`memory.search`): Checks if the exact question has a pre-approved answer in the FAISS vector database.
8.  **LLM Generation** (`llm_client.generate`): If no search results or cache hits occur, it calls the LLM (Ollama/Gemini) with a persona-specific system prompt.

---

## 3. Dual-Mode Logic

The Agent switches personas dynamically based on user intent:

### Consultant Mode (An)
*   **Persona**: Friendly vehicle advisor.
*   **Goal**: Discovery and advice. 
*   **Trigger**: General questions like "What bike is good for commuting?" or "Should I buy a Vision or a Lead?"

### Trader Mode (An)
*   **Persona**: Transactional analyst.
*   **Goal**: Matching inventory and facilitating deals.
*   **Trigger**: Specific inquiries like "Do you have an SH in red?" or "I want to see this bike tomorrow."

---

## 4. Tool Integration (The "Skills")

The AI has "Skill" functions that bridge the gap between chat and the database:

*   **`search_listings`**: A real SQLAlchemy query that filters by brand, price, year, and province.
*   **`book_appointment`**: Persists a record in the `Appointments` table when a viewing is requested.
*   **`detect_risks`**: Detects if a seller is too firm on price or if paperwork is missing.

---

## 5. Memory & Context Management

The system avoids "forgetting" by using a compact state object:
*   **Slot Filling**: The Agent tracks `budget`, `location`, and `brands`. It knows what info is missing.
*   **FAISS Indexing**: Intent samples are stored in `data/faiss/mode_classifier_index`. 
*   **History Compacting**: Long conversations are summarized periodically to stay within the LLM's context window.

---

## 6. How to Adjust the AI

If you want to change how the Agent behaves, look here:
*   **Change Tone/Persona**: Modify `COMMON_GUIDELINES` in `orchestrator_v3.py`.
*   **Add New Keywords**: Update `_update_state` in `orchestrator_v3.py`.
*   **Improve Intent Detection**: Add new samples to `scripts/seed_classifier.py` and run it.
*   **Tweak Search Logic**: Modify `parse_user_intent_for_search` in `tools/handlers_v2.py`.

> [!NOTE]
> The missing file `services/data_classification_service.py` was merged into `orchestrator_v3.py` to keep the code efficient and easier to maintain.
