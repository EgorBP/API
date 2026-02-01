from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import _BaseCRUD
from app.models import UserGifTag


class UserGifTagCRUD(_BaseCRUD):
    """
    CRUD для модели UserGifTag.

    Переопределяется только логика создания связи.
    Остальные операции наследуются от BaseCRUD.    
    """

    def __init__(self, async_session: AsyncSession):
        super().__init__(async_session, model=UserGifTag)

    async def create_user_gif_tag(
            self,
            user_id: int,
            gif_id: int,
            tag_id: int,
    ):
        """
        Создаёт связь между пользователем, гифкой и тегом
        или возвращает существующую.

        При конфликте по уникальному ограничению
        (user_id, gif_id, tag_id) новая запись не создаётся,
        а возвращается существующая строка.

        :return: Row с колонками модели UserGifTag.
        """
        return await super().create_instance({
            UserGifTag.user_id: user_id,
            UserGifTag.gif_id: gif_id,
            UserGifTag.tag_id: tag_id,
        })
