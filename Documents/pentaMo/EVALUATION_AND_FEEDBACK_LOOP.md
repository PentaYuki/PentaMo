# Evaluation Plan & Feedback Loop Implementation

## Visão Geral

Este documento descreve a **estratégia de avaliação** e **closed-loop feedback** implementada no PentaMo para medir sucesso, identificar problemas, e iterar continuamente.

---

## 1. Definição de Sucesso (3 Níveis)

### Nível 1: Task Success (Negócio)

| Métrica | Definition | Target | Medição |
|---------|------------|--------|----------|
| **Match Success Rate** | % de queries que resultam em listagens relevantes encontradas | ≥ 85% | Total queries with results / Total queries |
| **Booking Rate** | % de conversas que levam a appointment agendado | ≥ 40% | Bookings / Conversations |
| **Close Rate** | % de appointments que resultam em compra | ≥ 25% | Purchases / Appointments |
| **Time-to-Match** | Quantas mensagens até primeiro match relevante | < 8 msg | Avg message count until first match |
| **Time-to-Book** | Quantas mensagens até appointment agendado | < 15 msg | Avg message count until booking |
| **Time-to-Close** | Quantos dias de conversa até compra | < 7 days | Avg time from start to purchase |

### Nível 2: Quality (Operacional)

| Métrica | Definition | Target | Medição |
|---------|------------|--------|----------|
| **Slot Coverage** | % de informações críticas coletadas | ≥ 90% | (filled slots) / (required slots) |
| **Intent Accuracy** | % de intents identificadas corretamente | ≥ 92% | (correct intents) / (total intents) |
| **Entity Extraction Accuracy** | % de entidades extraídas sem erro | ≥ 88% | (correct entities) / (total entities) |
| **Tool Correctness** | % de ferramentas chamadas apropriadamente | ≥ 95% | (correct tools) / (total tools called) |
| **Safety Compliance** | % de violações de segurança detectadas | 100% | (violations caught) / (violations attempted) |
| **Hallucination Rate** | % de afirmações não suportadas | < 2% | (false claims) / (total claims) |
| **Response Relevance** | % de respostas relevantes à pergunta | ≥ 94% | (relevant) / (total responses) |

### Nível 3: User Experience (Experiência)

| Métrica | Definition | Target | Medição |
|---------|------------|--------|----------|
| **Avg Response Latency** | Tempo médio de resposta | < 2s (cache) / < 5s (LLM) | P50 latency |
| **P99 Latency** | 99º percentil de latência | < 8s | P99 latency |
| **Cache Hit Rate** | % de respostas vindas de cache | ≥ 35% | (cache hits) / (total requests) |
| **Uptime** | % de tempo sistema disponível | ≥ 99.5% | (up time) / (total time) |
| **Error Rate** | % de requisições com erro | < 1% | (errors) / (total requests) |
| **User Satisfaction** | NPS (Net Promoter Score) | ≥ 40 | Post-chat survey |
| **Feedback Submission Rate** | % de users que deixam feedback | ≥ 50% | (feedback given) / (conversations) |

---

## 2. Arquitetura de Logging

### 2.1 Event Types & Schemas

#### **Event 1: USER_MESSAGE**

```json
{
  "event_type": "USER_MESSAGE",
  "timestamp": "2026-02-05T09:00:30.123Z",
  "conversation_id": "conv-123",
  "sender_id": "user-456",
  "sender_type": "buyer",
  "message_text": "Mình muốn tìm xe tay ga Honda",
  
  "extracted": {
    "intent": "SEARCH",
    "intent_confidence": 0.92,
    "entities": {
      "brands": ["Honda"],
      "category": "tay_ga"
    }
  },
  
  "slot_coverage": {
    "budget": false,
    "brands": true,
    "location": false,
    "year": false,
    "covered_percent": 0.25
  }
}
```

#### **Event 2: AGENT_ACTION**

```json
{
  "event_type": "AGENT_ACTION",
  "timestamp": "2026-02-05T09:00:32.456Z",
  "conversation_id": "conv-123",
  
  "action": {
    "tool": "search_listings",
    "params": {
      "brands": ["Honda"],
      "limit": 10
    },
    "decision_reason": "Intent SEARCH detected. Brands: Honda."
  },
  
  "execution": {
    "duration_ms": 245,
    "success": true,
    "result_count": 5
  }
}
```

#### **Event 3: RESPONSE_GENERATED**

