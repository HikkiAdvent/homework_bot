class RequestError(Exception):
    """Некорректный запрос к серверу."""


class SendError(Exception):
    """Ошибка при отправке сообщения."""


class ParseError(Exception):
    """Ошибка при парсинге ответа."""
