# Mumzworld Gift Finder 🎁

A bilingual (English + Arabic) AI-powered gift recommendation tool for Mumzworld — the largest mother-and-baby e-commerce platform in the Middle East. Users describe what they need in natural language, and the system returns a curated shortlist of 3–5 products with reasoning, in both English and Arabic.

## What It Does

Users type a natural-language query like *"thoughtful gift for a friend with a 6-month-old, under 200 AED"* or *"هدية لصديقتي عندها طفل عمره 6 أشهر، الميزانية 200 درهم"*. The system:

1. **Parses** age, budget, occasion, and language from the query using deterministic regex
2. **Prompts** an LLM with a grounded product catalog (67 Mumzworld-style products)
3. **Validates** the response against a strict Pydantic v2 schema
4. **Grounds** the output by filtering any hallucinated product names against the catalog
5. **Renders** bilingual cards sorted by confidence (high → medium → low), with RTL Arabic support and graceful error states

---

## Two Non-Trivial LLM Engineering Techniques

### 1. Structured Output Enforcement (Schema-Grounded Generation)

Three layers of defense against LLM output instability:

- **`response_format: json_object`** — forces the model to emit raw JSON (no markdown fences, no preamble)
- **Pydantic `GiftResponse.model_validate()`** — validates schema compliance (confidence must be `high|medium|low`, max 5 recs, required fields)
- **Post-LLM grounding filter** (`_validate_grounding()`) — strips any product names the model hallucinated that don't exist in `catalog.json`

### 2. Eval-Driven Prompt Tuning (Automated Evaluation Suite)

- **12 test cases** spanning happy paths, edge cases, adversarial inputs, refusals, and bilingual stress tests
- **6 automated scoring dimensions** per case: schema validity, budget compliance, age appropriateness, uncertainty handling, recommendation count, catalog grounding
- Results saved to `eval/eval_results.json` for manual Arabic/English quality review
- This loop (change prompt → run eval → measure regression) is the core workflow for prompt engineering

---

## Setup & Run (< 5 minutes)