```json
{
  "event_type": "RESPONSE_GENERATED",
  "timestamp": "2026-02-05T09:00:33.890Z",
  "conversation_id": "conv-123",
  
  "response": {
    "text": "Dạ bên em có 5 chiếc Honda tay ga phù hợp với yêu cầu...",
    "source": "llm",  // or "cache"
    "llm_model": "ollama/llama2",
    "temperature": 0.3
  },
  
  "metrics": {
    "tokens_used": 125,
    "latency_ms": 2345
  },
  
  "grounding": {
    "references_search_results": true,
    "hallucinations_detected": 0
  }
}
```

#### **Event 4: RISK_DETECTED**

```json
{
  "event_type": "RISK_DETECTED",
  "timestamp": "2026-02-05T09:02:45.123Z",
  "conversation_id": "conv-123",
  
  "risk": {
    "type": "DOCUMENT_RISK",
    "severity": "HIGH",
    "description": "Giấy tờ chưa sang tên",
    "keywords_found": ["chưa sang tên", "chờ hồ sơ"],
    "confidence": 0.98
  },
  
  "recommendation": "ESCALATE"
}
```

#### **Event 5: FEEDBACK**

```json
{
  "event_type": "FEEDBACK",
  "timestamp": "2026-02-05T09:15:00.000Z",
  "conversation_id": "conv-123",
  
  "feedback": {
    "rating": "positive",  // positive, negative, neutral
    "score": 4,  // 1-5 scale
    "comment": "Agente rápido e hữu ích"
  },
  
  "user_context": {
    "sender_type": "buyer",
    "conversation_stage": "MATCHING"
  }
}
```

#### **Event 6: OUTCOME**

```json
{
  "event_type": "OUTCOME",
  "timestamp": "2026-02-05T10:30:00.000Z",
  "conversation_id": "conv-123",
  
  "outcome": {
    "final_stage": "CLOSING",
    "booked_appointment": true,
    "appointment_date": "2026-02-08",
    "purchase_completed": false,
    "days_to_close": 1,
    "total_messages": 15
  },
  
  "success_metrics": {
    "slot_coverage_final": 0.95,
    "risks_escalated": 1,
    "tool_calls_made": 3
  }
}
```

### 2.2 Event Collection Pipeline

```
┌─ Process message in orchestrator
│
├─ STEP 1: Extract intent + entities
│  └─ Log: USER_MESSAGE event
│
├─ STEP 2: Decide action
│  └─ Log: AGENT_ACTION event
│
├─ STEP 3: Generate response
│  └─ Log: RESPONSE_GENERATED event
│
├─ STEP 4: Detect risks
│  └─ Log: RISK_DETECTED event (if applicable)
│
└─ STEP 5: Persist + save
   ├─ Store message in chat_messages table
   ├─ Update conversation state
   └─ Emit event to Kafka/logging queue

Async Thread:
├─ Collect events
├─ Batch write to PostgreSQL
├─ Emit to analytics pipeline (BigQuery, etc)
```

---

## 3. Erro Analysis Framework

### 3.1 Error Classification

```
┌─ Intent Misclassification
│  ├─ Why: Ambiguous message, context missing
│  ├─ Example: "32tr cao quá" → classified as CHAT, should be NEGOTIATE
│  ├─ Fix: Add price_comparison detection
│  └─ Frequency: ~8% of messages
│
├─ Entity Extraction Errors
│  ├─ Why: Regex not matching, new pattern
│  ├─ Example: "tầm 25 triệu" → not matched (expects "tr" or "triệu")
│  ├─ Fix: Add pattern r'tầm\s+(\d+)'
│  └─ Frequency: ~5% of entities
│
├─ Tool Calling Errors
│  ├─ Why: Wrong tool chosen, or no tool called when needed
│  ├─ Example: Price mismatch detected but no escalation offered
│  ├─ Fix: Improve ActionPlanner priority logic
│  └─ Frequency: ~3% of conversations
│
├─ Hallucinations
│  ├─ Why: LLM generates unsupported claims
│  ├─ Example: Agent says "Xe này bao giờ hết bảo hành" but not mentioned by seller
│  ├─ Fix: Add grounding check, constrain LLM context
│  └─ Frequency: ~1-2% of responses
│
└─ Safety Violations
   ├─ Why: Malicious input not caught
   ├─ Example: Payment fraud attempt not detected
   ├─ Fix: Improve safety checker patterns
   └─ Frequency: < 0.1% (hopefully!)
```

### 3.2 Error Analysis Workflow

