from dataclasses import dataclass
from typing import Literal

Role = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str

    def to_ollama(self) -> dict:
        return {"role": self.role, "content": self.content}


def system_message(content: str) -> Message:
    return Message(role="system", content=content)


def user_message(content: str) -> Message:
    return Message(role="user", content=content)
