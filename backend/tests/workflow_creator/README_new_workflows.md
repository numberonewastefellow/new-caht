# New Workflow Use Cases

Two new multi-agent workflow examples demonstrating both orchestration modes.

---

## 05 — Content Marketing Pipeline (Sequential Mode)

**File:** `workflows/05_content_marketing.json`
**Workflow ID:** Created via `create_workflows.py`
**Mode:** `sequential` — fixed pipeline, each step feeds the next

### How It Works

A 4-stage content production pipeline. Each agent receives the user's original request plus ALL previous agent outputs, building on each other's work:

```
User Brief
  │
  ▼
┌─────────────────────┐
│  Topic Researcher    │  Researches angles, data, audience, competitor gaps
│  (has search tools)  │  Output: structured research brief
└─────────┬───────────┘
          │ research_brief
          ▼
┌─────────────────────┐
│  Content Writer      │  Writes 800-1200 word blog post from the brief
│  (no tools)          │  Output: publish-ready markdown article
└─────────┬───────────┘
          │ blog_draft
          ▼
┌─────────────────────┐
│  SEO Optimizer       │  Adds keywords, meta tags, internal links, alt-text
│  (no tools)          │  Output: optimized post + SEO scorecard
└─────────┬───────────┘
          │ seo_optimized
          ▼
┌─────────────────────┐
│  Social Media        │  Creates LinkedIn, Twitter/X, Instagram posts
│  Adapter (no tools)  │  Output: copy-paste ready social content
└─────────────────────┘
```

### Agents (Personas)

| Agent | Purpose | Tools |
|-------|---------|-------|
| WF Topic Researcher | Finds trending angles, data points, competitor gaps, title options | Internal Search |
| WF Content Writer | Writes engaging blog posts with hooks, structure, examples | None |
| WF SEO Optimizer | Optimizes for search: keywords, meta description, internal links, alt-text | None |
| WF Social Media Adapter | Creates platform-specific posts: LinkedIn (2), Twitter/X (3), Instagram (1+reel) | None |

### Test Command

```bash
python create_workflows.py --run <ID> "Write a blog post about why small businesses should adopt AI tools in 2026. Target audience: small business owners who are not tech-savvy but curious about AI."
```

### Expected Output Flow

1. **Topic Researcher** produces a structured brief with:
   - Target audience definition
   - 3-4 unique content angles
   - 5-7 data-backed core points
   - Competitor gap analysis
   - 3 title options
   - Tone/style recommendation

2. **Content Writer** uses the brief to write a full blog post:
   - Compelling hook opening
   - H2/H3 structured sections
   - Real-world examples
   - Clear call-to-action
   - Meta description

3. **SEO Optimizer** enhances the post:
   - SEO-friendly title (under 60 chars)
   - Meta description (under 160 chars)
   - Primary + 3-5 secondary keywords
   - Full rewritten post with keyword placement
   - [INTERNAL LINK] and [IMAGE] suggestions
   - SEO scorecard (density, readability, length)

4. **Social Media Adapter** creates ready-to-post content:
   - LinkedIn: 1 thought leadership post + 1 carousel outline
   - Twitter/X: thread hook + stat tweet + question tweet
   - Instagram: caption + reel script outline
   - All include [BLOG LINK] placeholder

### Why Sequential Mode?

Each step transforms the output for a different purpose. The flow is deterministic — research always feeds writing, writing always feeds SEO, SEO always feeds social. No routing decisions needed.

---

## 06 — Personal Finance Advisor (LLM-Decision Mode)

**File:** `workflows/06_finance_advisor.json`
**Workflow ID:** Created via `create_workflows.py`
**Mode:** `llm_decision` — orchestrator routes to the right specialist(s)

### How It Works

An AI financial advisory team. The orchestrator analyzes the user's question and decides which specialist(s) to consult. Simple questions go to one expert; complex questions get input from 2-3 specialists.

```
User Question
  │
  ▼
┌──────────────────────────────────────────┐
│           ORCHESTRATOR (LLM)             │
│  Analyzes question → routes to expert(s) │
│  Synthesizes final recommendation        │
└──────┬──────┬──────┬──────┬──────────────┘
       │      │      │      │
       ▼      ▼      ▼      ▼
   ┌──────┐┌──────┐┌──────┐┌──────┐
   │Budget││Invest││ Tax  ││ Debt │
   │Analyst││Advisor││Strat.││Mgr  │
   └──────┘└──────┘└──────┘└──────┘
```

### Routing Logic

The orchestrator decides based on question type:

| Question Type | Primary Agent | May Also Call |
|---------------|--------------|---------------|
| Spending, saving, emergency fund | Budget Analyst | — |
| Stocks, ETFs, retirement, portfolio | Investment Advisor | Tax Strategist |
| Deductions, filing, tax-advantaged accounts | Tax Strategist | Investment Advisor |
| Student loans, credit cards, payoff strategy | Debt Manager | Investment Advisor |
| "Got a bonus/windfall" | Budget Analyst | Investment Advisor + Tax Strategist |
| "Pay off debt or invest?" | Debt Manager | Investment Advisor |
| "Retirement planning" | Investment Advisor | Tax Strategist |
| "Buying a house" | Budget Analyst | Debt Manager |

### Agents (Personas)

