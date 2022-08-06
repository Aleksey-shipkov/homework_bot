from http.client import OK
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


def init_logger() -> None:
    """Создает логгер."""
    formatter = logging.Formatter('%(asctime)s, %(levelname)s, %(message)s')
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = StreamHandler(stream=None)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = init_logger()


def send_message(bot, message) -> None:
    """Высылает сообщение через телеграм-бот."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.info(f'Бот выслал сообщение {message}')
    except TelegramError as error:
        logger.error(error, exc_info=True)
        raise TelegramError(f'Произошла{error}')


def get_api_answer(current_timestamp) -> dict:
    """Функция получает ответ от API."""
    timestamp = current_timestamp
    payload = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != OK:
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


def check_response(response) -> list:
    """Функция проверяет ответ от API на соответствие критериям."""
    if not isinstance(response, dict):
        logger.error(NOT_DICT)
        raise TypeError(NOT_DICT)
    if not response['homeworks']:
        logger.error(NOT_EXIST)
        raise KeyError(NOT_EXIST)
    if not isinstance(response['homeworks'], list):
        logger.error(NOT_LIST)
        raise TypeError(NOT_LIST)
    try:
        homeworks = response.get('homeworks')
    except requests.exceptions.RequestException:
        logger.error(NOT_EXIST)
        raise requests.exceptions.RequestException(NOT_EXIST)
    return homeworks


def parse_status(homework) -> str:
    """Функция получает статус домашней работы."""
    if not homework['homework_name']:
        logger.error(NOT_HOMEWORK_NAME_KEY)
        raise KeyError(NOT_HOMEWORK_NAME_KEY)
    homework_name = homework.get('homework_name')
    if not homework['status']:
        logger.error(NOT_STATUS_KEY)
        raise KeyError(NOT_STATUS_KEY)
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_STATUSES:
        logger.error(NOT_HOMEWORK_STATUS)
        raise KeyError(NOT_HOMEWORK_STATUS)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> None:
    """Проверка на наличие всех необходимых элементов внешнего окружения."""
    token_list = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

    if any(
            globals()[token] is None or globals()[token] == ''
            for token in token_list):
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
            message = f'Сбой в работе программы: {error}'
            if message not in message_list:
                message_list.append(message)
                bot = Bot(token=TELEGRAM_TOKEN)
                send_message(bot, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
