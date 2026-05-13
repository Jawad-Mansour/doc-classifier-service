from __future__ import annotations

from pathlib import PurePosixPath

import paramiko

from app.core.config import settings


class SFTPClient:
    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        remote_folder: str | None = None,
        processed_folder: str | None = None,
    ) -> None:
        self.host = host or settings.SFTP_HOST
        self.port = port or settings.SFTP_PORT
        self.username = username or settings.SFTP_USERNAME
        self.password = password or settings.SFTP_PASSWORD
        self.remote_folder = remote_folder or settings.SFTP_REMOTE_FOLDER
        self.processed_folder = processed_folder or settings.SFTP_PROCESSED_FOLDER
        self._transport: paramiko.Transport | None = None
        self._sftp: paramiko.SFTPClient | None = None

    def connect(self) -> SFTPClient:
        self._transport = paramiko.Transport((self.host, self.port))
        self._transport.connect(username=self.username, password=self.password)
        self._sftp = paramiko.SFTPClient.from_transport(self._transport)
        return self

    def close(self) -> None:
        if self._sftp is not None:
            self._sftp.close()
        if self._transport is not None:
            self._transport.close()

    def __enter__(self) -> SFTPClient:
        return self.connect()

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    @property
    def sftp(self) -> paramiko.SFTPClient:
        if self._sftp is None:
            raise RuntimeError("SFTP client is not connected")
        return self._sftp

    def list_files(self) -> list[str]:
        return self.sftp.listdir(self.remote_folder)

    def download_bytes(self, filename: str) -> bytes:
        remote_path = str(PurePosixPath(self.remote_folder) / filename)
        with self.sftp.open(remote_path, "rb") as remote_file:
            return remote_file.read()

    def move_to_processed(self, filename: str) -> None:
        self._ensure_processed_folder()
        source = str(PurePosixPath(self.remote_folder) / filename)
        destination = str(PurePosixPath(self.processed_folder) / filename)
        self.sftp.rename(source, destination)

    def _ensure_processed_folder(self) -> None:
        try:
            self.sftp.mkdir(self.processed_folder)
        except OSError:
            pass


def is_valid_tiff(filename: str) -> bool:
    return filename.lower().endswith((".tif", ".tiff"))
