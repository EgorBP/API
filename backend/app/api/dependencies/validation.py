from fastapi import File, HTTPException, UploadFile


async def validate_gif_file(
        file: UploadFile = File()
) -> UploadFile:
    """FastAPI dependency validating an uploaded file is a genuine GIF or MP4.

    Checks both the declared MIME type and the actual file header/magic
    bytes, so a file with a spoofed `Content-Type` is still rejected.

    Args:
        file: The uploaded file.

    Returns:
        The same file object, with its read position reset to the start.

    Raises:
        HTTPException: 400, if the declared MIME type isn't
            `image/gif` or `video/mp4`, or if the file's header doesn't
            match the declared type.
    """
    ALLOWED_MIME_TYPES = {"image/gif", "video/mp4"}

    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only GIF and MP4 are allowed."
        )

    file_head = await file.read(12)
    await file.seek(0)

    is_valid = False

    if file.content_type == "image/gif":
        if file_head[:6] in (b"GIF87a", b"GIF89a"):
            is_valid = True

    elif file.content_type == "video/mp4":
        if len(file_head) >= 8 and file_head[4:8] == b"ftyp":
            is_valid = True

    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"File is corrupted or disguised as {file.content_type.split('/')[-1].upper()}."
        )

    return file
