from typing import Protocol
from fastapi import UploadFile


class StorageProvider(Protocol):
    """Интерфейс, которому должно соответствовать любое хранилище файлов в системе."""

    async def save_file(
            self, 
            file: UploadFile, 
            filename: str
    ) -> str:
        """
        Асинхронно сохраняет загруженный файл в целевое хранилище
        или возвращает его путь если файл существует без сохранения.

        :param file: Объект файла от FastAPI, содержащий поток байтов.
        :param filename: Уникальное имя, под которым файл должен быть сохранен.
        :return: Относительный путь от корня проекта (для диска) или ключ объекта (для S3).

        :raises IOError: Ошибка записи на локальный диск (нет прав, закончилось место).
        :raises RuntimeError: Сбой сети или отказ удаленного облачного провайдера.
        """
        ...

    async def delete_file(
            self, 
            file_key: str
    ) -> None:
        """
        Асинхронно удаляет файл из хранилища.

        :param file_key: Относительный путь или ключ объекта, ранее возвращенный методом `save_file`.
        :return: None

        :raises FileNotFoundError: Если указанный файл отсутствует в хранилище.
        :raises PermissionError: Попытка выйти за пределы разрешенной медиа-директории.
        :raises RuntimeError: Если хранилище недоступно или произошел сбой удаления.
        """
        ...
