import os
import json
import uuid
import requests
import numpy as np

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename

from PyPDF2 import PdfReader
from docx import Document

import faiss
from sentence_transformers import SentenceTransformer


# =========================================================
# CONFIGURATION
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOCUMENT_FOLDER = os.path.join(
    BASE_DIR,
    "data",
    "documents"
)

VECTOR_FOLDER = os.path.join(
    BASE_DIR,
    "data",
    "vector_store"
)

INDEX_FILE = os.path.join(
    VECTOR_FOLDER,
    "knowledge.index"
)

METADATA_FILE = os.path.join(
    VECTOR_FOLDER,
    "metadata.json"
)

OLLAMA_URL = "http://localhost:11434/api/generate"

OLLAMA_MODEL = "llama3.2"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

CHUNK_SIZE = 800

CHUNK_OVERLAP = 150

TOP_K = 5


# =========================================================
# IMPORTANT RAG SETTINGS
# =========================================================

# Minimum similarity score required before
# the question is considered relevant.

RELEVANCE_THRESHOLD = 0.35


# =========================================================
# FLASK
# =========================================================

app = Flask(__name__)

CORS(app)

app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


# =========================================================
# CREATE DIRECTORIES
# =========================================================

os.makedirs(
    DOCUMENT_FOLDER,
    exist_ok=True
)

os.makedirs(
    VECTOR_FOLDER,
    exist_ok=True
)


# =========================================================
# EMBEDDING MODEL
# =========================================================

print("\n========================================")
print("        NEXUS AI STARTING")
print("========================================")

print("Loading embedding model...")

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL
)

EMBEDDING_DIMENSION = (
    embedding_model
    .get_sentence_embedding_dimension()
)

print(
    "Embedding dimension:",
    EMBEDDING_DIMENSION
)


# =========================================================
# VECTOR DATABASE
# =========================================================