| Agent | Specialty | Output Format |
|-------|-----------|---------------|
| WF Budget Analyst | Income/expense analysis, 50/30/20 rule, emergency fund targets, quick savings wins | Budget table + monthly targets |
| WF Investment Advisor | Portfolio allocation, account priority (401k→IRA→HSA→taxable), specific ETF/fund names | Risk profile + allocation % + fund picks |
| WF Tax Strategist | Tax-advantaged accounts, deductions, tax-loss harvesting, bracket management | Tax moves ranked by impact + estimated savings |
| WF Debt Manager | Avalanche vs snowball comparison, consolidation analysis, payoff timeline | Strategy comparison + monthly payment plan + debt-free date |

### Test Commands

**Debt-focused question (routes to Debt Manager):**
```bash
python create_workflows.py --run <ID> "I'm 28 years old, earning 85000 USD per year. I have 25000 in student loans at 6.5% interest and 5000 in credit card debt at 22% APR. I also have 10000 in savings. I want to start investing but I'm not sure if I should pay off debt first. What should I do?"
```

**Bonus allocation (routes to Budget + Investment + Tax):**
```bash
python create_workflows.py --run <ID> "I just received a 20000 dollar year-end bonus. I'm 32, single, earning 110k per year in Texas (no state tax). I contribute 4% to my 401k getting full employer match. Monthly expenses are about 4000 dollars. I have 15000 in 401k, 8000 in savings (no Roth IRA, no HSA, no brokerage account), and zero debt. No big purchases planned. How should I allocate this 20000 bonus between emergency fund, investments, and tax-advantaged accounts?"
```

### Expected Output — Debt Question

1. **Orchestrator** identifies this as a debt-vs-invest question
2. **Debt Manager** is called with the full context:
   - Debt inventory with exact balances and rates
   - Avalanche vs snowball comparison with total interest + timeline
   - Recommendation to pay CC first ($5k at 22% > investing returns)
   - What to do with the $10k savings (balanced: $5k CC payoff + $4k emergency + $1k to student loan)
   - Monthly payment plan for remaining student loan
   - Consolidation analysis
   - Debt-free date projection
3. **Orchestrator** may also call **Investment Advisor** for the "when to start investing" aspect
4. **Final synthesis** with top 3-5 actionable recommendations

### Expected Output — Bonus Question

1. **Orchestrator** identifies this as a multi-faceted bonus allocation question
2. **Budget Analyst** provides:
   - Emergency fund gap calculation ($20k target - $8k = $12k needed)
   - Recommended split: $12k emergency + $7k Roth IRA + $1k brokerage
   - Quick wins to increase monthly savings
3. **Investment Advisor** adds:
   - Portfolio allocation for the Roth IRA (e.g., 80% US stocks / 15% international / 5% bonds)
   - Specific fund recommendations (VTI, VXUS, BND)
   - Account priority order (401k match → Roth IRA → HSA → taxable)
4. **Tax Strategist** adds:
   - Maximize Roth IRA ($7k limit) for tax-free growth
   - Consider HSA if HDHP eligible ($4,150 limit)
   - Increase 401k from 4% to 10%+ for tax bracket management
5. **Final synthesis** combining all three into a prioritized action plan

### Why LLM-Decision Mode?

Different financial questions need different experts. A "how to invest" question doesn't need the Debt Manager. A "pay off debt or invest" question needs both. The orchestrator intelligently routes based on context, avoiding unnecessary agent calls while ensuring all relevant perspectives are covered.

### Configuration Notes

- `max_calls_per_agent: 1` — each specialist can only be called once per query (prevents repetitive calls)
- `max_steps: 12` — allows orchestrator to call up to 4 agents + thinking cycles
- `timeout_seconds: 1200` — 20 minute timeout (finance questions can be complex)

---

## Setup & Run

### Create both workflows:
```bash
cd backend/tests/workflow_creator

# Create Content Marketing Pipeline
python create_workflows.py --file workflows/05_content_marketing.json --no-icons

# Create Personal Finance Advisor
python create_workflows.py --file workflows/06_finance_advisor.json --no-icons
```

### List workflows to get IDs:
```bash
python create_workflows.py --list
```

### Run with test messages:
```bash
# Sequential: Content Marketing
python create_workflows.py --run <ID> "Write a blog post about remote work productivity tips for 2026"

# LLM-Decision: Finance Advisor
python create_workflows.py --run <ID> "I have 50k in savings, no debt, earning 90k. Should I buy a house or invest?"
```

### Delete if needed:
```bash
python create_workflows.py --delete <ID>
```

---

## Bug Fix: `_apply_input_mapping` (Sequential Workflows)

During testing, a bug was found in `workflow_engine.py`'s `_apply_input_mapping()` function. The function only replaced `$output_key.output` format but the JSON convention uses `$output_key` (without `.output`). This affected ALL sequential workflows with explicit `input_mapping`.

**Fix applied:** The function now supports both patterns:
```python
# Replace step output references — support both $key.output and $key
for output_key, output in context.step_outputs.items():
    resolved = resolved.replace(f"${output_key}.output", output)
for output_key, output in context.step_outputs.items():
    resolved = resolved.replace(f"${output_key}", output)
```

**Workaround (before fix is deployed):** Omit `input_mapping` from steps — the default behavior automatically passes ALL previous step outputs to each subsequent step, which works well for pipeline workflows.