```python
def analyze_errors_weekly():
    """
    Automated weekly error analysis
    """
    
    # 1. Collect all failures from last week
    failures = query_db("""
        SELECT * FROM chat_messages
        WHERE positive_feedback_count = 0
        AND timestamp > NOW() - INTERVAL 7 DAY
        LIMIT 100
    """)
    
    # 2. Classify errors
    for message in failures:
        error_type = classify_error(message)
        # error_type: INTENT, ENTITY, TOOL, HALLUCINATION, SAFETY
        
        log_error_analysis({
            "conversation_id": message.conversation_id,
            "message_id": message.id,
            "error_type": error_type,
            "root_cause": analyze_root_cause(message),
            "fix_recommendation": generate_fix(error_type)
        })
    
    # 3. Generate report
    report = generate_error_report(failures)
    # → Send to Slack, save to database
    
    # 4. Update patterns
    for fix in report['recommendations']:
        if fix['priority'] == 'HIGH':
            implement_fix(fix)
            # Update regex, add keyword, improve prompt, etc
```

### 3.3 Exemplo: Deep Dive em C1 (Price Negotiation)

```
Problem Statement:
- Conversation C1 ended without booking
- Buyer: "32tr cao quá, chỉ mua tối đa 25-26tr"
- Agent response: "Dạ em tìm hết database nhưng chưa thấy xe ưng ý"
- Issue: Agent ignored price negotiation opportunity

Root Cause Analysis:
1. Intent Detection
   ✓ Correct intent: NEGOTIATE (gap 28%)
   ✗ But ActionPlanner didn't trigger detect_risks

2. State Not Updated
   ✗ listing_context.price = 32tr não estava no state
   ✓ Fix: _update_state() não foi chamado after seller message

3. Risk Detection Missed
   ✗ price_gap calculation not triggered
   ✓ Threshold era 40%, gap é 28% → missed!

Action Items:
1. Lower price_gap threshold: 40% → 15%
2. Ensure _update_state() called after ALL messages
3. Add test case: gap 28% should trigger detect_risks()

Verification:
- Replay conversation through updated system
- Agent should now suggest: "Anh muốn thương lượng hoặc tìm xe khác?"
- Expected: +15% booking rate
```

---

## 4. Feedback Loop Implementation

### 4.1 Fase 1: Collect Outcomes

```
Timeline per Conversation:

Msg 1-N: Normal conversation
    ↓
End of Conversation: → Check outcome
    ├─ Did user book appointment? (Yes/No)
    ├─ Did user complete purchase? (Yes/No)
    ├─ How many messages? (N)
    ├─ How long? (timestamp end - start)
    └─ User satisfaction? (1-5 scale)

Post-Conversation (30 seconds after end):
    ├─ Ask user: "Agente hỗ trợ tốt?"
    ├─ Options: 👍 👎 (maybe add comment box)
    ├─ Store feedback in feedback table
    └─ Emit FEEDBACK event

Track in Database:
```sql
INSERT INTO conversation_outcomes (
  conversation_id,
  booked_appointment,
  purchased,
  days_to_close,
  total_messages,
  user_satisfaction_score,
  user_comment
) VALUES (...)
```

### 4.2 Fase 2: Correlate Data

```python
def weekly_analysis():
    """
    Analyze what works vs what doesn't
    """
    
    # 1. Group by key dimensions
    groups = {
        "by_mode": group_by(mode=['consultant', 'trader']),
        "by_lead_score": group_by(lead_score=[(0,20), (21,40), ...]),
        "by_intent": group_by(intent=['SEARCH', 'BOOK', ...]),
        "by_risk_level": group_by(risk=['none', 'low', 'high'])
    }
    
    # 2. Calculate success rate for each group
    for group_name, conversations in groups.items():
        success_rate = len([c for c in conversations if c.booked]) / len(conversations)
        print(f"{group_name}: {success_rate * 100:.1f}% booking rate")
    
    # Example output:
    # by_mode[consultant]: 35% booking rate
    # by_mode[trader]: 52% booking rate  ← Trader mode 48% better!
    #
    # by_lead_score[0-20]: 5% booking rate
    # by_lead_score[81-100]: 68% booking rate  ← Hot leads convert!
    #
    # by_intent[SEARCH]: 28% booking rate
    # by_intent[NEGOTIATE]: 45% booking rate  ← Negotiation intent converts better
    
    # 3. Identify top performer conversations
    winners = filter(conversations, c.positive_feedback == True and c.booked == True)
    
    # 4. Extract patterns from winners
    patterns = extract_patterns(winners)
    # patterns = [
    #   {
    #     "conversation_id": "conv-123",
    #     "agent_response": "Anh muốn thương lượng hoặc tìm xe khác?",
    #     "outcome": "BOOKED",
    #     "success_factor": "Clear options presented"
    #   },
    #   ...
    # ]
