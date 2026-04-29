import logging
from collections.abc import Iterator

from app.config import settings

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Raised when the AI service is unavailable or misconfigured."""


class AIClient:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            import anthropic

            if not settings.ai_enabled:
                raise AIServiceError("AI service is disabled")
            if not settings.anthropic_api_key:
                raise AIServiceError("ANTHROPIC_API_KEY not configured")
            kwargs = {"api_key": settings.anthropic_api_key}
            if settings.ai_base_url:
                kwargs["base_url"] = settings.ai_base_url
            self._client = anthropic.Anthropic(**kwargs)
        return self._client

    def complete(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int | None = None,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str:
        """Synchronous completion. Callers wrap with asyncio.to_thread."""
        import anthropic

        model = model or settings.ai_model
        max_tokens = max_tokens or settings.ai_max_tokens
        last_error = None

        for attempt in range(2):
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                content = response.content
                if content:
                    for block in content:
                        if block.type == "text":
                            return block.text
                return ""

            except anthropic.APIStatusError as e:
                last_error = e
                logger.warning("Claude API error (attempt %d): %s", attempt + 1, e)
                if attempt == 0:
                    continue
            except anthropic.APITimeoutError as e:
                last_error = e
                logger.warning("Claude API timeout (attempt %d): %s", attempt + 1, e)
                if attempt == 0:
                    continue

        raise AIServiceError(f"Claude API failed after retries: {last_error}")

    def complete_stream(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int | None = None,
        model: str | None = None,
    ) -> Iterator[str]:
        """Synchronous streaming completion. Yields text chunks."""
        import anthropic

        model = model or settings.ai_model
        max_tokens = max_tokens or settings.ai_max_tokens

        try:
            with self.client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except anthropic.APIStatusError as e:
            logger.error("Claude API streaming error: %s", e)
            raise AIServiceError(f"Claude API streaming failed: {e}")
        except anthropic.APITimeoutError as e:
            logger.error("Claude API streaming timeout: %s", e)
            raise AIServiceError(f"Claude API streaming timeout: {e}")


ai_client = AIClient()