### Prerequisites
- Python 3.11+
- An [OpenRouter](https://openrouter.ai) API key (free tier works)

### Steps

```bash
# 1. Clone and enter
git clone https://github.com/manav-sh1/mumzworld.git
cd mumzworld

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -e ".[dev]"

# 4. Configure API key
copy .env.example .env
# Edit .env → set OPENROUTER_API_KEY=your_key_here

# 5. Run the server
uvicorn backend.main:app --reload --port 8000

# 6. Open browser
# → http://localhost:8000
```

### Run Evaluations

```bash
# With the server running in another terminal:
python -m eval.eval
```

---

## Architecture

```
User Input (EN or AR)
       │
       ▼
┌──────────────────┐
│  Input Parser     │  ← Regex-based: extracts age, budget, occasion, language
│  (parser.py)      │     Handles: "6-month-old", "newborn", "toddler", Arabic numerals
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Prompt Builder   │  ← Injects parsed params + full catalog JSON (~4K tokens)
│  (prompts.py)     │     System prompt enforces catalog grounding + bilingual quality
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  LLM Client       │  ← OpenRouter (Qwen 2.5 72B), 60s timeout, retry on rate limits
│  (client.py)      │     response_format: json_object, temp: 0.4
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Schema Validator  │  ← Pydantic v2 validation of GiftResponse
│  (schemas.py)      │     Fails loudly with SchemaValidationError — never silent
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Grounding Filter │  ← Strips hallucinated product names not in catalog.json
│  (service.py)     │     Logs a warning when filtering occurs
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Frontend         │  ← White/magenta Mumzworld-branded cards, EN↔AR toggle,
│  (HTML/CSS/JS)    │     RTL, confidence-sorted display, bilingual error messages
└──────────────────┘
```

### Why These Choices

| Decision | Reasoning |
|---|---|
| **Qwen 2.5 72B** | Notably better Arabic output than Llama 3.3; strong JSON mode; low cost on OpenRouter |
| **FastAPI** | Pydantic-native, async-ready, serves static files for zero-config frontend |
| **Vanilla JS** | No build step, no node_modules — graders can run it in seconds |
| **Mumzworld-branded UI** | White + magenta theme matching mumzworld.com brand identity |
| **Regex parser** | Simple, testable, transparent — no LLM needed for parameter extraction |
| **67-product catalog** | Large enough for diverse recommendations (~4K tokens), small enough for full-context injection |

---

## Reliability & Production Hardening

| Feature | Implementation |
|---|---|
| **Retry logic** | `tenacity` exponential backoff on rate limits only (auth errors fail fast) |
| **Timeout chain** | LLM client: 60s → frontend abort: 65s (backend always responds first) |
| **Exception hierarchy** | `GiftFinderError → LLMError \| SchemaValidationError \| CatalogError` |
| **Catch-all handler** | Route boundary catches unexpected errors with structured logging |
| **Empty response guard** | Validates LLM `choices[]` is non-empty before accessing |
| **Health check** | `GET /api/health` returns `{"status": "ok"}` |
| **Structured logging** | `structlog` with latency, token usage, and error context on every LLM call |
| **Grounding validation** | Post-LLM filter removes product names not found in catalog |

---

## Evals

### Scoring Rubric (per test case)

| Dimension | Score | Automated? |
|---|---|---|
| Schema validity | 0 or 1 | ✅ |
| Budget compliance | 0 or 1 | ✅ |
| Age appropriateness | 0 or 1 | ✅ |
| Uncertainty handling | 0 or 1 | ✅ |
| Recommendation count | 0 or 1 | ✅ |
| Catalog grounding | 0 or 1 | ✅ |
| EN reasoning quality | 0–2 | Manual |
| AR reasoning quality | 0–2 | Manual |
| Relevance | 0–2 | Manual |

**Automated max per case: 6 · Manual max per case: 6 · Total max: 12 per case**

### Test Cases

| ID | Description | Query | Expected |
|---|---|---|---|
| TC01 | Happy path EN | "gift for a friend with a 6-month-old, under 200 AED" | 1–5 recommendations |
| TC02 | Happy path AR | "هدية لصديقتي عندها طفل عمره 6 أشهر، الميزانية 200 درهم" | 1–5 recommendations |
| TC03 | No budget | "thoughtful gift for a newborn baby girl" | Clarification needed |
| TC04 | Budget too low | "gift for a 1-year-old, budget is 10 AED" | Refusal/empty |
| TC05 | No match (5yo) | "gift for a 5-year-old, budget 50 AED" | Refusal/empty |
| TC06 | Out of scope | "gift for a pregnant mom, something for herself" | Refusal |
| TC07 | Vague input | "something nice for a baby" | Clarification |
| TC08 | High budget | "gift for a 6-month-old, budget 1000 AED" | 3+ recommendations |
| TC09 | Specific interest | "educational gift for a 12-month-old who loves music" | 1+ relevant |
| TC10 | Bilingual mix | "gift for my friend's baby, 9 months, 150 AED, هدية مميزة" | 1+ recommendations |
| TC11 | Toddler edge | "gift for a 3-year-old toddler, budget 300 AED" | 1+ recommendations |
| TC12 | Non-gift query | "what is the best stroller on the market globally" | Refusal |

### Running Evals

```bash
python -m eval.eval
```

The script outputs a score table and saves raw LLM responses to `eval/eval_results.json` for manual EN/AR quality scoring.

---

## Tradeoffs

### Why This Problem
Gift recommendation is a genuine Mumzworld use case — it combines structured product data with natural language understanding and bilingual output. It's narrow enough to prototype well in 5 hours but complex enough to demonstrate prompt engineering, schema validation, and uncertainty handling.

### What I Rejected / Cut
- **Vector DB / RAG**: With 67 products (~5-10K tokens), full-catalog injection works fine. RAG adds complexity without benefit at this scale.
- **Real scraping**: Brief explicitly says don't scrape. Mock catalog is intentionally realistic.
- **React/Vite**: No build step keeps setup to under 2 minutes. Vanilla JS is sufficient for one page.
- **Database / auth**: Zero persistence needed for a recommendation prototype.
- **Fine-tuning**: Out of scope. Prompt engineering + structured output gets 90% of the quality.

### Model Choice
**Qwen 2.5 72B Instruct** (`qwen/qwen-2.5-72b-instruct`) via OpenRouter. Chosen because:
- Excellent Arabic — noticeably better than Llama 3.3 for Gulf Arabic tone
- Strong JSON mode compliance
- Low cost on OpenRouter ($0.36/M input tokens)

The `MODEL_NAME` env var can be changed to any OpenRouter model. Set it in `.env`.

### What I Would Build Next
1. **LLM-as-judge**: A second LLM call to rate Arabic output naturalness (1–5 scale)
2. **Real product API**: Replace mock catalog with Mumzworld's actual product feed
3. **Conversation memory**: Multi-turn refinement ("show me something cheaper")
4. **Occasion-aware ranking**: Baby shower → gift sets; birthday → statement pieces
5. **Caching**: Identical queries shouldn't hit the LLM twice

---

## Known Failure Modes

1. **Hallucination risk**: The model might invent products. Mitigation: system prompt forbids invention + post-LLM grounding filter strips names not in catalog.

2. **Arabic quality variance**: Model-dependent. Smaller models produce dictionary-like Arabic. We chose Qwen specifically for Arabic quality, but output should be manually reviewed. Also I have no knowledge about Arabic, so I cannot review for correctness manually.

3. **Budget edge cases**: A product at exactly the budget limit (e.g., 200 AED) should be included. The system prompt says "never suggest above" — the LLM handles this, not code-side filtering.

4. **Catalog coverage**: 67 products means some valid queries return 0–2 results. This is expected and documented in the refusal flow.

5. **Parser limitations**: The regex parser handles common patterns but may miss unusual phrasings. The LLM receives the raw query as a fallback.

---

## Tooling Transparency

- **Model**: Qwen 2.5 72B Instruct via OpenRouter
- **AI coding assistance**: Used Antigravity (Claude) for pair programming — architecture design, code generation, CSS design, and production hardening audit
- **What worked**: Structured output with `response_format: json_object` eliminates most parsing failures
- **What didn't**: Initial system prompt was too permissive — had to iterate 3x to get reliable refusals on out-of-scope queries
- **Key system prompt**: Committed in `backend/llm/prompts.py` — fully transparent

---

## Project Structure

```
mumzworld/
├── backend/
│   ├── core/
│   │   ├── config.py         # Settings (Pydantic v2 + pydantic-settings)
│   │   ├── exceptions.py     # Typed exception hierarchy
│   │   └── logging.py        # Structlog configuration
│   ├── llm/
│   │   ├── client.py         # OpenRouter API calls + retry + validation
│   │   └── prompts.py        # All prompt strings (zero inline prompts)
│   ├── gift_finder/
│   │   ├── schemas.py        # Pydantic models (request/response/parsed)
│   │   ├── parser.py         # Input parsing (age, budget, language)
│   │   ├── catalog.py        # Catalog loader with error handling
│   │   ├── catalog.json      # Mock product catalog (67 products)
│   │   └── service.py        # Orchestration + grounding filter
│   ├── api/
│   │   └── routes.py         # FastAPI endpoints (/recommend, /health)
│   └── main.py               # App entry point + lifespan
├── frontend/
│   ├── index.html            # Semantic HTML with <template> cards
│   ├── style.css             # Mumzworld-branded design system (white + magenta)
│   └── app.js                # Vanilla JS — i18n, RTL, confidence sorting
├── eval/
│   ├── test_cases.py         # 12 test case definitions
│   └── eval.py               # Automated evaluation runner
├── .env.example              # Environment template
├── pyproject.toml            # Dependencies + build config
└── README.md
```