def load_vector_database():

    if (
        os.path.exists(INDEX_FILE)
        and
        os.path.exists(METADATA_FILE)
    ):

        try:

            index = faiss.read_index(
                INDEX_FILE
            )

            with open(
                METADATA_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                metadata = json.load(file)

            return index, metadata

        except Exception as error:

            print(
                "Vector database error:",
                error
            )

    index = faiss.IndexFlatIP(
        EMBEDDING_DIMENSION
    )

    return index, []


vector_index, metadata = (
    load_vector_database()
)


# =========================================================
# SAVE VECTOR DATABASE
# =========================================================

def save_vector_database():

    faiss.write_index(
        vector_index,
        INDEX_FILE
    )

    with open(
        METADATA_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metadata,
            file,
            indent=2,
            ensure_ascii=False
        )


# =========================================================
# TEXT EXTRACTION
# =========================================================

def extract_text_from_pdf(file_path):

    text = ""

    reader = PdfReader(
        file_path
    )

    for page_number, page in enumerate(
        reader.pages
    ):

        try:

            page_text = page.extract_text()

            if page_text:

                text += (
                    f"\n[Page "
                    f"{page_number + 1}]\n"
                )

                text += page_text

        except Exception as error:

            print(
                "PDF page error:",
                error
            )

    return text


def extract_text_from_docx(file_path):

    document = Document(
        file_path
    )

    paragraphs = []

    for paragraph in document.paragraphs:

        if paragraph.text.strip():

            paragraphs.append(
                paragraph.text.strip()
            )

    return "\n".join(
        paragraphs
    )


def extract_text_from_txt(file_path):

    with open(
        file_path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as file:

        return file.read()


def extract_text(file_path):

    extension = os.path.splitext(
        file_path
    )[1].lower()

    if extension == ".pdf":

        return extract_text_from_pdf(
            file_path
        )

    elif extension == ".docx":

        return extract_text_from_docx(
            file_path
        )

    elif extension == ".txt":

        return extract_text_from_txt(
            file_path
        )

    return ""


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(text):

    text = text.replace(
        "\x00",
        " "
    )

    lines = []

    for line in text.splitlines():

        line = line.strip()

        if line:

            lines.append(line)

    return "\n".join(lines)


# =========================================================
# CHUNKING
# =========================================================

def create_chunks(text):

    text = clean_text(text)

    if not text:

        return []

    chunks = []

    start = 0

    while start < len(text):

        end = start + CHUNK_SIZE

        chunk = text[
            start:end
        ]

        if chunk.strip():

            chunks.append(
                chunk.strip()
            )

        if end >= len(text):

            break

        start = (
            end -
            CHUNK_OVERLAP
        )

    return chunks


# =========================================================
# CREATE EMBEDDINGS
# =========================================================

def create_embeddings(texts):

    embeddings = (
        embedding_model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
    )

    return embeddings.astype(
        "float32"
    )


# =========================================================
# ADD DOCUMENT
# =========================================================

def add_document_to_database(
    filename,
    chunks
):

    global vector_index
    global metadata

    if not chunks:

        return 0

    embeddings = create_embeddings(
        chunks
    )

    vector_index.add(
        embeddings
    )

    for chunk_index, chunk in enumerate(
        chunks
    ):

        metadata.append(
            {
                "id": str(uuid.uuid4()),

                "filename": filename,

                "chunk": chunk_index + 1,

                "text": chunk
            }
        )

    save_vector_database()

    return len(chunks)


# =========================================================
# SEARCH KNOWLEDGE BASE
# =========================================================

def search_knowledge_base(
    query,
    top_k=TOP_K
):

    if vector_index.ntotal == 0:

        return []

    query_embedding = (
        create_embeddings(
            [query]
        )
    )

    number_of_results = min(
        top_k,
        vector_index.ntotal
    )

    scores, indices = (
        vector_index.search(
            query_embedding,
            number_of_results
        )
    )

    results = []

    for score, index_position in zip(
        scores[0],
        indices[0]
    ):

        if index_position < 0:

            continue

        if (
            index_position
            >= len(metadata)
        ):

            continue

        result = (
            metadata[index_position]
            .copy()
        )

        result["score"] = float(
            score
        )

        results.append(
            result
        )

    return results


# =========================================================
# CHECK RELEVANCE
# =========================================================

def get_relevant_results(
    results
):

    relevant_results = []

    for result in results:

        score = result.get(
            "score",
            0
        )

        print(
            f"Similarity: "
            f"{score:.4f} | "
            f"{result['filename']} | "
            f"Chunk {result['chunk']}"
        )

        if (
            score
            >= RELEVANCE_THRESHOLD
        ):

            relevant_results.append(
                result
            )

    return relevant_results


# =========================================================
# OLLAMA
# =========================================================

def ask_ollama(
    question,
    context
):

    system_prompt = """
You are NEXUS AI, a document-based
knowledge assistant.

IMPORTANT RULES:

1. Answer ONLY using the supplied
   knowledge-base context.

2. Do NOT use your general knowledge
   to answer the question.

3. Do NOT invent or guess information.

4. If the answer is not supported by
   the supplied context, say:

   "I couldn't find that information
   in your knowledge base."

5. Keep answers clear and useful.

6. Use bullet points or headings when
   appropriate.
"""

    prompt = f"""

{system_prompt}

==============================
KNOWLEDGE BASE CONTEXT
==============================

{context}

==============================
USER QUESTION
==============================

{question}

==============================
ANSWER
==============================

Answer ONLY from the knowledge-base
context above.
"""

    payload = {

        "model": OLLAMA_MODEL,

        "prompt": prompt,

        "stream": False,

        "options": {

            "temperature": 0.1
        }
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=180
        )

        if response.status_code != 200:

            return (
                None,
                (
                    "Ollama returned HTTP "
                    f"{response.status_code}"
                )
            )

        data = response.json()

        answer = data.get(
            "response",
            ""
        ).strip()

        return answer, None

    except requests.exceptions.ConnectionError:

        return (
            None,
            (
                "Ollama is not running. "
                "Please start Ollama first."
            )
        )

    except requests.exceptions.Timeout:

        return (
            None,
            (
                "Ollama took too long "
                "to respond."
            )
        )

    except Exception as error:

        return (
            None,
            str(error)
        )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# HEALTH
# =========================================================

@app.route("/api/health")
def health():

    ollama_status = False

    try:

        response = requests.get(
            "http://localhost:11434/api/tags",
            timeout=3
        )

        if response.status_code == 200:

            ollama_status = True

    except Exception:

        pass

    document_names = set(
        item["filename"]
        for item in metadata
    )

    return jsonify(
        {
            "status": "online",

            "ollama": ollama_status,

            "documents": len(
                document_names
            ),

            "chunks": len(metadata),

            "model": OLLAMA_MODEL,

            "threshold":
                RELEVANCE_THRESHOLD
        }
    )


# =========================================================
# UPLOAD
# =========================================================

@app.route(
    "/api/upload",
    methods=["POST"]
)
def upload():

    if "file" not in request.files:

        return jsonify(
            {
                "success": False,
                "error":
                    "No file selected."
            }
        ), 400

    file = request.files["file"]

    if file.filename == "":

        return jsonify(
            {
                "success": False,
                "error":
                    "No file selected."
            }
        ), 400

    filename = secure_filename(
        file.filename
    )

    extension = os.path.splitext(
        filename
    )[1].lower()

    allowed_extensions = {
        ".pdf",
        ".docx",
        ".txt"
    }

    if extension not in allowed_extensions:

        return jsonify(
            {
                "success": False,
                "error":
                    (
                        "Only PDF, DOCX "
                        "and TXT files "
                        "are supported."
                    )
            }
        ), 400

    file_path = os.path.join(
        DOCUMENT_FOLDER,
        filename
    )

    try:

        file.save(
            file_path
        )

        text = extract_text(
            file_path
        )

        if not text.strip():

            return jsonify(
                {
                    "success": False,
                    "error":
                        (
                            "No readable "
                            "text found."
                        )
                }
            ), 400

        chunks = create_chunks(
            text
        )

        chunks_added = (
            add_document_to_database(
                filename,
                chunks
            )
        )

        return jsonify(
            {
                "success": True,

                "filename": filename,

                "characters":
                    len(text),

                "chunks":
                    chunks_added
            }
        )

    except Exception as error:

        return jsonify(
            {
                "success": False,
                "error": str(error)
            }
        ), 500


# =========================================================
# CHAT
# =========================================================

@app.route(
    "/api/chat",
    methods=["POST"]
)
def chat():

    data = request.get_json(
        silent=True
    )

    if not data:

        return jsonify(
            {
                "success": False,
                "error":
                    "Invalid request."
            }
        ), 400

    question = data.get(
        "message",
        ""
    ).strip()

    if not question:

        return jsonify(
            {
                "success": False,
                "error":
                    "Please enter a question."
            }
        ), 400


    # -----------------------------------------------------
    # STEP 1
    # Search all document chunks
    # -----------------------------------------------------

    search_results = (
        search_knowledge_base(
            question
        )
    )


    # -----------------------------------------------------
    # STEP 2
    # No documents
    # -----------------------------------------------------

    if not search_results:

        return jsonify(
            {
                "success": True,

                "answer":
                    (
                        "📚 Your knowledge "
                        "base is empty.\n\n"
                        "Please upload a "
                        "document before "
                        "asking questions."
                    ),

                "sources": [],

                "refused": True
            }
        )


    # -----------------------------------------------------
    # STEP 3
    # Apply relevance threshold
    # -----------------------------------------------------

    relevant_results = (
        get_relevant_results(
            search_results
        )
    )


    # -----------------------------------------------------
    # STEP 4
    # STRICT REFUSAL
    # -----------------------------------------------------

    if not relevant_results:

        print(
            "\n❌ QUESTION REFUSED"
        )

        print(
            "Question:",
            question
        )

        print(
            "Reason: "
            "No sufficiently relevant "
            "document chunk found."
        )

        return jsonify(
            {
                "success": True,

                "answer":
                    (
                        "I couldn't find "
                        "that information "
                        "in your knowledge "
                        "base.\n\n"
                        "Please upload a "
                        "document containing "
                        "information related "
                        "to this question."
                    ),

                "sources": [],

                "refused": True
            }
        )


    # -----------------------------------------------------
    # STEP 5
    # Build context
    # -----------------------------------------------------

    context_parts = []

    sources = []

    for result in relevant_results:

        context_parts.append(
            f"""
SOURCE: {result['filename']}

CHUNK: {result['chunk']}

CONTENT:

{result['text']}
"""
        )

        sources.append(
            {
                "filename":
                    result["filename"],

                "chunk":
                    result["chunk"],

                "score":
                    round(
                        result["score"],
                        4
                    )
            }
        )


    context = "\n".join(
        context_parts
    )


    # -----------------------------------------------------
    # STEP 6
    # Ask Ollama
    # -----------------------------------------------------

    answer, error = ask_ollama(
        question,
        context
    )


    if error:

        return jsonify(
            {
                "success": False,

                "error": error
            }
        ), 500


    # -----------------------------------------------------
    # STEP 7
    # Extra safety
    # -----------------------------------------------------

    if not answer:

        answer = (
            "I couldn't find "
            "that information "
            "in your knowledge "
            "base."
        )


    return jsonify(
        {
            "success": True,

            "answer": answer,

            "sources": sources,

            "refused": False
        }
    )


# =========================================================
# DOCUMENTS
# =========================================================

@app.route(
    "/api/documents"
)
def documents():

    document_names = sorted(
        list(
            set(
                item["filename"]
                for item in metadata
            )
        )
    )

    documents_data = []

    for filename in document_names:

        chunks = [
            item
            for item in metadata
            if item["filename"]
            == filename
        ]

        documents_data.append(
            {
                "filename":
                    filename,

                "chunks":
                    len(chunks)
            }
        )

    return jsonify(
        {
            "documents":
                documents_data,

            "total_documents":
                len(documents_data),

            "total_chunks":
                len(metadata)
        }
    )


# =========================================================
# CLEAR KNOWLEDGE BASE
# =========================================================

@app.route(
    "/api/clear",
    methods=["DELETE"]
)
def clear_database():

    global vector_index
    global metadata

    vector_index = (
        faiss.IndexFlatIP(
            EMBEDDING_DIMENSION
        )
    )

    metadata = []

    save_vector_database()


    try:

        for filename in os.listdir(
            DOCUMENT_FOLDER
        ):

            file_path = os.path.join(
                DOCUMENT_FOLDER,
                filename
            )

            if os.path.isfile(
                file_path
            ):

                os.remove(
                    file_path
                )

    except Exception as error:

        print(
            "Cleanup error:",
            error
        )


    return jsonify(
        {
            "success": True,

            "message":
                "Knowledge base cleared."
        }
    )


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    document_names = set(
        item["filename"]
        for item in metadata
    )

    print("\n========================================")

    print(
        "       NEXUS AI IS READY"
    )

    print("========================================")

    print(
        "URL: http://127.0.0.1:5000"
    )

    print(
        "Model:",
        OLLAMA_MODEL
    )

    print(
        "Documents:",
        len(document_names)
    )

    print(
        "Chunks:",
        len(metadata)
    )

    print(
        "Relevance threshold:",
        RELEVANCE_THRESHOLD
    )

    print("========================================\n")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )