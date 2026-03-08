from typing import Any, NotRequired, TypedDict


class ValueWithSource(TypedDict, total=False):
    value: Any
    source_text: NotRequired[str]
