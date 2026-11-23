"""ChatGPT-style Streamlit interface for the Medical RAG API."""
import os

import requests
import streamlit as st

st.set_page_config(page_title="Medical RAG Assistant", page_icon="🩺", layout="wide")
st.title("🩺 Medical RAG Assistant")
st.caption("Answers come only from your uploaded documents. Not a replacement for professional medical advice.")

if "messages" not in st.session_state:
    st.session_state.messages = []


def error_text(response: requests.Response) -> str:
    try:
        return response.json().get("detail", response.text)
    except ValueError:
        return response.text


with st.sidebar:
    st.header("Configuration")
    api_url = st.text_input("API URL", os.getenv("API_URL", "http://localhost:8000")).rstrip("/")
    top_k = st.slider("Chunks to retrieve (top_k)", 1, 10, 4)
    filename_filter = st.text_input("Limit to one filename (optional)")

    st.divider()
    uploaded = st.file_uploader("Upload documents", type=["pdf", "txt", "docx"], accept_multiple_files=True)
    if st.button("Index documents", disabled=not uploaded):
        for f in uploaded:
            with st.spinner(f"Indexing {f.name}..."):
                try:
                    r = requests.post(f"{api_url}/upload", files={"file": (f.name, f.getvalue())}, timeout=600)
                    if r.ok:
                        d = r.json()
                        st.success(f"{d['filename']}: {d['pages']} pages, {d['chunks']} chunks")
                    else:
                        st.error(f"{f.name}: {error_text(r)}")
                except requests.RequestException as exc:
                    st.error(f"Could not reach the API: {exc}")

    if st.button("Show index stats"):
        try:
            r = requests.get(f"{api_url}/stats", timeout=30)
            st.json(r.json())
        except requests.RequestException as exc:
            st.error(f"Could not reach the API: {exc}")

    st.divider()
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()


def show_sources(sources: list[dict]) -> None:
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})"):
        for i, s in enumerate(sources, start=1):
            st.markdown(f"**[{i}] {s['filename']}, p.{s['page']}** (score {s['score']:.2f})")
            st.caption(s["text"])


for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        show_sources(msg.get("sources", []))

if question := st.chat_input("Ask a medical question about your documents"):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching documents and generating answer..."):
            payload = {"question": question, "top_k": top_k}
            if filename_filter.strip():
                payload["filename"] = filename_filter.strip()
            try:
                r = requests.post(f"{api_url}/ask", json=payload, timeout=120)
                if r.ok:
                    data = r.json()
                    answer, sources = data["answer"], data["sources"]
                    st.markdown(answer)
                    show_sources(sources)
                    st.caption(f"Latency: {data['latency_ms']:.0f} ms")
                else:
                    answer, sources = f"Error: {error_text(r)}", []
                    st.error(answer)
            except requests.RequestException as exc:
                answer, sources = f"Could not reach the API: {exc}", []
                st.error(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
