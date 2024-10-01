import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

from exceptions import (
    SendError, RequestError, ParseError
)



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


def check_tokens():
    """Проверяет наличие данных в окружении."""
    try:
        assert (
            all([PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN]) is True
        )
    except Exception as error:
        logging.critical(
            f'Ошибка при чтении токенов. {error}'
            'Программа была остановлена'
        )
        sys.exit()


def send_message(bot, message):
    """Отправляет сообщение от бота."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Бот отправил сообщение: {message}')
    except Exception as error:
        raise SendError from error


def get_api_answer(timestamp):
    """Получает ответ от сервера."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        assert response.status_code == HTTPStatus.OK
    except Exception as error:
        raise RequestError(response.status_code, error) from error
    else:
        return response.json()


def check_response(response):
    """Проверяет ответ от сервера."""
    try:
        assert type(response.get('homeworks')) == list
    except Exception as error:
        raise TypeError from error
    else:
        if response.get('homeworks') != []:
            return True
        logging.debug('Статус работы не изменился')


def parse_status(homework):
    """Возвращает статус работы."""
    try:
        status = homework['status']
        verdict = HOMEWORK_VERDICTS[status]
        homework_name = homework['homework_name']
    except Exception as error:
        raise ParseError from error
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    check_tokens()

    while True:
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                message = parse_status(response['homeworks'][0])
                send_message(bot, message)
        except RequestError as error:
            logging.error(f'Страница недоступна. {error}')
        except SendError as error:
            logging.error(f'При отправке ответа возникла ошибка. {error}')
        except TypeError as error:
            logging.error(f'Некорректный ответ от сервера. {error}')
        except ParseError as error:
            logging.error(error)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        filemode='w',
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )

    logger = logging.getLogger(__name__)
    # Устанавливаем уровень, с которого логи будут сохраняться в файл:
    logger.setLevel(logging.INFO)
    # Указываем обработчик логов:
    handler = RotatingFileHandler('my_logger.log', maxBytes=50000000, backupCount=5)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    # Применяем его к хендлеру:
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    main()
