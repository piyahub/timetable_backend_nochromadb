import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Uses ChromaDB's built-in default embedding function
# which uses onnxruntime (lightweight, no torch needed)
from chromadb.utils import embedding_functions

_ef = None

def get_ef():
    global _ef
    if _ef is None:
        _ef = embedding_functions.DefaultEmbeddingFunction()
    return _ef

def embed(text: str) -> list:
    """
    Embeds text using ChromaDB's default embedding function.
    Uses onnxruntime under the hood — lightweight, no torch, no GPU needed.
    """
    ef = get_ef()
    result = ef([text])
    return result[0]