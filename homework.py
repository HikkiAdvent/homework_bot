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

TOKENS = {
    'Токен Практикума': PRACTICUM_TOKEN,
    'ID чата': TELEGRAM_CHAT_ID,
    'Токен Телеграмма': TELEGRAM_TOKEN,
}


def check_tokens(tokens: dict) -> bool:
    """Проверяет наличие данных в окружении."""
    TOKENS = {
        'Токен Практикума': PRACTICUM_TOKEN,
        'ID чата': TELEGRAM_CHAT_ID,
        'Токен Телеграмма': TELEGRAM_TOKEN,
    }
    tokens_failure = [name for name, token in TOKENS.items() if token is None]
    if tokens_failure:
        logging.critical(f'Отсутствуют {tokens_failure}')
        return False
    return True


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
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    try:
        logging.debug('Начато обращение к серверу')
        response = requests.get(**request_kwargs)
        logging.debug('Ответ получен')
    except requests.RequestException as error:
        raise RequestError(f'Ошибка во время выполнения запроса: {error}')
    if response.status_code != HTTPStatus.OK:
        raise RequestError(
            f'Ошибочный статус{response.status_code, request_kwargs}'
        )
    return response.json()


def check_response(response: dict) -> bool:
    """Проверяет ответ от сервера на условие, что статус изменился."""
    if not isinstance(response, dict):
        logging.error(
            f'Получен неправильный ответ{response}'
            'Ответ не является словарем.'
        )
        raise TypeError('Ответ сервера получен не в виде словаря.')
    if 'homeworks' not in response:
        raise TypeError('В ответе отсутствует ключ "homeworks"')
    if not isinstance(response.get('homeworks'), list):
        logging.error('Значение "homeworks" не является списком.')
        raise TypeError('Значение "homeworks" не является списком.')
    if not response.get('homeworks'):
        logging.debug('Статус работы не изменился.')
        return False
    return True


def parse_status(homework: dict) -> str:
    """Возвращает статус работы."""
    status = homework.get('status')
    homework_name = homework.get('homework_name')
    if not (status and homework_name):
        raise ParseError(
            f'Отсутствуют нужные ключи {status=}, {homework_name=}'
        )
    if status not in HOMEWORK_VERDICTS:
        logging.error(f'Неизвестный статус работы {status}.')
        raise ParseError('Неизвестный статус работы.')
    return (
        f'Изменился статус проверки работы "{homework_name}".'
        f'{HOMEWORK_VERDICTS[status]}'
    )


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens(TOKENS):
        logging.critical('Программа завершает работу')
        sys.exit()
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    message = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                if message != (message := parse_status(response['homeworks'][0])):
                    send_message(bot, message)
        except Exception as error:
            logging.error(f'Произошла ошибка: {error}')
            if message != (message := f'При работе возникли ошибки: {error}'):
                send_message(bot, message)
        finally:
            logging.debug(f'Старая дата запроса {timestamp}')
            timestamp = response.get('current_date') or timestamp
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
