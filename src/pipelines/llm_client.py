from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClientProtocol(Protocol):

    def chat(self, model: str, messages: list[dict], options: dict) -> dict: ...


class OllamaLLMClient:
    def __init__(self, host: str) -> None:
        from ollama import Client

        self._client = Client(host=host)

    def chat(self, model: str, messages: list[dict], options: dict) -> dict:
        return self._client.chat(
            model=model,
            messages=messages,
            options=options,
        )
