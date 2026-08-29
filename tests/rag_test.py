from backend.tools.documents import chunk_text


def test_chunk_text_overlap():
    text = "word " * 500
    chunks = chunk_text(text, size=80, overlap=20)
    assert len(chunks) > 1
    assert all(chunks)
