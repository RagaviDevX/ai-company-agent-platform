import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from frontend.components.api import get_json, post_json

st.set_page_config(page_title="Knowledge · AI Company", page_icon="📚", layout="wide")
st.title("Knowledge base")

docs = (get_json("/documents") or {}).get("documents") or []
st.write(f"{len(docs)} indexed files")
st.dataframe(docs, use_container_width=True)

q = st.text_input("Search documents")
if q:
    data = post_json("/rag", {"query": q, "limit": 5})
    if data:
        for h in data.get("hits", []):
            st.markdown(f"**{h.get('filename')}** · score `{h.get('score'):.3f}`")
            st.write(h.get("text"))
