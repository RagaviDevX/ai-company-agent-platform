import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from frontend.components.api import get_json, post_json

st.set_page_config(page_title="Memory · AI Company", page_icon="🧠", layout="wide")
st.title("Long-term memory")

data = get_json("/memory", user_id=1) or {}
memories = data.get("memories") or []
convos = data.get("conversations") or []

new = st.text_area("Add a memory")
if st.button("Save") and new.strip():
    post_json("/memory", {"user_id": 1, "memory": new.strip()})
    st.rerun()

st.subheader("Stored memories")
if not memories:
    st.caption("None yet.")
for m in memories:
    st.write(f"- {m.get('memory')}")

st.subheader("Recent conversations")
for c in convos[:20]:
    with st.expander(str(c.get("message", ""))[:80]):
        st.write(c.get("response"))
