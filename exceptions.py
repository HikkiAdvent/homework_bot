class RequestError(Exception):
    """Некорректный запрос к серверу."""

    def __init__(self, status, error):
        """Инициализация класса."""
        self.status = status
        self.error = error
        super().__init__(
            f"При обращении к серверу вышла ошибка {status}"
            f"{error}"
        )


class SendError(Exception):
    """Ошибка при отправке сообщения."""


class ParseError(Exception):
    """Ошибка при парсинге ответа."""
