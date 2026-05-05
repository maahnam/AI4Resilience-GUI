from __future__ import annotations

import json

import numpy as np
import pandas as pd

from lahso.web.serialization import dataframe_records, json_safe


def test_json_safe_converts_numpy_scalars_and_nan() -> None:
    payload = json_safe(
        {
            "int_value": np.int64(7),
            "float_value": np.float64(2.5),
            "nan_value": np.float64("nan"),
            "array_value": np.array([np.int64(1), np.int64(2)]),
        }
    )

    assert payload == {
        "int_value": 7,
        "float_value": 2.5,
        "nan_value": None,
        "array_value": [1, 2],
    }
    json.dumps(payload)


def test_dataframe_records_are_json_serializable() -> None:
    records = dataframe_records(
        pd.DataFrame(
            [
                {
                    "Episode": np.int64(1),
                    "Total Cost": np.float64(123.5),
                    "Total Reward": np.float64("nan"),
                }
            ]
        )
    )

    assert records == [{"Episode": 1, "Total Cost": 123.5, "Total Reward": None}]
    json.dumps(records)
