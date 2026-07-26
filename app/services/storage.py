from pathlib import Path

import anyio
from fastapi import UploadFile

from app import settings


class LocalStorageProvider:
    """`StorageProvider` implementation that saves files to local disk.

    Files are stored under `media_path` and referenced elsewhere in the
    app by a path relative to `base_path` (the project root), so the
    stored value stays valid regardless of the machine's absolute
    filesystem layout.
    """
    
    def __init__(
            self,
            media_path: str = str(settings.MEDIA_DIR),
            base_path: str = str(settings.BASE_DIR)
    ):
        """Initializes the provider.

        Args:
            media_path: Absolute directory where files are stored.
                Defaults to `settings.MEDIA_DIR`.
            base_path: Absolute project root, used to compute the
                relative paths returned by `save_file`. Defaults to
                `settings.BASE_DIR`.
        """
        self.media_path = anyio.Path(media_path)
        self.base_path = Path(base_path)
    
    async def save_file(
            self, 
            file: UploadFile, 
            filename: str
    ) -> str:
        """Saves a file to disk under `media_path`, streamed in chunks.

        If a file already exists at the target path, the write is
        skipped entirely and the existing file's relative path is
        returned — this relies on `filename` being derived from the
        file's content hash upstream, so an existing file at that path is
        guaranteed to have identical content.

        Args:
            file: The uploaded file, as a byte stream.
            filename: The name to store the file under, within
                `media_path`.

        Returns:
            The file's path relative to `base_path`, suitable for storing
            in the database.

        Raises:
            IOError: If the target directory can't be created or the
                file can't be written (no permissions, out of space).
        """
        await self.media_path.mkdir(parents=True, exist_ok=True)
        full_destination_path = self.media_path / filename

        relative_path = Path(str(full_destination_path)).relative_to(self.base_path)

        if await full_destination_path.exists():
            return str(relative_path)

        await file.seek(0)
        async with await full_destination_path.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                await buffer.write(chunk)

        return str(relative_path)
    
    async def delete_file(
            self,
            file_key: str
    ) -> None:
        """Deletes a file from disk, given its path relative to `base_path`.

        Resolves `file_key` to an absolute path and verifies it stays
        within `media_path` before deleting, to prevent a crafted
        `file_key` (e.g. containing `..`) from deleting files outside the
        media directory.

        Args:
            file_key: The file's path relative to `base_path`, as
                returned by `save_file`.

        Raises:
            PermissionError: If the resolved path falls outside
                `media_path`.
            FileNotFoundError: If no file exists at the resolved path.
        """
        target_path = (self.base_path / file_key).resolve()

        absolute_media = Path(str(self.media_path)).resolve()

        if not target_path.is_relative_to(absolute_media):
            raise PermissionError("Attempted to delete a file outside the allowed directory.")

        async_target = anyio.Path(target_path)

        if not await async_target.exists():
            raise FileNotFoundError(f"No file found at path {file_key}.")

        await async_target.unlink()
