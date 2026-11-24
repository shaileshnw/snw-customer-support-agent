"""Streamlit chat UI. Calls the FastAPI /chat endpoint."""
import streamlit as st
import requests
import os

API_URL = os.getenv('API_URL', 'http://localhost:8000/chat')

st.set_page_config(page_title='Support Agent', page_icon='🎧')
st.title('🎧 Customer Support')
st.caption('Powered by AI. Escalates to humans when needed.')

if 'messages' not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg['role']):
        st.markdown(msg['content'])

if prompt := st.chat_input('Describe your issue...'):
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    with st.chat_message('user'):
        st.markdown(prompt)
    with st.chat_message('assistant'):
        with st.spinner('Thinking...'):
            try:
                response = requests.post(API_URL, json={'message': prompt, 'customer_id': 'demo_customer'}, timeout=60)
                answer = response.json()['reply'] if response.status_code == 200 else 'API error: ' + str(response.status_code)
            except Exception as e:
                answer = 'Could not reach server: ' + str(e)
            st.markdown(answer)
    st.session_state.messages.append({'role': 'assistant', 'content': answer})