```

### 4.3 Fase 3: Iterate

```
┌─ Winner Extraction
│
├─ Identify top 10 conversations by booking rate + satisfaction
├─ Extract agent responses that led to booking
├─ Find common patterns:
│  ├─ Phrases: "thương lượng", "xem xe", "hỗ trợ"
│  ├─ Actions: Offered alternatives, addressed objections
│  ├─ Timing: When were these offered? (early vs late)
│  └─ Context: What was lead_score, stage, risk_level?
│
└─ Update System Prompt
   ├─ Add top phrases to few-shot examples
   ├─ Adjust response template for trader mode
   ├─ Increase temperature slightly (more helpful tone)
   └─ Test new variant in A/B test
```

### 4.4 A/B Testing Framework

```
Design: 2-way test (Control vs Treatment)

Control (60% traffic):
├─ Original prompt
├─ Original few-shot examples
├─ Original tool routing logic
└─ Metric: booking_rate_control

Treatment (40% traffic):
├─ Updated prompt (with winner patterns)
├─ Updated few-shot examples
├─ Enhanced tool routing
└─ Metric: booking_rate_treatment

Run Duration: 7 days (≥500 conversations per variant)

Analysis:
├─ booking_rate_control = 38%
├─ booking_rate_treatment = 41%
├─ Difference = +3% (absolute)
├─ Lift = (41 - 38) / 38 = 7.9% (relative)
├─ Confidence: 95% (p-value < 0.05)
└─ Decision: ✓ STATISTICALLY SIGNIFICANT → Deploy treatment

Long-term:
├─ Keep measurement for regression
├─ Monitor if lift persists after deployment
├─ A/B test next hypothesis (different tool routing, etc)
```

### 4.5 Loop de Feedback Contínuo

```
Week 1: Baseline
├─ Control (100%): 38% booking rate
└─ Identify top 10 conversations

Week 2: A/B Test
├─ Design treatment based on winners
├─ Run 60/40 control/treatment
├─ booking_rate_control: 38%
├─ booking_rate_treatment: 41% (+3%)
└─ Decision: Deploy treatment

Week 3: Deployment
├─ Roll out treatment (100%)
├─ Monitor for regressions
├─ New baseline: 41% booking rate
└─ Identify next hypothesis (e.g., risk escalation)

Week 4: Next Iteration
├─ Design treatment 2 (better risk handling)
├─ Run 60/40 control (old) / treatment (new)
├─ booking_rate_treatment: 43% (+2% more)
└─ Deploy if significant

Pattern:
├─ Week 1: 38% (baseline)
├─ Week 3: 41% (+3% from iteration 1)
├─ Week 5: 43% (+2% from iteration 2)
├─ Week 7: 45% (+2% from iteration 3)
├─ Week 9: 47% (+2% from iteration 4)
└─ Target: 50%+ within 10 weeks
```

---

## 5. Dashboards & Reporting

### 5.1 Executive Dashboard

```
┌─────────────────────────────────────────────────────┐
│  PentaMo AI Agent - Executive Dashboard             │
├─────────────────────────────────────────────────────┤
│                                                      │
│  📊 KEY METRICS (Last 7 Days)                       │
│  ├─ Total Conversations: 1,245                      │
│  ├─ Booking Rate: 42% (↑3% vs last week)            │
│  ├─ Close Rate: 28% (↑2%)                          │
│  ├─ Avg Response Time: 2.3s (↓0.2s)               │
│  ├─ User Satisfaction: 4.2/5.0 (↑0.1)             │
│  └─ Cache Hit Rate: 42% (→ stable)                │
│                                                      │
│  🎯 CONVERSION FUNNEL                              │
│  Conversations: 1,245                              │
│      ↓ (42%)                                        │
│  Bookings: 523                                      │
│      ↓ (28%)                                        │
│  Purchases: 146                                     │
│                                                      │
│  ⚠️ TOP ISSUES                                      │
│  1. Intent misclassification (8% of messages)      │
│  2. Price negotiation detection (15% of C1 cases)  │
│  3. Document risk escalation (10% missed)          │
│                                                      │
│  📈 WEEKLY TRENDS                                   │
│  [Line chart: booking rate increasing]             │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 5.2 Operational Dashboard

