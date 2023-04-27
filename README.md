# api_yamdb

![example workflow](https://github.com/Aleksey-shipkov/yamdb_final/actions/workflows/yamdb_workflow.yml/badge.svg)

### Проект HomeWork_bot

Проект написан с использованием Python и библиотеки Python-telegram-bot.
Проект телеграм-бота позволяет получать уведомления об изменении статуса ревью домашней работы на курсе Яндекс Практикума.
Ведется лог работы программы.
Получение информации происходит путем обращения  API Яндекс Практикума через эндпоинт 'https://practicum.yandex.ru/api/user_api/homework_statuses/',
с интервалом в 10 минут.


## Как развернуть проект

Системные требования:

- Python==3.7.9

1. Создать в корневой директории проекта файл .env

#Указать в файле 'PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID'

>PRACTICUM_TOKEN = 

>TELEGRAM_TOKEN = 

>TELEGRAM_CHAT_ID = 

2. Установить виртуальное окружение

> python -m venv venv

3. Активировать виртуальное окружение

> source venv/scripts/activate

4. Обновить pip

> python -m pip install --upgrade pip

5. Установить зависимости

> pip install -r requirements.txt
