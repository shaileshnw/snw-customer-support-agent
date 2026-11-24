"""FastAPI backend with Razorpay quantity-based billing."""
import os
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from api.agent_core import run_agent
from api.billing import increment_usage

load_dotenv()

app = FastAPI(title='Support Agent API', version='1.0.0')

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'usage.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS usage (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, message TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS subscriptions (customer_id TEXT PRIMARY KEY, subscription_id TEXT, quantity INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

init_db()

class ChatRequest(BaseModel):
    message: str
    customer_id: str = 'demo_customer'

class ChatResponse(BaseModel):
    reply: str
    customer_id: str
    billing_reported: bool

@app.post('/chat', response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        reply = run_agent(request.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Log usage
    conn = sqlite3.connect(DB_PATH)
    conn.execute('INSERT INTO usage (customer_id, message) VALUES (?, ?)', (request.customer_id, request.message))
    conn.commit()

    # Increment Razorpay subscription quantity
    billing_ok = False
    row = conn.execute('SELECT subscription_id, quantity FROM subscriptions WHERE customer_id = ?', (request.customer_id,)).fetchone()
    if row:
        sub_id, current_qty = row
        result = increment_usage(sub_id, current_qty)
        if result['success']:
            conn.execute('UPDATE subscriptions SET quantity = ? WHERE customer_id = ?', (current_qty + 1, request.customer_id))
            conn.commit()
            billing_ok = True
        else:
            print('⚠️ Razorpay update failed:', result['error'])
    else:
        print('⚠️ No subscription for', request.customer_id, '- billing skipped')

    conn.close()
    return ChatResponse(reply=reply, customer_id=request.customer_id, billing_reported=billing_ok)

@app.post('/subscribe/{customer_id}')
async def subscribe(customer_id: str):
    """Create a Razorpay subscription for a customer."""
    from api.billing import create_subscription
    result = create_subscription(customer_id)
    if not result['success']:
        raise HTTPException(status_code=500, detail=result['error'])
    sub = result['subscription']
    conn = sqlite3.connect(DB_PATH)
    conn.execute('INSERT OR REPLACE INTO subscriptions (customer_id, subscription_id, quantity) VALUES (?, ?, 0)', (customer_id, sub['id']))
    conn.commit()
    conn.close()
    return {'subscription_id': sub['id'], 'authorization_url': sub['short_url']}

@app.get('/health')
async def health():
    return {'status': 'ok'}

@app.get('/usage/{customer_id}')
async def get_usage(customer_id: str):
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute('SELECT COUNT(*) FROM usage WHERE customer_id = ?', (customer_id,)).fetchone()[0]
    conn.close()
    return {'customer_id': customer_id, 'total_messages': count}
