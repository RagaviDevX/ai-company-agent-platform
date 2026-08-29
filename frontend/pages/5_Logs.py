import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from frontend.components.api import get_json

st.set_page_config(page_title="Logs · AI Company", page_icon="📊", layout="wide")
st.title("Agent logs")

data = get_json("/logs") or {}
st.subheader("File logs")
st.json(data.get("file_logs") or [])
st.subheader("Database logs")
st.dataframe(data.get("db_logs") or [], use_container_width=True)
