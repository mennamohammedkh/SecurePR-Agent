"""
rag_search.py
==============
Person 5 - RAG / Tools / UI Owner
RAG Search Tools - دي الـTools اللي بتتوفر لباقي الفريق (نقطة الربط) عشان
الـAgents تقدر تعمل Semantic Search على الـKnowledge Base من غير ما تعرف
تفاصيل الـLlamaIndex Pipeline اللي وراها (ingestion / indexing / retriever /
query_engine).

- search_security_knowledge()  : بتدور في OWASP / CWE / secure_coding
- search_historical_reviews()  : بتدور في historical_reviews (إضافة قوية -
  Historical Review Retrieval) وترجع تعليقات قديمة على PRs شبيهة.
"""

from src.rag.ingestion import load_documents, chunk_documents, add_document_text
from src.rag.indexing import get_or_build_index, add_nodes_to_index
from src.rag.retriever import retrieve
from src.rag.query_engine import query

# --- Person 2 (Integration) ---
# LlamaIndex افتراضيًا بيحاول يستخدم OpenAI embeddings، وده بيفشل من غير
# API key. بنستخدم embedding محلي (src/rag/local_embedding.py) بدل كده
# عشان الـRAG تشتغل فعليًا من غير ما نعتمد على خدمة خارجية وقت الـDemo.
from src.rag.local_embedding import configure_local_embeddings
configure_local_embeddings()

SECURITY_KNOWLEDGE_INDEX_NAME = "security_knowledge"
HISTORICAL_REVIEWS_INDEX_NAME = "historical_reviews"

SECURITY_KNOWLEDGE_SOURCES = ["knowledge/OWASP", "knowledge/CWE", "knowledge/secure_coding"]
HISTORICAL_REVIEWS_SOURCE = "knowledge/historical_reviews"


def _build_security_knowledge_index():
    """بتبني (أو تحمّل) الـindex بتاع الـsecurity knowledge base."""
    all_documents = []
    for source_dir in SECURITY_KNOWLEDGE_SOURCES:
        all_documents.extend(load_documents(source_dir))
    nodes = chunk_documents(all_documents)
    return get_or_build_index(nodes, persist_name=SECURITY_KNOWLEDGE_INDEX_NAME)


def _build_historical_reviews_index():
    """بتبني (أو تحمّل) الـindex بتاع الـhistorical reviews."""
    documents = load_documents(HISTORICAL_REVIEWS_SOURCE)
    nodes = chunk_documents(documents)
    return get_or_build_index(nodes, persist_name=HISTORICAL_REVIEWS_INDEX_NAME)


def search_security_knowledge(query_text: str, top_k: int = 5, as_answer: bool = False):
    """
    بتعمل Semantic Search في الـKnowledge Base الأمنية (OWASP / CWE /
    secure_coding) وترجع الـchunks الأقرب للـquery.

    Args:
        query_text: نص الكود أو السؤال المطلوب البحث عنه، مثلًا
                    "SQL query built with string concatenation"
        top_k: عدد النتائج المطلوبة
        as_answer: لو True بترجع إجابة مصاغة (query_engine) بدل الـchunks الخام

    Returns:
        list[dict] بالـchunks الأقرب، أو dict فيه answer+sources لو as_answer=True
    """
    index = _build_security_knowledge_index()
    if as_answer:
        return query(index, query_text, top_k=top_k)
    return retrieve(index, query_text, top_k=top_k)


def search_historical_reviews(query_text: str, top_k: int = 3, as_answer: bool = False):
    """
    Historical Review Retrieval: بتدور على PRs شبيهة اتعملها قبل كده وترجع
    الـreviews القديمة كـContext للـCode Review Agent، مثال:
    "A similar change previously received comments about missing
     authentication validation."

    Args:
        query_text: وصف أو diff الـPR الحالي اللي عايزين ندور على شبيه له
        top_k: عدد الـreviews القديمة المطلوب رجوعها
        as_answer: لو True بترجع إجابة مصاغة (query_engine) بدل الـchunks الخام

    Returns:
        list[dict] بالـreviews القديمة الأقرب، أو dict فيه answer+sources
    """
    index = _build_historical_reviews_index()
    if as_answer:
        return query(index, query_text, top_k=top_k)
    return retrieve(index, query_text, top_k=top_k)


def add_historical_review(review_text: str, pr_number: int = None, repo_name: str = None) -> None:
    """
    بتضيف review جديد خلص لتوه لقاعدة الـhistorical_reviews عشان يستخدم في
    البحث الدلالي (Semantic Search) بعدين لو ظهر PR شبيه.

    Args:
        review_text: نص الـreview أو التعليقات اللي اتكتبت على الـPR
        pr_number: رقم الـPR (اختياري، يتحفظ كـmetadata)
        repo_name: اسم الـrepository (اختياري، يتحفظ كـmetadata)
    """
    metadata = {"source": "historical_reviews"}
    if pr_number is not None:
        metadata["pr_number"] = pr_number
    if repo_name is not None:
        metadata["repo_name"] = repo_name

    document = add_document_text(review_text, metadata=metadata)
    nodes = chunk_documents([document])

    index = _build_historical_reviews_index()
    add_nodes_to_index(index, nodes, persist_name=HISTORICAL_REVIEWS_INDEX_NAME)
