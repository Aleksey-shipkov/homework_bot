import os

import time

import requests

import logging

from logging import StreamHandler
from dotenv import load_dotenv

from telegram import Bot
import telegram


load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s'
)
logger = logging.getLogger(__name__)

logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=None)

handler.setFormatter(formatter)

logger.addHandler(handler)


def send_message(bot, message):
    """Высылает сообщение через телеграм-бот."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Бот выслал сообщение {message}')
    except telegram.TelegramError as error:
        logger.error(error, exc_info=True)
        raise telegram.TelegramError(f'Произошла{error}')


def get_api_answer(current_timestamp):
    """Функция получает ответ от API."""
    timestamp = current_timestamp
    payload = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != 200:
            logger.error(
                f'Не удалось получить доступ к эндпоинту {ENDPOINT}.'
                f'Ошибка: {response.status_code}')
            raise requests.exceptions.HTTPError(
                f'Не удалось получить доступ к эндпоинту {ENDPOINT}.'
                f'Ошибка: {response.status_code}')
        return response.json()
    except Exception as error:
        logger.error(f'Произошла{error}', exc_info=True)
        raise Exception(f'Произошла{error}')


def check_response(response):
    """Функция проверяет ответ от API на соответствие критериям."""
    if not isinstance(response, dict):
        logger.error('Произошла ошибка. Ответ не является словарем')
        raise TypeError('Произошла ошибка. Ответ не является словарем')
    if not isinstance(response['homeworks'], list):
        logger.error('Произошла ошибка. Ответ не является списком')
        raise TypeError('Произошла ошибка. Ответ не является списком')
    if response['homeworks'] == []:
        logger.debug('Новые статусы отсутствуют')
    try:
        homework = response.get('homeworks')
    except KeyError as error:
        logger.error(f'{error}: невозможно получить необходимое содержимое')
        raise KeyError(f'{error}: невозможно получить необходимое содержимое')
    except IndexError as error:
        logger.error(f'{error} В ответе нет объекта "homeworks"')
        raise IndexError((f'{error}Неизвестный тип объекта {type(response)}.'
                          f'Объект не является ответом типа "список"'))
    except Exception as error:
        logger.error(f'Произошла{error}', exc_info=True)
        raise Exception(f'Произошла{error}')
    return homework


def parse_status(homework):
    """Функция получает статус домашней работы."""
    try:
        homework_name = homework.get('homework_name')
        homework_status = homework.get('status')
        if homework_status not in HOMEWORK_STATUSES:
            logger.error(
                'Ошибка: Незадокументированный статус домашней работы')
            raise KeyError(
                'Ошибка: Незадокументированный статус домашней работы')
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except KeyError as error:
        logger.error(f'{error}: невозможно получить необходимое содержимое')
        raise KeyError(f'{error}: невозможно получить необходимое содержимое')


def check_tokens():
    """Проверка на наличие всех необходимых элементов внешнего окружения."""
    token_list = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

    for token in token_list:
        if globals()[token] is None or globals()[token] == '':
            logger.critical('Отсутствует обязательный элемент окружения!')
            return False
    return True


def main():
    """Основная логика работы бота."""
    message_list = []

    if not check_tokens():
        raise SystemExit

    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    check_tokens()
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework)
            if message in message_list or message == []:
                logger.debug('Новые статусы отсутствуют')
            else:
                message_list.append(message)
                send_message(bot, message)
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message not in message_list:
                message_list.append(message)
                bot = Bot(token=TELEGRAM_TOKEN)
                send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
