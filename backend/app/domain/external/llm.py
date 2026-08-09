from typing import Any, Dict, List, Optional, Protocol
from app.domain.models.message import LLMMessage


class LLM(Protocol):
    """LLM gateway interface.

    Abstracts the underlying model framework (LangChain, raw SDK, …) away from
    the domain. Implementations live in ``infrastructure/external/llm`` and are
    responsible for translating :class:`LLMMessage` to/from framework types,
    tool binding, JSON repair and retries.
    """

    async def ask(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[str] = None,
        tool_choice: Optional[str] = None,
    ) -> LLMMessage:
        """Send a chat request and return the assistant message.

        Args:
            messages: Full conversation context as domain messages.
            tools: Optional OpenAI-style function schemas for tool calling.
            response_format: Optional response format hint (e.g. ``json_object``).
            tool_choice: Optional tool choice directive (e.g. ``none``).

        Returns:
            The assistant :class:`LLMMessage`, with any tool calls parsed.
        """
        ...

    async def ask_stream(
        self,
        messages: List[LLMMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[str] = None,
        tool_choice: Optional[str] = None,
    ):
        """Send a chat request and yield assistant message chunks.

        Args:
            messages: Full conversation context as domain messages.
            tools: Optional OpenAI-style function schemas for tool calling.
            response_format: Optional response format hint (e.g. ``json_object``).
            tool_choice: Optional tool choice directive (e.g. ``none``).

        Yields:
            Chunks of text content and tool call deltas as they arrive.
        """
        ...
        
    async def parse_json(self, text: str) -> Dict[str, Any]:
        """Extract/repair a JSON object from raw model output."""
        ...
