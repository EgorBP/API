import hashlib
from fastapi import UploadFile


# TODO: update dockstring
async def create_unique_filename_and_hash(
        file: UploadFile
) -> tuple[str, str]:
    await file.seek(0)

    sha256_hash = hashlib.sha256()
    while chunk := await file.read(1024 * 1024):
        sha256_hash.update(chunk)

    file_hash = sha256_hash.hexdigest()

    await file.seek(0)

    file_ext = file.filename.split(".")[-1] if "." in file.filename else "gif"
    unique_filename = f"{file_hash}.{file_ext.lower()}"

    return unique_filename, file_hash
