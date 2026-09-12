"""
retriever.py
=============
Person 5 - RAG / Tools / UI Owner
RAG Pipeline - Step 5: Retriever

بياخد الـVectorStoreIndex (من indexing.py) وبيبني منه Retriever بيقدر
يجيب أقرب الـchunks (Relevant Context) لأي سؤال أو query جاي من الـAgent.
"""

from llama_index.core import VectorStoreIndex


def get_retriever(index: VectorStoreIndex, top_k: int = 5):
    """
    بتبني retriever من الـindex بيرجع أقرب top_k chunks لأي query.

    Args:
        index: الـVectorStoreIndex الجاهز (من indexing.get_or_build_index مثلًا)
        top_k: عدد الـchunks المطلوب رجوعها لكل query

    Returns:
        BaseRetriever
    """
    return index.as_retriever(similarity_top_k=top_k)


def retrieve(index: VectorStoreIndex, query: str, top_k: int = 5) -> list:
    """
    بتنفذ retrieval مباشر: بتاخد query نصي وترجع الـchunks الأقرب ليه بصيغة
    مبسطة (text + score + metadata) عشان تتبعت للـAgent أو تتعرض في الـUI.

    Args:
        index: الـVectorStoreIndex الجاهز
        query: نص السؤال أو الكود المطلوب البحث عنه
        top_k: عدد النتائج المطلوبة

    Returns:
        list[dict]
    """
    retriever = get_retriever(index, top_k=top_k)
    nodes = retriever.retrieve(query)

    results = []
    for node_with_score in nodes:
        results.append({
            "text": node_with_score.node.get_content(),
            "score": node_with_score.score,
            "metadata": node_with_score.node.metadata,
        })
    return results
