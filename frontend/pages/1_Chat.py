import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from frontend.components.api import post_json

st.set_page_config(page_title="Chat · AI Company", page_icon="💬", layout="wide")
st.title("Company chat")

if "history" not in st.session_state:
    st.session_state.history = []

mode = st.radio("Mode", ["company", "chat"], horizontal=True, help="company = full 10-agent workflow")
message = st.chat_input("Describe the product, research, or coding job…")

for turn in st.session_state.history:
    with st.chat_message("user"):
        st.write(turn["user"])
    with st.chat_message("assistant"):
        st.markdown(turn["assistant"])
        if turn.get("logs"):
            st.caption("Agents: " + " → ".join(turn["logs"]))

if message:
    with st.chat_message("user"):
        st.write(message)
    with st.chat_message("assistant"):
        with st.spinner("Agents are working… this can take a few minutes"):
            result = post_json("/chat", {"message": message, "user_id": 1, "mode": mode})
        if result:
            final = result.get("final") or result.get("review") or str(result)
            st.markdown(final)
            logs = result.get("logs") or []
            if logs:
                st.caption("Agents: " + " → ".join(logs))
            with st.expander("Raw agent outputs"):
                st.json({k: v for k, v in result.items() if k != "final"})
            st.session_state.history.append({"user": message, "assistant": final, "logs": logs})
