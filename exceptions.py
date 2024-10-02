class RequestError(Exception):
    """Некорректный запрос к серверу."""

    def __init__(self, status, request_data):
        """Инициализация исключения."""
        self.status = status
        self.request_data = request_data
        super().__init__(
            f'Неверный статус ответа {status}'
            f'Данные запроса: {request_data}'
        )


class SendError(Exception):
    """Ошибка при отправке сообщения."""

    def __init__(self, message):
        """Инициализация исключения."""
        super().__init__(message)


class ParseError(Exception):
    """Ошибка при чтении ответа."""
