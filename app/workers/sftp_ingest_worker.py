import time

from app.infra.sftp.watcher import (
    connect_sftp,
    list_files,
    download_file,
    is_valid_tiff,
)

from app.infra.blob.minio_client import upload_file
from app.infra.queue.rq_queue import classification_queue


POLL_INTERVAL_SECONDS = 5
PROCESSED_FILES = set()


def run():
    print("SFTP ingest worker started...")

    while True:
        sftp = None

        try:
            sftp = connect_sftp()
            files = list_files(sftp)

            for filename in files:
                if filename in PROCESSED_FILES:
                    continue

                if not is_valid_tiff(filename):
                    print(f"Skipping invalid file: {filename}")
                    PROCESSED_FILES.add(filename)
                    continue

                print(f"Found TIFF file: {filename}")

                local_path = download_file(sftp, filename)
                blob_path = f"raw/{filename}"

                upload_file(local_path, blob_path)

                job_payload = {
                    "batch_id": 1,
                    "blob_path": blob_path,
                }

                classification_queue.enqueue(
                    "app.workers.inference_worker.process_document",
                    job_payload,
                )

                print(f"Queued job for: {blob_path}")

                PROCESSED_FILES.add(filename)

        except Exception as e:
            print(f"SFTP ingest error: {e}")

        finally:
            if sftp is not None:
                sftp.close()

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()