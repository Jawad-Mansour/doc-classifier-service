def test_smoke_ingest_contract():
    payload = {
        "batch_id": 1,
        "blob_path": "raw/test.tiff"
    }

    assert payload["batch_id"] == 1
    assert payload["blob_path"].startswith("raw/")
    assert payload["blob_path"].endswith(".tiff")