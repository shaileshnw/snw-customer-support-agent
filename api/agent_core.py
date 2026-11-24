"""Agent core: tools, LLM, and the run_agent() entry point."""
import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

load_dotenv()

ORDERS = {
    'ORD-1001': {'status': 'shipped', 'carrier': 'UPS', 'eta': '2 days', 'items': 'Wireless Mouse'},
    'ORD-1002': {'status': 'processing', 'carrier': None, 'eta': '5 days', 'items': 'USB-C Hub'},
    'ORD-1003': {'status': 'delivered', 'carrier': 'FedEx', 'eta': 'delivered', 'items': 'Laptop Stand'},
    'ORD-1004': {'status': 'delayed', 'carrier': 'DHL', 'eta': 'unknown', 'items': 'Mechanical Keyboard'},
}

POLICIES = {
    'returns': 'Returns are accepted within 30 days of delivery. Items must be unused and in original packaging.',
    'refunds': 'Refunds are processed within 5-7 business days after the returned item is received.',
    'shipping': 'Standard shipping takes 5-7 business days. Express shipping takes 2-3 business days.',
    'warranty': 'All electronics come with a 1-year manufacturer warranty.',
}

@tool
def lookup_order(order_id: str) -> str:
    """Look up order status by order ID. Use for questions about order status,
    shipping, delivery date, or what items are in an order."""
    order = ORDERS.get(order_id.upper().strip())
    if not order:
        return 'No order found with ID ' + order_id + '.'
    return (
        'Order ' + order_id + ': ' + order['items'] + '. '
        'Status: ' + order['status'] + '. '
        'Carrier: ' + (order['carrier'] or 'pending') + '. '
        'ETA: ' + order['eta'] + '.'
    )

@tool
def search_policy(topic: str) -> str:
    """Search company policies for returns, refunds, shipping, or warranty."""
    key = topic.lower().strip()
    for k, v in POLICIES.items():
        if k in key:
            return 'Policy (' + k + '): ' + v
    return 'No policy found. Available topics: returns, refunds, shipping, warranty.'

@tool
def escalate_to_human(ticket_summary: str, reason: str) -> str:
    """Escalate to a human support agent. Use ONLY for: damaged items, lost packages,
    billing discrepancies, or manager requests."""
    return '✅ Escalated to human. Reason: ' + reason + '. Summary: ' + ticket_summary

llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)

agent = create_agent(
    model=llm,
    tools=[lookup_order, search_policy, escalate_to_human],
    system_prompt=(
        'You are a friendly, efficient customer support agent for an e-commerce store. '
        'Your job is to resolve customer issues end-to-end using the available tools.\n\n'
        'RULES:\n'
        '1. Always be polite and acknowledge the issue.\n'
        '2. Use lookup_order for any order, shipping, or delivery question.\n'
        '3. Use search_policy for any policy question.\n'
        '4. Escalate ONLY for: damaged items, lost packages, billing issues, or manager requests.\n'
        '5. Never guess. If you cannot answer with tools, escalate.\n'
        '6. Keep responses concise and actionable.'
    ),
)

def run_agent(user_message: str) -> str:
    result = agent.invoke({'messages': [{'role': 'user', 'content': user_message}]})
    return result['messages'][-1].content
