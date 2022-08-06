from http import HTTPStatus
from typing import Dict, List
import os
import time
import requests
import logging
from logging import StreamHandler
from dotenv import load_dotenv
from json.decoder import JSONDecodeError

from telegram import Bot, TelegramError


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

NOT_DICT = 'Произошла ошибка. Ответ не является словарем.'
NOT_EXIST = 'Не возможно получить необходимое содержимое.'
NOT_LIST = 'Произошла ошибка. Ответ не является списком.'
NOT_HOMEWORK_NAME_KEY = 'Ошибка: отсутствует ключ "homework_name".'
NOT_STATUS_KEY = 'Ошибка: отсутствует ключ "status".'
NOT_HOMEWORK_STATUS = 'Ошибка: Незадокументированный статус домашней работы'
NOT_ENDPOINT = f'Не удалось получить доступ к эндпоинту {ENDPOINT}.'
NOT_JSON = 'Не удалось не удалось обработать json.'
EMPTY_LIST = 'Список домашних работ пуст.'


def init_logger() -> logging.Logger:
    """Создает логгер."""
    formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = StreamHandler(stream=None)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = init_logger()


def send_message(bot: Bot, message: str) -> None:
    """Высылает сообщение через телеграм-бот."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Бот выслал сообщение {message}')
    except TelegramError as error:
        logger.error(error, exc_info=True)
        raise TelegramError(f'Произошла{error}')


def get_api_answer(current_timestamp: int) -> Dict[str, list]:
    """Функция получает ответ от API."""
    timestamp = current_timestamp
    payload = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            logger.error(
                f'{NOT_ENDPOINT}'
                f'Ошибка: {response.status_code}')
            raise requests.exceptions.HTTPError(
                f'{NOT_ENDPOINT}'
                f'Ошибка: {response.status_code}')
    except Exception as error:
        logger.error(f'Произошла{error}', exc_info=True)
        raise Exception(f'Произошла{error}')
    try:
        response = response.json()
        return response
    except JSONDecodeError as error:
        logger.error(f'{error}: {NOT_JSON}')
        raise JSONDecodeError(NOT_JSON)


def check_response(response: Dict[str, list]) -> List[str]:
    """Функция проверяет ответ от API на соответствие критериям."""
    if not isinstance(response, dict):
        logger.error(NOT_DICT)
        raise TypeError(NOT_DICT)
    try:
        homeworks = response['homeworks']
    except KeyError:
        logger.error(NOT_EXIST)
        raise KeyError(NOT_EXIST)
    if not isinstance(response['homeworks'], list):
        logger.error(NOT_LIST)
        raise TypeError(NOT_LIST)
    try:
        homeworks[0]
    except IndexError:
        logger.error(EMPTY_LIST)
        raise IndexError(EMPTY_LIST)
    return homeworks


def parse_status(homework: List[str]) -> str:
    """Функция получает статус домашней работы."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logger.error(NOT_HOMEWORK_NAME_KEY)
        raise KeyError(NOT_HOMEWORK_NAME_KEY)
    try:
        homework_status = homework['status']
    except KeyError:
        logger.error(NOT_STATUS_KEY)
        raise KeyError(NOT_STATUS_KEY)
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(NOT_HOMEWORK_STATUS)
        raise KeyError(NOT_HOMEWORK_STATUS)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверка на наличие всех необходимых элементов внешнего окружения."""
    if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logger.critical('Отсутствует обязательный элемент окружения!')
        return False
    return True


def main() -> None:
    """Основная логика работы бота."""
    message_list = []
    if not check_tokens():
        raise SystemExit
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    print(type(current_timestamp))
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            homework = homeworks[0]
            message = parse_status(homework)
            if message in message_list or message == []:
                logger.debug('Новые статусы отсутствуют')
            else:
                message_list.append(message)
                send_message(bot, message)
            current_timestamp = int(time.time())
        except Exception as error:
            logger.error(f'{error}')
            message = f'Сбой в работе программы: {error}'
            if message not in message_list:
                message_list.append(message)
                send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
