"""
ingestion.py
=============
Person 5 - RAG / Tools / UI Owner
RAG Pipeline - Step 1 & 2: Documents -> Chunking

بيقرا الملفات من الـKnowledge Base (knowledge/OWASP, knowledge/CWE,
knowledge/secure_coding, knowledge/repository_docs, knowledge/historical_reviews)
وبيقسمها (Chunking) عشان تبقى جاهزة للـEmbedding في indexing.py.

LlamaIndex Pipeline:
    Documents -> Chunking -> Embeddings -> Vector Database -> Retriever -> Relevant Context
"""

import os
from llama_index.core import SimpleDirectoryReader, Document
from llama_index.core.node_parser import SentenceSplitter

KNOWLEDGE_BASE_DIR = os.environ.get("KNOWLEDGE_BASE_DIR", "knowledge")

# مقاس الـchunk وعدد الـoverlap بين الـchunks المتتالية
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64


def load_documents(source_dir: str) -> list:
    """
    بتقرا كل الملفات من مجلد معين (زي knowledge/OWASP) وترجعهم كـLlamaIndex Documents.

    Args:
        source_dir: مسار المجلد اللي فيه الملفات (pdf, txt, md, ...)

    Returns:
        list[Document]
    """
    if not os.path.isdir(source_dir) or not os.listdir(source_dir):
        return []

    reader = SimpleDirectoryReader(input_dir=source_dir, recursive=True)
    return reader.load_data()


def load_all_knowledge_sources() -> dict:
    """
    بتحمّل كل مصادر الـKnowledge Base مقسمة حسب النوع (OWASP, CWE, secure_coding,
    repository_docs, historical_reviews) عشان كل مصدر يتفهرس لوحده لو احتجنا.

    Returns:
        dict {source_name: list[Document]}
    """
    sources = ["OWASP", "CWE", "secure_coding", "repository_docs", "historical_reviews"]
    documents_by_source = {}
    for source in sources:
        path = os.path.join(KNOWLEDGE_BASE_DIR, source)
        documents_by_source[source] = load_documents(path)
    return documents_by_source


def chunk_documents(documents: list, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP) -> list:
    """
    بتقسم الـDocuments لـnodes/chunks أصغر عشان تبقى مناسبة للـEmbeddings.

    Args:
        documents: لستة الـDocuments اللي جايه من load_documents()
        chunk_size: حجم الـchunk بالـtokens تقريبًا
        chunk_overlap: عدد الـtokens المشتركة بين chunk واللي بعده

    Returns:
        list[TextNode]
    """
    if not documents:
        return []

    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.get_nodes_from_documents(documents)


def add_document_text(text: str, metadata: dict = None) -> Document:
    """
    بتبني Document واحد يدويًا من نص خام (مفيد لما تحب تضيف Historical Review
    جديد بعد ما يخلص الـreview، من غير ما يبقى ملف على الـdisk).

    Args:
        text: النص المطلوب إضافته
        metadata: بيانات إضافية زي {"source": "historical_reviews", "pr_number": 152}

    Returns:
        Document
    """
    return Document(text=text, metadata=metadata or {})
