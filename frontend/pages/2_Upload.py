import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from frontend.components.api import post_file

st.set_page_config(page_title="Upload · AI Company", page_icon="📂", layout="wide")
st.title("Upload documents, images, audio")

tab1, tab2, tab3 = st.tabs(["Documents (RAG)", "Vision", "Voice"])

with tab1:
    f = st.file_uploader("PDF, DOCX, TXT, CSV, Excel", type=["pdf", "docx", "txt", "md", "csv", "xlsx"])
    if f and st.button("Ingest into knowledge base"):
        result = post_file("/upload", f.name, f.getvalue())
        if result:
            st.success(result)

with tab2:
    img = st.file_uploader("Image", type=["png", "jpg", "jpeg", "webp"], key="img")
    prompt = st.text_input("Vision prompt", "OCR and describe this image.")
    if img and st.button("Analyze image"):
        result = post_file("/vision", img.name, img.getvalue(), extra={"prompt": prompt})
        if result:
            st.write(result.get("analysis"))

with tab3:
    audio = st.file_uploader("Audio", type=["mp3", "wav", "m4a", "webm"], key="aud")
    if audio and st.button("Transcribe with Whisper"):
        result = post_file("/voice", audio.name, audio.getvalue())
        if result:
            st.write(result.get("transcript"))
