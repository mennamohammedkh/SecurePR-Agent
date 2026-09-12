"""
local_embedding.py — Person 2 (Integration)
============================================
المشكلة اللي كانت موجودة: LlamaIndex افتراضيًا محتاج embedding provider
(زي OpenAI's text-embedding-ada-002) عشان يحوّل النص لأرقام (vectors).
ده يحتاج API key + اتصال إنترنت لحظي وقت العرض — مخاطرة إضافية يوم
الـDemo (زي ما شفنا قبل كده مع GitHub API، أي حاجة بتعتمد على خدمة خارجية
لازم يكون عندها خطة بديلة).

الحل هنا: embedding محلي 100% (hashing-based bag-of-words)، مفيهوش:
  - ولا API key
  - ولا تحميل موديل من الإنترنت
  - ولا اعتماد على أي خدمة خارجية

طبيعة الحل: مش semantic embedding عميق زي BERT/OpenAI (يعني مش هيفهم
المرادفات، بس هيلاقي تداخل فعلي في الكلمات المشتركة بين النص والمستندات
— وده كافي لحالتنا: query زي "SQL query built with string concatenation"
هيتطابق كويس مع مستند فيه "SQL Injection" و"parameterized queries").

**توصية للفريق:** لو حبيتوا جودة أعلى بعدين، استبدلوا الكلاس ده بـ
`HuggingFaceEmbedding` (محتاج تحميل موديل، شغال offline بعد أول تحميل)
أو `OpenAIEmbedding` (لو متوفر API key). الاستبدال سطر واحد بس في
`configure_local_embeddings()" تحت — باقي الكود مش هيتغير.
"""
import hashlib
import math
import re
from typing import List

from llama_index.core.base.embeddings.base import BaseEmbedding

_TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]+")
_DIM = 256  # حجم الـvector — مش لازم يتغير إلا لو عايزين دقة/سرعة مختلفة


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _hash_index(token: str, dim: int = _DIM) -> int:
    # hashlib بدل hash() المدمجة في بايثون عشان تكون ثابتة بين تشغيلات مختلفة
    # (hash() نفسها بتتغير بين كل تشغيل للبرنامج بسبب PYTHONHASHSEED العشوائي).
    digest = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(digest, 16) % dim


def _embed_text(text: str) -> List[float]:
    vec = [0.0] * _DIM
    for token in _tokenize(text):
        vec[_hash_index(token)] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


class LocalHashingEmbedding(BaseEmbedding):
    """Embedding محلي بالكامل (hashing trick) — بديل مؤقت لحد ما يتوفر
    embedding provider حقيقي (HuggingFace محلي أو OpenAI API)."""

    def _get_query_embedding(self, query: str) -> List[float]:
        return _embed_text(query)

    def _get_text_embedding(self, text: str) -> List[float]:
        return _embed_text(text)

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [_embed_text(t) for t in texts]

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return _embed_text(query)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return _embed_text(text)


def configure_local_embeddings() -> None:
    """
    بتستدعى مرة واحدة بس (عند أول import لـ rag_search) عشان تخلي
    LlamaIndex يستخدم الـembedding المحلي ده بدل ما يحاول يتصل بـOpenAI
    ويفشل (أو يعلّق) لو مفيش API key.
    """
    from llama_index.core.settings import Settings
    Settings.embed_model = LocalHashingEmbedding()
