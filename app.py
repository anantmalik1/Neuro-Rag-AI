import streamlit as st
import os
import io
import re
 
# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="NeuroRAG AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)
 
# ─────────────────────────────────────────────
# Custom CSS — dark purple UI
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
 
* { font-family: 'Inter', sans-serif; }
 
.stApp {
    background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2e 50%, #0d0d2b 100%);
    min-height: 100vh;
}
 
/* Hide default streamlit elements */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 2rem; }
 
/* Upload area */
.uploadedFile { background: rgba(139,92,246,0.1) !important; border: 1px solid rgba(139,92,246,0.3) !important; border-radius: 12px !important; }
 
/* Chat messages */
.stChatMessage { background: rgba(255,255,255,0.03) !important; border: 1px solid rgba(139,92,246,0.15) !important; border-radius: 16px !important; margin-bottom: 12px !important; }
 
/* Input box */
.stChatInputContainer { background: rgba(255,255,255,0.05) !important; border: 1px solid rgba(139,92,246,0.4) !important; border-radius: 16px !important; }
.stChatInputContainer textarea { color: white !important; }
 
/* Buttons */
.stButton button {
    background: linear-gradient(135deg, #7c3aed, #a855f7) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
}
.stButton button:hover {
    background: linear-gradient(135deg, #6d28d9, #9333ea) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 20px rgba(139,92,246,0.4) !important;
}
 
/* Metric cards */
[data-testid="metric-container"] {
    background: rgba(139,92,246,0.1) !important;
    border: 1px solid rgba(139,92,246,0.3) !important;
    border-radius: 12px !important;
    padding: 12px !important;
}
[data-testid="metric-container"] label { color: #a78bfa !important; }
[data-testid="stMetricValue"] { color: white !important; }
 
/* Text colors */
.stMarkdown, p, span, label { color: #e2e8f0 !important; }
h1, h2, h3 { color: white !important; }
 
/* File uploader */
[data-testid="stFileUploader"] {
    background: rgba(139,92,246,0.05) !important;
    border: 2px dashed rgba(139,92,246,0.4) !important;
    border-radius: 16px !important;
    padding: 20px !important;
}
 
/* Success / error */
.stSuccess { background: rgba(16,185,129,0.1) !important; border: 1px solid rgba(16,185,129,0.3) !important; border-radius: 10px !important; }
.stError   { background: rgba(239,68,68,0.1)  !important; border: 1px solid rgba(239,68,68,0.3)  !important; border-radius: 10px !important; }
.stInfo    { background: rgba(59,130,246,0.1)  !important; border: 1px solid rgba(59,130,246,0.3)  !important; border-radius: 10px !important; }
.stWarning { background: rgba(245,158,11,0.1)  !important; border: 1px solid rgba(245,158,11,0.3)  !important; border-radius: 10px !important; }
 
/* Spinner */
.stSpinner > div { border-top-color: #a855f7 !important; }
 
/* Selectbox */
.stSelectbox div { background: rgba(139,92,246,0.1) !important; color: white !important; border: 1px solid rgba(139,92,246,0.3) !important; border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────
# Helper — extract text from uploaded file
# ─────────────────────────────────────────────
def extract_text(uploaded_file) -> str:
    name = uploaded_file.name.lower()
    raw  = uploaded_file.read()
 
    # ── TXT ──
    if name.endswith(".txt"):
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                return raw.decode(enc)
            except Exception:
                continue
        return raw.decode("utf-8", errors="ignore")
 
    # ── PDF ──
    if name.endswith(".pdf"):
        # Try pypdf first (new API), then PyPDF2 (legacy)
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except ImportError:
            pass
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(raw))
            return "\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except ImportError:
            pass
        # Brute-force fallback: pull ASCII strings from raw bytes
        text = raw.decode("latin-1", errors="ignore")
        strings = re.findall(r'[\x20-\x7E]{4,}', text)
        return " ".join(strings)
 
    # ── DOCX ──
    if name.endswith(".docx"):
        try:
            import docx2txt
            return docx2txt.process(io.BytesIO(raw))
        except ImportError:
            pass
        try:
            from docx import Document
            doc = Document(io.BytesIO(raw))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            pass
        return "DOCX library not installed. Please add python-docx to requirements.txt."
 
    return "Unsupported file format. Please upload PDF, TXT, or DOCX."
 
 
# ─────────────────────────────────────────────
# Helper — chunk text
# ─────────────────────────────────────────────
def chunk_text(text: str, size: int = 500, overlap: int = 50) -> list[str]:
    words  = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunk = " ".join(words[i:i + size])
        if chunk.strip():
            chunks.append(chunk)
        i += size - overlap
    return chunks
 
 
# ─────────────────────────────────────────────
# Helper — find relevant chunks
# ─────────────────────────────────────────────
def find_relevant_chunks(query: str, chunks: list[str], top_k: int = 4) -> list[str]:
    q_words = set(query.lower().split())
    scored  = []
    for chunk in chunks:
        c_words = set(chunk.lower().split())
        score   = len(q_words & c_words) / max(len(q_words), 1)
        scored.append((score, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:top_k]]
 
 
# ─────────────────────────────────────────────
# Mistral API call — pure requests, no library
# ─────────────────────────────────────────────
def query_mistral(user_question: str, context: str, api_key: str) -> str:
    import requests
    import json
 
    url = "https://api.mistral.ai/v1/chat/completions"
 
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
 
    payload = {
        "model": "mistral-small-latest",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are NeuroRAG AI, an intelligent document analysis assistant. "
                    "Answer questions based ONLY on the provided document context. "
                    "If the answer is not in the context, say: "
                    "'I could not find the answer in the document.' "
                    "Be concise, accurate, and helpful."
                ),
            },
            {
                "role": "user",
                "content": f"Document Context:\n{context}\n\nQuestion: {user_question}",
            },
        ],
        "max_tokens": 1024,
        "temperature": 0.3,
    }
 
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
 
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        elif resp.status_code == 401:
            return (
                "❌ Invalid API key. Please check your MISTRAL_API_KEY in "
                "HuggingFace Space → Settings → Variables and Secrets."
            )
        elif resp.status_code == 429:
            return "⚠️ Rate limit reached. Please wait a moment and try again."
        else:
            return f"❌ API Error {resp.status_code}: {resp.text[:200]}"
 
    except requests.exceptions.Timeout:
        return "⚠️ Request timed out. Please try again."
    except Exception as e:
        return f"❌ Error: {str(e)}"
 
 
# ─────────────────────────────────────────────
# Session state initialisation
# ─────────────────────────────────────────────
for key, default in {
    "messages":        [],
    "document_text":   None,
    "document_chunks": [],
    "document_name":   None,
    "doc_stats":       {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default
 
# ─────────────────────────────────────────────
# Mistral API key (from HuggingFace Secret)
# ─────────────────────────────────────────────
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
 
 
# ═════════════════════════════════════════════
# UI
# ═════════════════════════════════════════════
 
# ── Header ──
col_logo, col_title, col_badge = st.columns([1, 8, 2])
with col_logo:
    st.markdown("## 🧠")
with col_title:
    st.markdown("# NeuroRAG AI")
    st.markdown(
        "<p style='color:#a78bfa;margin-top:-10px;font-size:14px;'>"
        "Intelligent Document Analysis · Powered by Mistral AI"
        "</p>",
        unsafe_allow_html=True,
    )
with col_badge:
    status = "🟢 Ready" if st.session_state.document_text else "⚪ No Document"
    st.markdown(
        f"<div style='background:rgba(139,92,246,0.15);border:1px solid rgba(139,92,246,0.4);"
        f"border-radius:20px;padding:6px 14px;text-align:center;color:#a78bfa;"
        f"font-size:12px;font-weight:600;margin-top:16px;'>{status}</div>",
        unsafe_allow_html=True,
    )
 
st.markdown("---")
 
# ── API key warning ──
if not MISTRAL_API_KEY:
    st.warning(
        "⚠️ **MISTRAL_API_KEY not found.**  "
        "Go to your HuggingFace Space → **Settings → Variables and Secrets** → "
        "add `MISTRAL_API_KEY` with your Mistral key from "
        "[console.mistral.ai](https://console.mistral.ai)."
    )
 
# ── Two-column layout ──
left_col, right_col = st.columns([1, 2], gap="large")
 
# ══════════════════════
# LEFT — Document panel
# ══════════════════════
with left_col:
    st.markdown("### 📄 Upload Document")
 
    uploaded = st.file_uploader(
        "Choose a PDF, TXT, or DOCX file",
        type=["pdf", "txt", "docx"],
        help="Maximum file size: 200 MB",
    )
 
    if uploaded:
        if (
            st.session_state.document_name != uploaded.name
            or st.session_state.document_text is None
        ):
            with st.spinner("🔄 Processing document…"):
                try:
                    text = extract_text(uploaded)
 
                    if text and len(text.strip()) > 50:
                        chunks = chunk_text(text)
                        word_count = len(text.split())
                        # Estimate pages
                        if uploaded.name.lower().endswith(".pdf"):
                            try:
                                uploaded.seek(0)
                                raw = uploaded.read()
                                try:
                                    from pypdf import PdfReader
                                    pages = len(PdfReader(io.BytesIO(raw)).pages)
                                except Exception:
                                    import PyPDF2
                                    pages = len(PyPDF2.PdfReader(io.BytesIO(raw)).pages)
                            except Exception:
                                pages = max(1, word_count // 250)
                        else:
                            pages = max(1, word_count // 250)
 
                        st.session_state.document_text   = text
                        st.session_state.document_chunks = chunks
                        st.session_state.document_name   = uploaded.name
                        st.session_state.doc_stats = {
                            "pages":  pages,
                            "words":  word_count,
                            "chunks": len(chunks),
                        }
                        st.session_state.messages = []  # reset chat
                        st.success(f"✅ **{uploaded.name}** loaded successfully!")
                    else:
                        st.error(
                            "❌ Could not extract text from this file. "
                            "Make sure the PDF is not scanned/image-only."
                        )
                except Exception as e:
                    st.error(f"❌ Error processing file: {str(e)}")
 
    # Stats
    if st.session_state.document_text and st.session_state.doc_stats:
        s = st.session_state.doc_stats
        st.markdown("#### 📊 Document Stats")
        m1, m2, m3 = st.columns(3)
        m1.metric("Pages",  s.get("pages",  0))
        m2.metric("Words",  f"{s.get('words', 0):,}")
        m3.metric("Chunks", s.get("chunks", 0))
 
        st.markdown(
            f"<div style='background:rgba(139,92,246,0.1);border:1px solid rgba(139,92,246,0.3);"
            f"border-radius:10px;padding:10px;margin-top:8px;'>"
            f"<p style='color:#a78bfa;font-size:12px;font-weight:600;margin:0;'>📁 {st.session_state.document_name}</p>"
            f"</div>",
            unsafe_allow_html=True,
        )
 
        if st.button("🔄 Upload New Document"):
            for k in ("document_text", "document_chunks", "document_name", "doc_stats", "messages"):
                st.session_state[k] = [] if k in ("messages", "document_chunks") else None if k != "doc_stats" else {}
            st.rerun()
 
    # Suggested questions
    if st.session_state.document_text:
        st.markdown("#### 💡 Suggested Questions")
        suggestions = [
            "Summarize this document",
            "What are the main topics?",
            "What are the key findings?",
            "List the important points",
        ]
        for q in suggestions:
            if st.button(q, key=f"sugg_{q}"):
                st.session_state.messages.append({"role": "user", "content": q})
                relevant = find_relevant_chunks(q, st.session_state.document_chunks)
                context  = "\n\n---\n\n".join(relevant)
                answer   = query_mistral(q, context, MISTRAL_API_KEY)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.rerun()
 
 
# ══════════════════════
# RIGHT — Chat panel
# ══════════════════════
with right_col:
    st.markdown("### 💬 Chat with Your Document")
 
    if not st.session_state.document_text:
        st.markdown(
            "<div style='background:rgba(139,92,246,0.08);border:2px dashed rgba(139,92,246,0.3);"
            "border-radius:16px;padding:60px 30px;text-align:center;'>"
            "<div style='font-size:48px;margin-bottom:16px;'>📄</div>"
            "<h3 style='color:#a78bfa;'>Upload a document to get started</h3>"
            "<p style='color:#7c6fa0;'>Supports PDF, TXT, and DOCX files</p>"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        # Chat history
        chat_container = st.container()
        with chat_container:
            if not st.session_state.messages:
                st.info(
                    f"✅ **{st.session_state.document_name}** is ready! "
                    "Ask me anything about this document."
                )
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
 
        # Chat input
        if prompt := st.chat_input("Ask a question about your document…"):
            if not MISTRAL_API_KEY:
                st.error(
                    "❌ API key not found. Add MISTRAL_API_KEY in "
                    "HuggingFace Space Settings → Variables and Secrets."
                )
            else:
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
 
                with st.chat_message("assistant"):
                    with st.spinner("🧠 Thinking…"):
                        relevant = find_relevant_chunks(prompt, st.session_state.document_chunks)
                        context  = "\n\n---\n\n".join(relevant)
                        answer   = query_mistral(prompt, context, MISTRAL_API_KEY)
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
 


