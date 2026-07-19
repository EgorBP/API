from pathlib import Path
import anyio
from fastapi import UploadFile
from app import settings


class LocalStorageProvider:
    def __init__(
            self,
            media_path: str = str(settings.MEDIA_DIR),
            base_path: str = str(settings.BASE_DIR)
    ):
        self.media_path = anyio.Path(media_path)
        self.base_path = Path(base_path)
    
    async def save_file(
            self, 
            file: UploadFile, 
            filename: str
    ) -> str:
        """
        Сохраняет файл на диск и возвращает путь относительно BASE_DIR        
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
        """
        Удаляет файл, принимая его относительный путь из базы данных.
        """
        target_path = (self.base_path / file_key).resolve()

        absolute_media = Path(str(self.media_path)).resolve()

        if not target_path.is_relative_to(absolute_media):
            raise PermissionError("Попытка удаления файла за пределами разрешенной директории")

        async_target = anyio.Path(target_path)

        if not await async_target.exists():
            raise FileNotFoundError(f"Файл по пути {file_key} не найден")

        await async_target.unlink()