```
┌──────────────────────────────────────────────┐
│  PentaMo - Operations Dashboard              │
├──────────────────────────────────────────────┤
│                                               │
│  ⚡ SYSTEM HEALTH                           │
│  Uptime: 99.8% | CPU: 45% | Memory: 62%    │
│  Ollama: ✓ Active | Gemini: ✓ Fallback OK  │
│  FAISS: 850 vectors (325MB)                 │
│                                               │
│  📊 LATENCY DISTRIBUTION (Last Hour)         │
│  P50: 2.1s | P95: 4.8s | P99: 7.2s         │
│  Cache Hits (P50): 0.003s                   │
│  LLM Calls (P50): 2.8s                      │
│                                               │
│  🔴 ERRORS (Last Hour)                      │
│  Total: 12 errors                            │
│  - Ollama timeout: 4                         │
│  - DB connection: 3                          │
│  - Safety violation: 1                       │
│  - Unknown: 4                                │
│                                               │
│  📝 MESSAGE PROCESSING (Last Hour)          │
│  Total: 234 messages                         │
│  Intent distribution:                        │
│  - SEARCH: 65% (152)                        │
│  - CHAT: 20% (47)                           │
│  - BOOK: 10% (23)                           │
│  - Other: 5% (12)                           │
│                                               │
└──────────────────────────────────────────────┘
```

---

## 6. Reporting Schedule

### 6.1 Daily Reports (Automated)

```
Time: 9:00 AM (Send to Slack #metrics)

Content:
├─ Yesterday's metrics
│  ├─ Conversations: 180
│  ├─ Booking rate: 42%
│  ├─ Errors: 5
│  └─ Notable issues: None
├─ 7-day trend
│  └─ Booking rate: ↑3% vs last week ✓
└─ Action items
   └─ Priority: None
```

### 6.2 Weekly Reports (Manual Review)

```
Time: Every Monday 10:00 AM

Content:
├─ Executive summary (3-5 bullets)
├─ Metrics scorecard (all KPIs)
├─ Error analysis (top 10 failures)
├─ A/B test results (if running)
├─ Data quality issues (if any)
└─ Recommendations for next week
```

### 6.3 Monthly Reports (Deep Dive)

```
Time: First Monday of month

Content:
├─ Comprehensive metrics analysis
├─ Cohort analysis (by user segment, region, etc)
├─ ML model performance (if applicable)
├─ Infrastructure cost analysis
├─ Feedback themes (user comments)
├─ Competitor benchmarking (if available)
└─ Q next quarter roadmap
```

---

## 7. Implementação (Checklist)

### Phase 1: Infrastructure (Week 1)

- [ ] Setup event logging table (PostgreSQL)
- [ ] Implement event emission in orchestrator
- [ ] Setup batch writing to database
- [ ] Create basic dashboard (Excel/Sheets)
- [ ] Test event collection with 10 conversations

### Phase 2: Analysis (Week 2-3)

- [ ] Implement error classification
- [ ] Generate weekly error analysis script
- [ ] Implement correlation analysis
- [ ] Generate weekly reports
- [ ] Share first error analysis report with team

### Phase 3: A/B Testing (Week 4-5)

- [ ] Design A/B testing framework
- [ ] Implement traffic splitting logic
- [ ] Run first A/B test (hypothesis: better prompts)
- [ ] Measure statistical significance
- [ ] Document results + deploy winner

### Phase 4: Automation (Week 6-8)

- [ ] Automate daily reports
- [ ] Automate weekly error analysis
- [ ] Automate A/B test data collection
- [ ] Setup alerting (booking rate drops, etc)
- [ ] Create operational dashboard

### Phase 5: Iteration (Week 9+)

- [ ] Run continuous A/B tests (new hypothesis each week)
- [ ] Implement feedback from operations
- [ ] Scale and optimize based on learnings
- [ ] Prepare for production deployment

---

## 8. Sucesso Criteria

| Fase | Métrica | Target |
|------|---------|--------|
| **Week 1-2** | Evento collection | 100% de events logados |
| **Week 3-4** | Error analysis | Top 5 error patterns identificados |
| **Week 5-6** | A/B testing | First test com p < 0.05 |
| **Week 7-8** | Automation | 90%+ reports automated |
| **Week 9-12** | Iteration | +10% booking rate improvement |

---

## 9. Próximos Passos

1. ✅ Definir métricas (seção 1 acima)
2. ⏳ Implementar event logging (seção 2)
3. ⏳ Setup error analysis pipeline (seção 3)
4. ⏳ Design + run first A/B test (seção 4)
5. ⏳ Create dashboards (seção 5)
6. ⏳ Setup reporting schedule (seção 6)

---

## Conclusão

A **avaliação contínua** + **feedback loop fechado** é essencial para:
- Medir progresso contra objetivos de negócio
- Identificar problemas rapidamente
- Iterar baseado em dados (não adivinhação)
- Melhorar systematicamente a taxa de conversão

**Espera-se:** +10% de aumento na booking rate em 12 semanas através de iterações baseadas em feedback.

