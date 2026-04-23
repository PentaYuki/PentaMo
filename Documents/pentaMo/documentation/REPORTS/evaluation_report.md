# 📊 Evaluation & Continuous Feedback Loop

As an AI Product Engineer, we don't just build; we measure and iterate. This report defines what "Success" looks like for PentaMo and analyzes early failure modes from the provided test data.

---

## 1. Defining Success (The North Star)

Our main hypothesis is that **Proactive Tool Orchestration** (instead of passive chatting) will lead to higher trust and conversion.

### Core Metrics
| Category | Metric | Definition | Target |
| :--- | :--- | :--- | :--- |
| **Business** | **Appointment Rate** | % of chats leading to a booked viewing. | > 40% |
| **Business** | **Time-to-Match** | Avg number of turns until a relevant listing is found. | < 6 turns |
| **Quality** | **Slot Coverage** | % of critical info (Budget/Loc) collected. | > 90% |
| **Safety** | **Risk Escalation Rate** | % of legal/fraud risks correctly handed to humans. | 100% |

---

## 2. Error Analysis (The "Fail Fast" Audit)

We analyzed the failures in the provided `chat_history.jsonl` (C1, C2, C3) to identify system weaknesses.

### Case C1: Price Mismatch & Negotiation
- **What happened**: Seller wanted 32tr, Buyer capped at 25tr (28% gap).
- **Failure Mode**: The Agent's current passive response ("Let me ask...") lacks a **Counter-offer Strategy**.
- **Root Cause**: The orchestrator didn't trigger `negotiate_price` because the gap was seen as a "risk" but not an "actionable challenge".
- **Fix**: Lower the `PRICE_MISMATCH` threshold to 15% and implement a `suggest_alternatives` tool for gaps > 30%.

### Case C2: Document & Compliance Risk
- **What happened**: Seller admitted paperwork is "pending withdrawal" (rút hồ sơ).
- **Success**: The system correctly detected `DOCUMENT_RISK`.
- **Improvement**: Instead of just warning, the Agent should trigger an **Automated Legal Guide** or escalate to the "Transaction Security" team immediately.

### Case C3: Intermediary Rejection
- **What happened**: Seller explicitly rejected middle-men ("môi giới").
- **Failure Mode**: Standard chatbot behavior often ignores the emotional nuance of "distrust".
- **Root Cause**: Intent classifier saw "Chat", but missed the "Negative Sentiment toward Platform".
- **Fix**: Update the `ActionPlanner` to recognize **Platform Distrust** signals and trigger an immediate "Transparency Handoff".

---

## 3. The Continuous Feedback Loop

We implement a **Closed-Loop System** to ensure the Agent learns from every interaction:

1.  **Collection**: Every conversation is logged with a `satisfaction_score` (1-5) and an `outcome` (Booked/Dropped).
2.  **Synthesis**: Failed conversations (Score < 3) are automatically flagged for **Human-in-the-Loop (HITL)** review.
3.  **Iteration**: 
    -   **Few-shot Injection**: High-performing responses are harvested and added to the LLM's prompt as examples.
    -   **Tool Refinement**: If `detect_risks` misses a keyword, that keyword is added to the orchestrator's regex patterns.
    -   **Vector Refresh**: The Semantic Cache (FAISS) is updated weekly with "Corrected" responses.

---

## 4. Conclusion

By focusing on **Slot Coverage** and **Risk Escalation**, we move beyond "Toy Chatbots" into **Reliable Agents**. The next phase will focus on fine-tuning the `ActionPlanner` to handle multi-party negotiation in C1 more aggressively.
