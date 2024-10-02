import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot, apihelper

from exceptions import RequestError, SendError, ParseError


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens() -> bool:
    """Проверяет наличие данных в окружении."""
    tokens = {
        'Токен Практикума': PRACTICUM_TOKEN,
        'ID чата': TELEGRAM_CHAT_ID,
        'Токен Телеграмма': TELEGRAM_TOKEN,
    }
    values = [i for i in tokens.values()]
    if all(values) is True:
        return True
    tokens_failure = [name for name, token in tokens.items() if token is None]
    logging.critical(f'Отсутствуют {tokens_failure}')
    return False


def send_message(bot: TeleBot, message: str) -> None:
    """Отправляет сообщение от бота."""
    try:
        logging.debug('Бот начал отправку сообщения')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Бот отправил сообщение: {message}')
    except (apihelper.ApiException,
            requests.RequestException
            ) as error:
        logging.error(f'При отправке сообщения возникла ошибка. {error}')
        raise SendError('При отправе сообщения возникла ошибка') from error


def get_api_answer(timestamp: int) -> dict:
    """Получает ответ от сервера."""
    request_kwargs = {
        'endpoint': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    try:
        logging.debug('Начато обращение к серверу')
        response = requests.get(**request_kwargs)
        logging.debug('Ответ получен')
        if response.status_code != HTTPStatus.OK:
            raise RequestError(response.status_code, request_kwargs)
    except requests.RequestException as error:
        logging.error(f'Ошибка при запросе. {error}')
    except RequestError as error:
        logging.error(
            f'Неверный статус ответа {response.status_code}'
            f'Данные запроса: {request_kwargs}'
        )
        raise RequestError from error
    else:
        return response.json()


def check_response(response: dict) -> bool:
    """Проверяет ответ от сервера на условие, что статус изменился."""
    if not isinstance(response, dict):
        logging.error(
            f'Получен неправильный ответ{response}'
            'Ответ не является словарем.'
        )
        raise TypeError
    if not isinstance(response.get('homeworks'), list):
        logging.error('Значение "homeworks" не является списком.')
        raise TypeError
    if response.get('homeworks') == []:
        logging.debug('Статус работы не изменился')
        return False
    return True


def parse_status(homework: dict) -> str:
    """Возвращает статус работы."""
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if not homework_name:
        raise ParseError
    if status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    logging.error(f'Неизвестный статус работы {status}')
    raise ParseError


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Программа завершает работу')
        sys.exit()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                message = parse_status(response['homeworks'][0])
                send_message(bot, message)
        except Exception as error:
            send_message(bot, f'Во время работы возникли ошибки. {error}')
        finally:
            current_date = response.get('current_date')
            logging.debug(f'Старая дата запроса {timestamp}')
            timestamp = current_date if current_date else timestamp
            logging.debug(f'Новая дата запроса {timestamp}')
            logging.debug(f'Следующий запрос будет через {RETRY_PERIOD}')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        filemode='w',
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )
    main()
