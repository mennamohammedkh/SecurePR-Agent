"""
indexing.py
============
Person 5 - RAG / Tools / UI Owner
RAG Pipeline - Step 3 & 4: Embeddings -> Vector Database

بياخد الـnodes/chunks اللي جايه من ingestion.py وبيبني عليها VectorStoreIndex
(الـEmbeddings + الـVector Database) وبيحفظه على الـdisk عشان مانعيدش الـEmbedding
كل مرة.
"""

import os
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.settings import Settings

PERSIST_DIR_BASE = os.environ.get("RAG_PERSIST_DIR", "storage")


def build_index(nodes: list, persist_name: str = "default") -> VectorStoreIndex:
    """
    بتبني VectorStoreIndex جديد من الـnodes (بتعمل Embedding لكل node وتحطه في
    الـVector Database) وبتحفظه على الـdisk عشان الاستخدام بعدين.

    Args:
        nodes: لستة الـTextNodes اللي جايه من ingestion.chunk_documents()
        persist_name: اسم الفهرس (مفيد لو عندك أكتر من knowledge base منفصل،
                      زي "security_knowledge" و"historical_reviews")

    Returns:
        VectorStoreIndex
    """
    index = VectorStoreIndex(nodes)
    persist_dir = os.path.join(PERSIST_DIR_BASE, persist_name)
    os.makedirs(persist_dir, exist_ok=True)
    index.storage_context.persist(persist_dir=persist_dir)
    return index


def load_index(persist_name: str = "default"):
    """
    بتحمّل index محفوظ من قبل من الـdisk بدل ما تعمل embedding تاني من الأول.

    Args:
        persist_name: اسم الفهرس اللي اتحفظ بيه (نفس اللي في build_index)

    Returns:
        VectorStoreIndex أو None لو الفهرس مش موجود
    """
    persist_dir = os.path.join(PERSIST_DIR_BASE, persist_name)
    if not os.path.isdir(persist_dir):
        return None

    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    return load_index_from_storage(storage_context)


def get_or_build_index(nodes: list, persist_name: str = "default"):
    """
    بتحاول تحمّل index محفوظ الأول، ولو مش موجود بتبني واحد جديد من الـnodes.

    Args:
        nodes: لستة الـTextNodes (تستخدم بس لو محتاجين نبني index جديد)
        persist_name: اسم الفهرس

    Returns:
        VectorStoreIndex
    """
    index = load_index(persist_name)
    if index is not None:
        return index
    return build_index(nodes, persist_name)


def add_nodes_to_index(index: VectorStoreIndex, nodes: list, persist_name: str = "default") -> VectorStoreIndex:
    """
    بتضيف nodes جديدة لـindex موجود بالفعل (مفيد لما نضيف Historical Review
    جديد بعد ما يخلص review من غير ما نعمل rebuild لكل حاجة) وبتحفظ التحديث.

    Args:
        index: الـVectorStoreIndex الحالي
        nodes: الـnodes الجديدة المطلوب إضافتها
        persist_name: اسم الفهرس عشان نحفظ التحديث في نفس المكان

    Returns:
        VectorStoreIndex بعد التحديث
    """
    for node in nodes:
        index.insert_nodes([node])
    persist_dir = os.path.join(PERSIST_DIR_BASE, persist_name)
    os.makedirs(persist_dir, exist_ok=True)
    index.storage_context.persist(persist_dir=persist_dir)
    return index
