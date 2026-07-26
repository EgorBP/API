from typing import Protocol
from fastapi import UploadFile


class StorageProvider(Protocol):
    """Interface that any file storage backend in the system must implement.

    Allows swapping the storage backend (local disk, S3, etc.) without
    changing service code — anything conforming to this protocol can be
    passed wherever a `StorageProvider` is expected.
    """

    async def save_file(
            self, 
            file: UploadFile, 
            filename: str
    ) -> str:
        """Saves an uploaded file to the target storage.

        If a file with the same `filename` already exists in storage,
        implementations may skip re-writing it and simply return its
        path, since callers typically derive `filename` from the file's
        content hash.

        Args:
            file: The uploaded file, as a byte stream.
            filename: The name the file should be stored under.

        Returns:
            The path or key under which the file was stored — e.g. a path
            relative to the project root for local disk, or an object key
            for S3.

        Raises:
            IOError: On a local-disk write failure (no permissions, out of
                space).
            RuntimeError: On a network failure or remote provider error.
        """
        ...

    async def delete_file(
            self, 
            file_key: str
    ) -> None:
        """Deletes a file from storage.

        Args:
            file_key: The path or object key previously returned by
                `save_file`.

        Raises:
            FileNotFoundError: If no file exists at `file_key`.
            PermissionError: If `file_key` resolves outside the allowed
                storage directory.
            RuntimeError: If the storage backend is unreachable or the
                deletion otherwise fails.
        """
        ...
