"""
Milestone 1 test: prove query_globocan_data works standalone before
wiring it into the Disease Agent.

Unlike the other three data tools (PubMed, ClinicalTrials, openFDA), this
one does not call a live API — GLOBOCAN has none. It reads a cached
export from S3. These tests use a mocked S3 client rather than hitting
real AWS, so they run offline.

Run:
    pip install -r requirements.txt
    python -m pytest test_query_globocan_data.py
"""
import sys
import os
import json
import io

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools", "query_globocan_data"))


class _FakeS3Client:
    """Minimal stand-in for boto3's S3 client, just enough for these tests."""

    def __init__(self, objects: dict):
        self._objects = objects  # key -> dict (will be json-encoded)

    def get_object(self, Bucket, Key):
        if Key not in self._objects:
            from botocore.exceptions import ClientError
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
                "GetObject",
            )
        body = json.dumps(self._objects[Key]).encode("utf-8")
        return {"Body": io.BytesIO(body)}


def test_returns_cached_data_when_export_exists(monkeypatch):
    os.environ["DATA_BUCKET_NAME"] = "test-bucket"
    import handler  # noqa: E402

    fake_data = {
        "data_year": 2024,
        "records": [{"country": "Global", "incidence": 1930000, "mortality": 900000}],
    }
    monkeypatch.setattr(handler, "s3", _FakeS3Client({
        "globocan/colorectal_cancer.json": fake_data,
    }))
    monkeypatch.setattr(handler, "BUCKET", "test-bucket")

    result = handler.lambda_handler({"therapeutic_area": "Colorectal Cancer"}, context=None)

    assert result["agent"] == "disease_agent"
    assert result["tool"] == "query_globocan_data"
    assert result["record_count"] == 1
    assert "error" not in result


def test_returns_clear_error_when_no_export_cached(monkeypatch):
    import handler  # noqa: E402

    monkeypatch.setattr(handler, "s3", _FakeS3Client({}))
    monkeypatch.setattr(handler, "BUCKET", "test-bucket")

    result = handler.lambda_handler({"therapeutic_area": "Some Unmapped Cancer"}, context=None)

    assert result["records"] == []
    assert "error" in result
    assert "No cached GLOBOCAN export found" in result["error"]
