import json
from typing import Any


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def loads_list(value: str | None) -> list[str]:
    if not value:
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed]
