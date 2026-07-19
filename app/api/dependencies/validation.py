from fastapi import HTTPException, UploadFile, File


async def validate_gif_file(
        file: UploadFile = File()
) -> UploadFile:
    """
    Зависимость для проверки, что загружаемый файл — это GIF.
    
    :param file: Объект загруженного файла от FastAPI.
    :return: Исходный объект файла, если он успешно прошёл валидацию.
    
    :raises HTTPException: С кодом 400, если MIME-тип не равен 'image/gif'.
    :raises HTTPException: С кодом 400, если заголовок файла не содержит сигнатуру 'GIF87a' или 'GIF89a'.
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
