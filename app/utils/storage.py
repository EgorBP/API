import hashlib
from fastapi import UploadFile


async def create_unique_filename_and_hash(
        file: UploadFile
) -> tuple[str, str]:
    """Computes a content hash for a file and derives a filename from it.

    Streams the file in 1 MB chunks to hash it without loading the whole
    file into memory, then rewinds it so the caller can still read its
    contents afterward (e.g. to save it to storage).

    Args:
        file: The uploaded file to hash. Its extension is preserved in
            the generated filename, defaulting to "gif" if none is
            present.

    Returns:
        A tuple of `(unique_filename, file_hash)`, where
        `unique_filename` is `"{file_hash}.{ext}"` and `file_hash` is the
        hex-encoded SHA-256 digest of the file's contents.
    """
    await file.seek(0)

    sha256_hash = hashlib.sha256()
    while chunk := await file.read(1024 * 1024):
        sha256_hash.update(chunk)

    file_hash = sha256_hash.hexdigest()

    await file.seek(0)

    file_ext = file.filename.split(".")[-1] if "." in file.filename else "gif"
    unique_filename = f"{file_hash}.{file_ext.lower()}"

    return unique_filename, file_hash
