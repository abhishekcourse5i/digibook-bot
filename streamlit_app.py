import streamlit as st
import asyncio
from src.agents.LangBotAgent import LangBotAgent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

if 'agent' not in st.session_state:
    st.session_state['agent'] = LangBotAgent()
if 'user_input' not in st.session_state:
    st.session_state['user_input'] = ""
if 'run_stream' not in st.session_state:
    st.session_state['run_stream'] = False
if 'pending_user_input' in st.session_state:
    st.session_state['user_input'] = st.session_state.pop('pending_user_input')

# Centered label above the input bar
st.markdown('<div style="text-align: center; font-size: 1.2em; font-weight: bold;">Ask anything</div>', unsafe_allow_html=True)

# Add a gap between the label and the input field
st.markdown("<br>", unsafe_allow_html=True)

user_input = st.text_input(
    "Ask anything",  # Non-empty label for accessibility
    value=st.session_state['user_input'],
    key="user_input",
    on_change=lambda: st.session_state.update({'run_stream': True}),
    placeholder="Ask anything",
    label_visibility="collapsed"
)

notification_area = st.empty()  # Placeholder for notifications below input

agent = st.session_state['agent']

def extract_message_content(chunk):
    if isinstance(chunk, dict):
        if 'supervisor' in chunk and 'structured_response' in chunk['supervisor']:
            sr = chunk['supervisor']['structured_response']
            if hasattr(sr, 'dict'):
                sr = sr.dict()
            return sr  # Return the dict for final output
        for agent_key in chunk:
            agent_data = chunk[agent_key]
            if isinstance(agent_data, dict) and 'messages' in agent_data:
                messages = agent_data['messages']
                for m in reversed(messages):
                    if isinstance(m, AIMessage) or isinstance(m, HumanMessage) or isinstance(m, ToolMessage):
                        content = getattr(m, 'content', None)
                        if content:
                            return f"**{agent_key}:** {content}"
    return str(chunk)

def sync_stream_response(message):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async_gen = agent.astream_database(message)
    final_output = None
    try:
        while True:
            try:
                chunk = loop.run_until_complete(async_gen.__anext__())
                pretty = extract_message_content(chunk)
                # If pretty is a dict, it's the final structured output
                if isinstance(pretty, dict):
                    final_output = pretty
                    break
                else:
                    notification_area.info(pretty)
            except StopAsyncIteration:
                break
    finally:
        loop.close()
    if final_output:
        notification_area.empty()  # Clear notification area
        st.write(final_output)
        yield ""  # Ensure this is always a generator

if st.session_state.get('run_stream') and st.session_state['user_input']:
    st.write_stream(sync_stream_response(st.session_state['user_input']))
    st.session_state['run_stream'] = False 