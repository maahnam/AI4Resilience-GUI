from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any


def dataframe_records(dataframe: Any, limit: int | None = None) -> list[dict[str, Any]]:
    bounded = dataframe
    if limit is not None and len(dataframe) > limit:
        bounded = dataframe.tail(limit)
    return json_safe(bounded.to_dict("records"))


def json_safe(value: Any) -> Any:
    if value is None or isinstance(value, str | bool):
        return value

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return value if math.isfinite(value) else None

    if isinstance(value, Decimal):
        safe_value = float(value)
        return safe_value if math.isfinite(safe_value) else None

    if isinstance(value, datetime | date):
        return value.isoformat()

    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except (AttributeError, TypeError, ValueError):
            pass

    if hasattr(value, "tolist"):
        try:
            return json_safe(value.tolist())
        except (AttributeError, TypeError, ValueError):
            pass

    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}

    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        return [json_safe(item) for item in value]

    return str(value)
