# State Schema & Conversation Management

## Visão Geral

Este documento descreve em detalhes o **esquema de estado estruturado** mantido por cada conversa no PentaMo, a estratégia de armazenamento, e como o agente usa esse estado para tomar decisões.

---

## 1. Estrutura Completa de Estado

### Root Level Structure

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "participants": {},
  "lead_stage": "NEGOTIATION",
  "mode": "trader",
  "constraints": {},
  "listing_context": {},
  "open_questions": [],
  "risks": {},
  "next_best_action": {},
  "summary": "",
  "message_count": 7,
  "lead_score": 65,
  "temperature": "warm",
  "recent_messages": [],
  "updated_at": "2026-02-05T09:03:50Z"
}
```

### 1.1 Participants

```json
{
  "participants": {
    "buyer_id": "buyer-uuid-123",
    "seller_id": "seller-uuid-456",
    "agent_id": "system"
  }
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `buyer_id` | UUID | Identificador do comprador |
| `seller_id` | UUID | Identificador do vendedor |
| `agent_id` | String | ID do agente (sempre "system") |

### 1.2 Lead Stage

```json
{
  "lead_stage": "DISCOVERY"
}
```

| Estágio | Descrição | Transição |
|---------|-----------|-----------|
| `DISCOVERY` | Buyer explorando, definindo critérios | → MATCHING (after search) |
| `MATCHING` | Agent oferece listagens relevantes | → NEGOTIATION (if price gap) |
| `NEGOTIATION` | Discussão de preço/termos | → APPOINTMENT ou volta MATCHING |
| `APPOINTMENT` | Appointment agendado | → CLOSING (after visit) |
| `CLOSING` | Deal finalizado/payment iniciado | → COMPLETED |
| `COMPLETED` | Compra finalizada com sucesso | (Terminal) |
| `DROPPED` | Lead abandonado | (Terminal) |
| `CANCELLED` | Conversa cancelada | (Terminal) |

**Transições de Estado:**

```
DISCOVERY
    ↓ (search_listings call)
MATCHING
    ↓ (if price_gap > 15%)
NEGOTIATION
    ├─→ APPOINTMENT (if book_appointment call)
    ├─→ COMPLETED (if purchase confirmed)
    └─→ DROPPED (if buyer unresponsive)
```

### 1.3 Mode

```json
{
  "mode": "consultant"
}
```

| Modo | Quando | Prompt Style |
|------|--------|-------------|
| `consultant` | Buyer explorando, questions | Educacional, informativo |
| `trader` | Buyer focado em transação | Comercial, direto |

Atualizado via `_detect_mode()` em cada mensagem.

### 1.4 Constraints (Restrições de Busca)

```json
{
  "constraints": {
    "budget": {
      "min": 23000000,
      "max": 27000000,
      "currency": "VND"
    },
    "brands": ["Honda", "Yamaha"],
    "models": ["SH", "Air Blade"],
    "location": "TP Hồ Chí Minh",
    "location_alternatives": ["Bình Dương", "Đồng Nai"],
    "year_min": 2020,
    "year_max": 2026,
    "odo_max": 20000,
    "odo_unit": "km",
    "color_preference": ["Đen", "Xanh"],
    "condition": "Tốt",
    "paperwork_required": true,
    "financing_needed": false,
    "exclude_brands": ["China"],
    "must_have_features": ["ABS", "Keyless"]
  }
}
```

**Quando Populated:**
- `budget`: Quando buyer menciona preço ("25tr", "tầm 30 triệu")
- `brands`: Quando buyer menciona marca ("Honda", "Yamaha")
- `location`: Quando buyer menciona khu vực ("HCM", "Hà Nội")
- `year_min`: Quando buyer menciona đời ("2020+", "2021")
- `odo_max`: Quando buyer menciona "odo thấp" ou valor específico
- `paperwork_required`: Quando buyer menciona "giấy tờ" ou "chính chủ"

### 1.5 Listing Context (Veículo Atual em Discussão)

```json
{
  "listing_context": {
    "id": "listing-uuid-789",
    "seller_id": "seller-uuid-456",
    "brand": "Honda",
    "model": "Air Blade",
    "model_year": 2021,
    "model_line": "Honda Air Blade 125cc",
    "engine_cc": 125,
    "color": "Xanh",
    "condition": "Rất mới",
    "price": 32000000,
    "price_original": 32000000,
    "suggested_price": 28000000,
    "odo": 19000,
    "odo_unit": "km",
    "province": "TP Hồ Chí Minh",
    "district": "Q1",
    "address": "123 Nguyễn Huệ, Q1, HCM",
    "ownership_status": "Chính chủ",
    "paperwork_status": "Chưa sang tên, chờ rút hồ sơ",
    "images": [
      "https://cdn.pentamo.com/listings/l789/front.jpg",
      "https://cdn.pentamo.com/listings/l789/side.jpg"
    ],
    "documents": [
      "https://cdn.pentamo.com/listings/l789/reg_cert.jpg"
    ],
    "verification_status": "PENDING",
    "created_at": "2026-02-05T08:00:00Z"
  }
}
```

**Quando Populated:**
- Quando seller oferece um veículo específico
- Quando agent busca listings e seleciona um para mostrar
- Atualizado quando seller fornece novos detalhes

### 1.6 Open Questions (Dúvidas em Aberto)

```json
{
  "open_questions": [
    {
      "id": "q1",
      "category": "price",
      "text": "Há possibilidade de negociar o preço?",
      "asked_by": "buyer",
      "asked_at": "2026-02-05T09:00:30Z",
      "answered": false
    },
    {
      "id": "q2",
      "category": "paperwork",
      "text": "Quando pode estar pronto para sang tên?",
      "asked_by": "buyer",
      "asked_at": "2026-02-05T09:01:00Z",
      "answered": false
    }
  ]
}
```

**Utilizado para:**
- Rastrear tópicos não resolvidos
- Priorizá-los na próxima resposta
- Gerar "next_best_action"

### 1.7 Risks (Sinais de Risco Detectados)

```json
{
  "risks": {
    "level": "MEDIUM",
    "overall_severity": "MEDIUM",
    "flags": [
      {
        "id": "r1",
        "type": "PRICE_MISMATCH",
        "description": "Gap 28% entre orçamento (25tr) e preço solicitado (32tr)",
        "severity": "MEDIUM",
        "confidence": 0.95,
        "keywords_found": ["32tr cao quá"],
        "detected_at": "2026-02-05T09:02:30Z",
        "recommendation": "Suggest thương lượng ou tìm xe khác",
        "resolved": false
      },
      {
        "id": "r2",
        "type": "DOCUMENT_RISK",
        "description": "Giấy tờ chưa sang tên, đang chờ rút hồ sơ gốc",
        "severity": "HIGH",
        "confidence": 0.98,
        "keywords_found": ["chưa sang tên", "chờ rút hồ sơ"],
        "detected_at": "2026-02-05T09:02:45Z",
        "recommendation": "ESCALATE để tư vấn pháp lý chuyên sâu",
        "resolved": false
      }
    ]
  }
}
```

**Risk Types:**

| Tipo | Severity | Action |
|------|----------|--------|
| `PRICE_MISMATCH` | MEDIUM | Suggest negotiation |
| `DOCUMENT_RISK` | HIGH | Escalate + legal review |
| `FRAUD_RISK` | CRITICAL | Block + Alert admin |
| `INTERMEDIARY_REJECTION` | MEDIUM | Handoff to human |
| `PAYMENT_PRESSURE` | CRITICAL | Block + Alert |

### 1.8 Next Best Action

```json
{
  "next_best_action": {
    "tool": "detect_risks",
    "params": {
      "type": "PRICE_MISMATCH",
      "gap": 0.28,
      "listing_id": "listing-uuid-789"
    },
    "reason": "Khoảng cách giá 28% quá lớn. Cần đàm phán hoặc tìm xe khác.",
    "confidence": 0.95,
    "priority": "HIGH",
    "suggested_response": "Anh muốn thương lượng hoặc em tìm xe khác trong tầm giá?"
  }
}
```

**Decidido por:** `ActionPlanner.decide_next_action()`

**Utilizado para:**
- Orquestração da próxima ação
- Explanação de "por que" (auditoria)
- Teste em modo debug

### 1.9 Summary (Resumo Compacto)

```json
{
  "summary": "Buyer procura Honda/Yamaha tay ga dưới 26tr ở HCM, ano 2020+, odo baixo. Vendor ofereceu Air Blade 2021 32tr com giấy tờ pendente. Há gap de preço 28% + risco legal. Recomendação: Negotiação de preço ou explorar alternativas."
}
```

**Atualizado:**
- A cada 25 mensagens (compaction)
- Quando há grandes mudanças de estado

### 1.10 Lead Score & Temperature

```json
{
  "message_count": 7,
  "lead_score": 65,
  "lead_score_breakdown": {
    "budget_clarity": 20,
    "preference_clarity": 15,
    "engagement_level": 15,
    "purchase_intent": 10,
    "tool_usage": 5,
    "temporal_freshness": 0
  },
  "temperature": "warm",
  "temperature_details": {
    "emoji": "🔥",
    "meaning": "Strong interest, progressing toward decision"
  }
}
```

**Temperature Scale:**

| Score | Emoji | Label | Action |
|-------|-------|-------|--------|
| 0-20 | ❄️ | Cold | Generic offer |
| 21-40 | 🌨️ | Cool | Reminder campaign |
| 41-60 | 😐 | Lukewarm | Engagement needed |
| 61-80 | 🔥 | Warm | Acceleration push |
| 81-100 | 🌡️ | Hot | Close/final objection |

### 1.11 Recent Messages (Context Window)

```json
{
  "recent_messages": [
    {
      "sequence": 5,
      "sender": "buyer",
      "text": "32tr cao quá, mình chỉ mua tối đa 25-26tr thôi"
    },
    {
      "sequence": 6,
      "sender": "agent",
      "text": "Để mình hỏi thêm..."
    },
    {
      "sequence": 7,
      "sender": "seller",
      "text": "Xe mình giữ kỹ, máy móc zin..."
    }
  ]
}
```

**Propósito:** Fornecer contexto conversacional ao LLM sem re-ler 100+ mensagens

---

## 2. Estratégia de Persistência

### Banco de Dados

**Tabela Principal:**
```sql
CREATE TABLE conversations (
  id UUID PRIMARY KEY,
  buyer_id VARCHAR,
  seller_id VARCHAR,
  listing_id VARCHAR,
  state JSONB,                    -- ← Armazena todo o state acima
  memory_summary TEXT,            -- ← Resumo compacto
  lead_stage ENUM(...),           -- ← Desnormalizado para queries rápidas
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  channel_id VARCHAR,             -- ← Para chat direct bridge
  tags VARCHAR[]                  -- ← Para filtragem rápida
);
```

### Frequência de Update

| Evento | Frequência | Operação |
|--------|-----------|----------|
| Nova mensagem | Por mensagem | `UPDATE state = ...` |
| Mudança lead_stage | ~5x/conversa | `UPDATE lead_stage = ...` |
| Compaction (summary) | A cada 25 msgs | `UPDATE memory_summary = ...` |

### Versionamento (Auditoria)

```
Versão N → Versão N+1:
- Timestamp cada mudança
- Log delta (what changed)
- Permite rollback se necessário
```

---

## 3. Atualização de Estado

### Fluxo de Update

```python
def _update_state(message: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract entities from message, merge com estado atual
    """
    state = current_state.copy()
    
    # 1. Extract budget
    if "25tr" in message:
        state["constraints"]["budget"]["max"] = 25_000_000
    
    # 2. Extract brands
    if "Honda" in message:
        state["constraints"]["brands"].append("Honda")
    
    # 3. Extract location
    if "HCM" in message:
        state["constraints"]["location"] = "TP Hồ Chí Minh"
    
    # 4. Update lead_stage
    if listing_offered:
        state["lead_stage"] = "MATCHING"
    
    # 5. Detect risks
    if "chưa sang tên" in message:
        state["risks"]["flags"].append({
            "type": "DOCUMENT_RISK",
            ...
        })
    
    # 6. Calculate next action
    state["next_best_action"] = planner.decide_next_action(message, state)
    
    state["updated_at"] = datetime.utcnow().isoformat()
    return state
```

---

## 4. Recuperação de Estado

### Padrão: Context Window

```python
def generate_prompt(state: Dict) -> str:
    """
    Builds LLM prompt from state (2KB max)
    """
    prompt = f"""
    Contexto da Conversa:
    
    Cliente: {state['participants']['buyer_id']}
    Veículo em Discussão: {state['listing_context']['brand']} {state['listing_context']['model']}
    
    Orçamento: {state['constraints']['budget']['min']}-{state['constraints']['budget']['max']} VND
    Localização: {state['constraints']['location']}
    
    Preço Solicitado: {state['listing_context']['price']}
    Gap: {gap}%
    
    Riscos: {[f['type'] for f in state['risks']['flags']]}
    
    Próxima Ação Sugerida: {state['next_best_action']['tool']}
    
    Mensagens Recentes:
    {format_recent_messages(state['recent_messages'])}
    """
    return prompt
```

**Tamanho Típico:** ~2KB (suffcient for context)

---

## 5. Exemplos de Evolução de Estado

### Exemplo 1: Descoberta → Negociação

```
MSG 1: "Mình muốn tìm xe tay ga Honda, tầm 25tr"
├─ constraints.brands = ["Honda"]
├─ constraints.budget = {min: 23tr, max: 27tr}
├─ lead_stage = "DISCOVERY"

MSG 2: [Agent searches, finds 5 listings]
├─ lead_stage = "MATCHING"

MSG 3: [Seller offers Air Blade 32tr]
├─ listing_context = {brand: Honda, price: 32tr, ...}
├─ risks.flags.append({type: PRICE_MISMATCH, gap: 28%})
├─ lead_stage = "NEGOTIATION"
├─ next_best_action = {tool: detect_risks, ...}

MSG 4: "32tr cao quá, có cái nào khác không?"
├─ open_questions.append({text: "Xe khác nào?", ...})
├─ lead_stage = "MATCHING" (back to search)
```

### Exemplo 2: Risco de Documentação

```
MSG 1: "Giấy tờ sao vậy?"
MSG 2: [Seller: "Chưa sang tên, chờ rút hồ sơ"]
├─ risks.flags.append({
│   type: "DOCUMENT_RISK",
│   severity: "HIGH",
│   recommendation: "ESCALATE"
├─ next_best_action = {tool: detect_risks, ...}
├─ next_best_action.suggested_response = 
│   "Dạ em sẽ kiểm tra quy trình sang tên..."
```

---

## 6. Design Trade-offs

### Por que JSON vs Colunas Separadas?

**JSON:**
```sql
state JSONB contains: {constraints, risks, next_action, ...}
Vantagem: Sem migração, escalável
Desvantagem: Queries indexing difícil
```

**Colunas Separadas:**
```sql
ALTER TABLE ADD COLUMN budget_min INT;
ALTER TABLE ADD COLUMN budget_max INT;
...
Vantagem: Queries rápidas, indexing fácil
Desvantagem: Migrações caras, inflexível
```

**Escolha:** JSON + Desnormalização seletiva
```sql
state JSONB,
lead_stage ENUM,  -- Desnormalizado para queries rápidas
created_at TIMESTAMP,  -- Indexado
```

### Por que Compaction a cada 25 mensagens?

```
25 mensagens = ~5-10 minutos de conversa
Após compaction:
- Resumo em 2-3 sentenças
- Últimas 5 mensagens mantidas
- Total state size: 2KB → 1KB (50% reduction)

Sem compaction:
- 100 mensagens = 20KB state
- LLM context window esmagado
- Latência aumenta
```

---

## Conclusão

O esquema de estado é **compacto mas rico**, permitindo:
- ✅ Contexto suficiente para LLM gerar resposta apropriada
- ✅ Auditoria completa (rastreamento de mudanças)
- ✅ Escalabilidade (JSON permite novos campos)
- ✅ Performance (queries rápidas em desnormalizados)

**Próximos Passos:**
1. Validar schema com 100+ real conversations
2. Adicionar mais campos conforme necessário
3. Otimizar queries no PostgreSQL JSONB
4. Implementar versionamento completo para rollback
