class TgUserNotFoundError(Exception):
    def __init__(
            self, 
            tg_user_id: int | None = None
    ):
        self.tg_user_id = tg_user_id
        
        super().__init__(f"User with tg_id {tg_user_id} not found")


class UserGifsNotFoundError(Exception):
    def __init__(
            self,
            source: str | None = None,
            user_id: int | None = None,
            tg_user_id: int | None = None
    ):
        self.source = source
        self.user_id = user_id
        self.tg_user_id = tg_user_id
        
        super().__init__(f"User GIF's not found")


class GifNotFoundError(Exception):
    def __init__(
            self,
            gif_id: int,
            user_id: int | None = None
    ):
        self.gif_id = gif_id
        self.user_id = user_id

        super().__init__(f"GIF with ID {self.gif_id} not found")


class UserTagsNotFoundError(Exception):
    def __init__(
            self,
            user_id: int
    ):
        self.user_id = user_id

        super().__init__(f"Tags for user with ID {self.gif_id} not found")
