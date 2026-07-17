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
