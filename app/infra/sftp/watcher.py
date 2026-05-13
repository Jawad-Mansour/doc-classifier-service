from app.infra.sftp.client import SFTPClient, is_valid_tiff


def connect_sftp() -> SFTPClient:
    return SFTPClient().connect()


def list_files(sftp: SFTPClient) -> list[str]:
    return sftp.list_files()


def download_bytes(sftp: SFTPClient, filename: str) -> bytes:
    return sftp.download_bytes(filename)


def move_to_processed(sftp: SFTPClient, filename: str) -> None:
    sftp.move_to_processed(filename)


__all__ = [
    "SFTPClient",
    "connect_sftp",
    "download_bytes",
    "is_valid_tiff",
    "list_files",
    "move_to_processed",
]
