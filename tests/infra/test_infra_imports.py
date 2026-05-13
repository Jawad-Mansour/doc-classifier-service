def test_infra_modules_import_without_live_services():
    import app.infra.blob.minio_client  # noqa: F401
    import app.infra.queue.rq_client  # noqa: F401
    import app.infra.queue.rq_queue  # noqa: F401
    import app.infra.sftp.client  # noqa: F401
    import app.workers.sftp_ingest_worker  # noqa: F401
