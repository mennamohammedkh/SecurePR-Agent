"""
query_engine.py
=================
Person 5 - RAG / Tools / UI Owner
RAG Pipeline - Step 6: Relevant Context

بيبني Query Engine كامل فوق الـindex (Retriever + Response Synthesizer) عشان
يرجع Context جاهز ومصاغ (مش chunks خام بس) للـAgents اللي محتاجة تفهم إجابة
جاهزة على سؤال معين، زي:
    "A similar change previously received comments about missing
     authentication validation."
"""

from llama_index.core import VectorStoreIndex


def get_query_engine(index: VectorStoreIndex, top_k: int = 5):
    """
    بتبني query engine كامل من الـindex (retriever + response synthesis).

    Args:
        index: الـVectorStoreIndex الجاهز
        top_k: عدد الـchunks اللي هيتبني عليهم الرد

    Returns:
        BaseQueryEngine
    """
    return index.as_query_engine(similarity_top_k=top_k)


def query(index: VectorStoreIndex, question: str, top_k: int = 5) -> dict:
    """
    بتسأل الـindex سؤال مباشر وترجع الـRelevant Context جاهز مع مصادره.

    Args:
        index: الـVectorStoreIndex الجاهز
        question: السؤال أو الـcontext المطلوب (مثلًا "هل الـPR ده شبيه بحاجة
                  اتعملها قبل كده؟")
        top_k: عدد الـchunks المستخدمة في تكوين الإجابة

    Returns:
        dict فيه:
            - "answer": النص النهائي (Relevant Context)
            - "sources": لستة بالـchunks اللي اتبنى عليها الرد
    """
    engine = get_query_engine(index, top_k=top_k)
    response = engine.query(question)

    sources = []
    for node_with_score in getattr(response, "source_nodes", []):
        sources.append({
            "text": node_with_score.node.get_content(),
            "score": node_with_score.score,
            "metadata": node_with_score.node.metadata,
        })

    return {
        "answer": str(response),
        "sources": sources,
    }
