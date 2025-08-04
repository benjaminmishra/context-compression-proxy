"""Naive QR-based context reducer used by the proxy.

This implementation is intentionally light-weight: it does not load any
heavyweight model but demonstrates the interface that a real retriever would
expose.  The `reduce` function shortens the context to a fixed number of
whitespace-delimited tokens.
"""

from functools import lru_cache
from typing import Iterable

MAX_TOKENS = 128


def _truncate(tokens: Iterable[str], limit: int) -> str:
    return " ".join(list(tokens)[:limit])


@lru_cache
def get_retriever() -> int:
    """Placeholder for model/LoRA loading.

    A real implementation would load the base model and apply any PEFT/LoRA
    weights here.  Returning a dummy value keeps the function trivial while
    still demonstrating the cached load behaviour.
    """

    return 1


def reduce(query: str, context: str) -> str:
    """Condense `context` to at most `MAX_TOKENS` tokens.

    Parameters
    ----------
    query:
        The user query; unused in the naive implementation but part of the
        interface.
    context:
        The conversation history to reduce.
    """

    get_retriever()  # ensure the retriever is initialised once

    tokens = context.split()
    if len(tokens) <= MAX_TOKENS:
        return context
    return _truncate(tokens, MAX_TOKENS)
