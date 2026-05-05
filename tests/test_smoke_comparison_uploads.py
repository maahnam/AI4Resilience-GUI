from __future__ import annotations

from io import BytesIO

from werkzeug.datastructures import FileStorage, MultiDict

from lahso.web.services import compare_result_uploads


COMPARISON_HEADER = (
    "Episode,Total Cost,Total Storage Cost,Total Travel Cost,"
    "Total Handling Cost,Total Delay Penalty\n"
)


def test_compare_result_uploads_accepts_two_policy_csvs() -> None:
    file1 = _csv_upload(
        "always_wait.csv",
        "1,100,10,50,25,15\n2,200,20,90,55,35\n",
    )
    file2 = _csv_upload(
        "greedy_policy.csv",
        "1,130,13,62,32,23\n2,180,18,80,50,32\n",
    )

    result = compare_result_uploads(
        MultiDict([("label1", "Always Wait"), ("label2", "Greedy Policy")]),
        MultiDict([("file1", file1), ("file2", file2)]),
    )

    assert result["success"] is True
    rows = result["comparison_data"]
    assert rows[0]["Total Cost Delta"] == 30
    assert rows[0]["Total Cost Delta Sign"] == "Always Wait"
    assert rows[1]["Total Cost Delta"] == -20
    assert rows[1]["Total Cost Delta Sign"] == "Greedy Policy"


def test_compare_result_uploads_requires_csv_files() -> None:
    result = compare_result_uploads(MultiDict(), MultiDict())

    assert result == {"success": False, "error": "Two CSV uploads are required"}


def _csv_upload(filename: str, rows: str) -> FileStorage:
    return FileStorage(
        stream=BytesIO((COMPARISON_HEADER + rows).encode()),
        filename=filename,
        content_type="text/csv",
    )
