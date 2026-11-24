# 🎧 Customer Support Agent — Sellable SaaS MVP

A production-shaped AI support agent with a real API, a real UI, and a real billing meter. Built with **LangChain v1 + FastAPI + Streamlit**, deployed to Railway + Streamlit Cloud, and billed via **Razorpay** using quantity-based subscriptions. The agent resolves tickets end-to-end with three tools — order lookup, policy search, and human escalation — and the escalation policy lives in the system prompt, not in code.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![LangChain](https://img.shields.io/badge/LangChain-v1-green)](https://python.langchain.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.40-red)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Live demo:** [Chat UI](https://your-app.streamlit.app) · [API docs](https://your-api.up.railway.app/docs) · [Health](https://your-api.up.railway.app/health)

> Replace the three URLs above with your deployed endpoints before publishing.

## What This Project Is (and Isn't)

**It is:** a working SaaS product. A customer opens a chat, describes an issue, the AI resolves it or escalates to a human, and every resolved ticket increments a billing meter that charges the customer monthly.

**It is not:** a notebook demo. Notebooks can't be sold. This project has five layers that each do one job and can be replaced independently.

**Layer: Agent** — `api/agent_core.py`
Only file that imports LangChain. Swap the framework → nothing else changes.

**Layer: API** — `api/main.py`
The product customers pay for. UI is one disposable client.

**Layer: Billing** — `api/billing.py`
Only file that imports the payment SDK. Swap processor → one file.

**Layer: UI** — `app/streamlit_app.py`
Talks to the API over HTTP. Replace with mobile, Slack, or nothing.

**Layer: Data** — `data/usage.db`
The billing meter. Source of truth for "how many tickets did this customer resolve."


## Architecture
Customer
│
▼
Streamlit UI ──POST /chat──▶ FastAPI ──▶ LangChain Agent ──▶ OpenAI
│
├──▶ SQLite (usage log + subscription cache)
│
└──▶ Razorpay (quantity-based subscription)


**Three design rules that make it production-shaped:**

1. **Billing never blocks support.** If the payment provider is down, the agent still answers. The response includes `billing_reported: false` and you reconcile later. A support agent that dies because a billing API hiccupped is worse than an unbilled ticket.

2. **Local state is a cache.** The `subscriptions` table in SQLite stores the last-known quantity; Razorpay is the source of truth. Reconcile at billing cycle end.

3. **Parameterized SQL everywhere.** `conn.execute('... VALUES (?, ?)', (a, b))` — never f-strings. The `?` placeholder treats input as data, never code.

## The Agent Design 

### The loop is not a pipeline

The agent reads the message, decides which tool to call, inspects the result, and either responds or calls another tool. There is no hardcoded `if/else` — the LLM chooses at every turn.
Customer message → LLM reads → decides tool(s) → calls → inspects → responds or escalates

### Tool docstrings are the real prompt

Each `@tool` docstring tells the LLM **when** to use the tool, not what it does:

```python
@tool
def lookup_order(order_id: str) -> str:
    """Look up order status by order ID. Use for questions about order status,
    shipping, delivery date, or what items are in an order.
    Do NOT use for policy questions."""
A vague docstring = wrong tool calls = angry customers. Every sentence should change a decision the model makes.

Escalation is a policy, not a fallback
The system prompt in api/agent_core.py defines exact escalation triggers:

"Escalate ONLY for: (1) damaged items, (2) lost packages, (3) billing discrepancies, (4) explicit manager requests."

Without precise rules, the agent either escalates everything (annoying) or nothing (unsafe). The balance lives in the prompt — not in code.

Deterministic by default
temperature=0 — same input, same output. Creativity is a bug in support. Temperature 0 is the first step to making LLM behavior testable.

Fully observable
Every decision trace is inspectable: message → AI tool call → tool result → final response. This is how you debug "why did the agent say that?" without re-running blindly.

Why Razorpay Instead of Stripe
Most SaaS tutorials default to Stripe. That breaks for a large share of the world's developers.

Sign up from India — Stripe is invite-only and company-biased; Razorpay is self-serve and sole-proprietor friendly.

Payment methods — Stripe handles cards and some wallets; Razorpay handles UPI, RuPay, netbanking, cards, and wallets.

Onboarding time — Stripe takes weeks to months; Razorpay takes same day to 48 hours.

Metered billing — Stripe has a first-class MeterEvent primitive; Razorpay uses quantity-based subscription updates.

PCI compliance — Both offload card handling.

If you're in the US/EU, use Stripe. If you're in India, or selling to Indian customers, Razorpay is the practical choice. The architecture isolates the billing layer — swapping processors is one file (api/billing.py) and one SDK install.

The billing pattern in this repo — quantity-based subscriptions — generalizes across providers. Stripe calls it metered billing; Razorpay calls it subscription quantity updates. The idea is identical: charge unit_price × usage_count at the end of each cycle.

The Billing Model
Create a Plan in the payment dashboard: ₹1/month per unit (or $0.10/unit — any per-unit price).

On POST /subscribe, create a subscription with quantity=1.

Every POST /chat increments quantity by 1: subscription.update(sub_id, {'quantity': n+1}).

At end of cycle, the processor charges quantity × unit_price.

A customer who resolves 50 tickets pays ₹51 (₹1 activation + ₹50 usage). Honest usage-based pricing that scales with value delivered.

The three billing invariants every SaaS needs:

Graceful degradation — processor outages don't break the product.

Eventual consistency — local cache is not the truth; the processor is.

PCI offload — you never see card numbers. The processor handles compliance. You see IDs only.

Tech Stack
LLM — OpenAI gpt-4o-mini. ~₹0.10 per ticket. Tool calling supported.

Agent framework — LangChain v1 (create_agent). v1 API only — do not use deprecated create_react_agent.

Backend — FastAPI + Uvicorn. Auto-generated docs at /docs.

Frontend — Streamlit. Uses st.chat_input and st.session_state.

Billing — Razorpay. Quantity-based subscription model.

Database — SQLite (stdlib). Zero setup; swap for Postgres at scale.

Secrets — python-dotenv + platform Variables. .env locally; Railway Variables in prod.

Deployment — Railway (API) + Streamlit Cloud (UI). Both watch GitHub and auto-redeploy on push.

Project Structure

support-agent/
├── .env                    ← secrets (never committed)
├── .gitignore              ← excludes .env, data/, __pycache__
├── Procfile                ← Railway startup command
├── requirements.txt
├── README.md
├── LICENSE
├── api/
│   ├── __init__.py
│   ├── agent_core.py       ← agent + tools + system prompt
│   ├── billing.py          ← payment processor client
│   └── main.py             ← FastAPI endpoints
├── app/
│   └── streamlit_app.py    ← chat UI
└── data/
    └── usage.db            ← SQLite meter (generated at first run)
Quickstart
Prerequisites
Python 3.10+

OpenAI account with ~$5 credit

Razorpay account (Test Mode is free)

GitHub account

Step 1 — Clone and install
bash
git clone https://github.com/YOUR_USERNAME/support-agent.git
cd support-agent
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
Step 2 — Create your .env
bash
cat > .env << EOF
OPENAI_API_KEY=sk-your-openai-key
RAZORPAY_KEY_ID=rzp_test_your-key-id
RAZORPAY_KEY_SECRET=your-key-secret
RAZORPAY_PLAN_ID=plan_your-plan-id
EOF
Getting the Razorpay values:

Razorpay dashboard → toggle Test Mode (top-right).

Settings → API Keys → Generate Test Key → copy Key ID + Secret.

Subscriptions → Plans → Create Plan:

Name: Support Agent Usage

Amount: 100 (paise — this is ₹1; do not enter 1, that's ₹0.01)

Currency: INR

Billing: Monthly, interval 1

Copy the Plan ID (starts with plan_).

Step 3 — Run locally
bash
# Terminal 1 — API
uvicorn api.main:app --reload --port 8000

# Terminal 2 — UI
API_URL=http://localhost:8000/chat streamlit run app/streamlit_app.py
API docs: http://localhost:8000/docs

Chat UI: http://localhost:8501

Step 4 — Test the full pipeline
bash
# Health
curl http://localhost:8000/health

# Chat before subscribing — billing will be skipped
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Where is ORD-1001?", "customer_id": "alice"}'

# Subscribe — returns an authorization URL
curl -X POST http://localhost:8000/subscribe/alice
# → {"subscription_id": "sub_...", "authorization_url": "https://rzp.io/..."}

# Open the authorization_url in a browser and complete the mandate (Test Mode)

# Chat again — billing now increments the subscription quantity
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Where is ORD-1001?", "customer_id": "alice"}'
# → {"reply": "...", "customer_id": "alice", "billing_reported": true}
Verify in three places:

Local DB: sqlite3 data/usage.db "SELECT * FROM usage WHERE customer_id='alice';"

Payment dashboard → Subscriptions → quantity should be 2

API response → billing_reported: true

API Reference
POST /chat
Resolve a customer message end-to-end.

Request:

json
{ "message": "Where is my order ORD-1002?", "customer_id": "alice" }
Response:

json
{
  "reply": "Order ORD-1002: USB-C Hub. Status: processing. Carrier: pending. ETA: 5 days.",
  "customer_id": "alice",
  "billing_reported": true
}
POST /subscribe/{customer_id}
Create a subscription and return an authorization URL.

json
{
  "subscription_id": "sub_MZ9x...",
  "authorization_url": "https://rzp.io/l/..."
}
Send authorization_url to the customer. They authorize the mandate; the subscription becomes active.

GET /usage/{customer_id}
json
{ "customer_id": "alice", "total_messages": 42 }
GET /health
json
{ "status": "ok" }
Deployment
API → Railway
Push the repo to GitHub (.gitignore keeps .env out).

Railway → New Project → Deploy from GitHub repo → select support-agent.

Railway detects Python and runs Procfile:

web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
Settings → Variables — add all four from your .env.

Settings → Networking → Generate Domain → copy URL.

Verify: curl https://YOUR-URL.up.railway.app/health

UI → Streamlit Cloud
Update the fallback URL in app/streamlit_app.py:

python
API_URL = os.getenv('API_URL', 'https://YOUR-RAILWAY-URL.up.railway.app/chat')
git add . && git commit -m "Point UI to prod API" && git push

share.streamlit.io → New app → repo → branch main → file app/streamlit_app.py → Deploy.

Both platforms watch GitHub — every git push triggers a redeploy.

Testing Checklist
Test in this order. Never build layer N+1 on top of a broken layer N.

Layer: Agent
Command — python -c "from api.agent_core import run_agent; print(run_agent('Where is ORD-1001?'))"
Expected — Order details in response.

Layer: Escalation
Command — run_agent('My keyboard arrived cracked')
Expected — Response mentions escalation.

Layer: Health
Command — curl localhost:8000/health
Expected — {"status": "ok"}

Layer: Chat
Command — curl -X POST localhost:8000/chat ...
Expected — Reply + billing_reported.

Layer: Subscribe
Command — curl -X POST localhost:8000/subscribe/alice
Expected — authorization_url returned.

Layer: Billing
Command — Authorize mandate, then chat again.
Expected — Razorpay quantity increments.

Layer: E2E
Command — Chat in Streamlit UI.
Expected — Response appears; /usage count rises.

Layer: Production
Command — Same tests against Railway URL.
Expected — Same behavior.

Troubleshooting
ImportError: cannot import name 'create_agent'
Cause — LangChain too old. Fix — pip install -U langchain, restart venv.

AuthenticationError from OpenAI
Cause — Wrong key or no credit. Fix — Check .env; add credit at platform.openai.com.

Address already in use
Cause — Stale uvicorn. Fix — pkill -f uvicorn.

/chat returns 500
Cause — Agent exception. Fix — Check API logs; usually OpenAI key or rate limit.

/usage returns 0 after chat
Cause — DB path wrong. Fix — DB_PATH should end in data/usage.db.

/chat prints "billing skipped"
Cause — No subscription for that customer. Fix — Call /subscribe/{customer_id} first.

subscription.update fails
Cause — Subscription not authorized. Fix — Customer must complete the short_url flow.

Railway 502
Cause — App crashes on import. Fix — Check Logs tab; often missing api/__init__.py.

Streamlit "could not reach server"
Cause — API_URL still localhost. Fix — Update fallback to Railway URL, push.

.env committed to GitHub
Cause — Forgot .gitignore. Fix — Rotate the OpenAI key immediately — assume compromised.

Roadmap
Replace mock ORDERS with Shopify API — 1 day — Works on real orders, 10× value.

Self-serve signup via payment link — 1 day — Customers onboard without you, 5×.

Conversation memory (MemorySaver) — 2 hours — Remembers customer name, 2×.

Human approval for escalations (HumanInTheLoopMiddleware) — 2 hours — Enterprise-ready, 3×.

50-ticket evaluation suite — 1 day — Proof it works, 5×.

Swap SQLite for Postgres — 4 hours — Multi-instance deploy, 3×.

Sentiment tool → auto-escalate angry customers — 2 hours — Reduced churn, 2×.

Contributing
PRs that improve clarity, add tests, or expand deployment options (Fly.io, Render, AWS Lambda) are welcome.

Fork the repo.

Create a branch: git checkout -b feature/your-feature.

Commit with a clear message.

Open a PR.

License
MIT — see LICENSE. Free to use, modify, and sell.

Contact
Built by Your Name — GitHub · LinkedIn

If this project helped you ship your own support agent, drop a ⭐ on the repo.


