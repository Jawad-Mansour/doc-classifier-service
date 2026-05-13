import os
import paramiko

from app.core.config import settings


REMOTE_FOLDER = settings.SFTP_REMOTE_FOLDER
LOCAL_FOLDER = "sftp_downloads"


def connect_sftp():
    transport = paramiko.Transport(
        (
            settings.SFTP_HOST,
            settings.SFTP_PORT
        )
    )

    transport.connect(
        username=settings.SFTP_USERNAME,
        password=settings.SFTP_PASSWORD
    )

    return paramiko.SFTPClient.from_transport(
        transport
    )


def list_files(
    sftp,
    remote_folder=REMOTE_FOLDER
):
    try:
        return sftp.listdir(remote_folder)

    except FileNotFoundError:
        print(
            f"Remote folder not found: "
            f"{remote_folder}"
        )

        return []


def download_file(
    sftp,
    filename,
    remote_folder=REMOTE_FOLDER,
    local_folder=LOCAL_FOLDER
):
    os.makedirs(
        local_folder,
        exist_ok=True
    )

    remote_path = (
        f"{remote_folder}/{filename}"
    )

    local_path = os.path.join(
        local_folder,
        filename
    )

    sftp.get(
        remote_path,
        local_path
    )

    return local_path


def is_valid_tiff(filename: str):
    return filename.lower().endswith(
        (
            ".tif",
            ".tiff"
        )
    )