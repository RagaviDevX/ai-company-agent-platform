import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="Settings · AI Company", page_icon="S", layout="wide")
st.title("Settings")

st.session_state.backend_url = st.text_input(
    "FastAPI URL",
    st.session_state.get("backend_url", "http://127.0.0.1:8000"),
)

st.markdown(
    """
### Free model routing (LiteLLM)

| Role | Default model | Provider |
|---|---|---|
| Planner | DeepSeek V3 free | OpenRouter |
| Coder | Qwen 3 32B | Groq |
| Reasoning | Llama 3.3 70B | Groq |
| Vision | Llama 4 Scout | Groq |
| STT | Whisper Large v3 | Groq |
| Embeddings | BGE Small v1.5 | Hugging Face local |

Change models in `backend/config/settings.py`.
Put keys in `.env` — never commit them.
"""
)
