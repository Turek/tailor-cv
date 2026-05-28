"""Provider-neutral LLM client interface and Usage record."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass(frozen=True)
class Usage:
    """Token accounting for one LLM call, provider-neutral.

    `cache_read` / `cache_write` are None for providers that don't expose prompt
    caching (e.g. Google Antigravity). When all aggregated usages have None for
    both, the summary view omits the cache lines.
    """

    input_tokens: int
    output_tokens: int
    cache_read: Optional[int] = None
    cache_write: Optional[int] = None


@runtime_checkable
class LLMClient(Protocol):
    """Single entry point both backends implement.

    Implementations build provider-specific request shapes from the two prompts
    plus the KB, and return raw model text plus a Usage record. Code-fence
    stripping and empty-response handling live in the dispatcher, not here.
    """

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        kb: str,
        cache: bool = False,
    ) -> tuple[str, Usage]: ...
