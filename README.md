https://habr.com/ru/post/651241/

## Индекс чистой стоимости фонда Тинькофф NASDAQ

1. Для работы индекса необходимо добавить свой токен(ы) от тиньков api в файл `token.txt`, который находится в папке `microservice`

2. Если добавлен только один токен, то необходимо поменять интервал ожидания в файле `index.js`, который находится в папке `html` (инструкция есть в конце этого файла в виде комментов). Примечание: больше двух токенов не требуется, т.к. согласно [ограничениям на количество запросов](https://tinkoff.github.io/invest-openapi/rest/) это и будет максимум. Если будет много ошибок, то можно также поиграть с параметром этого файла по чуть-чуть увеличивая интервал.

---

Системные требования: docker, браузер

Запуск микросервиса: `docker-compose up --build` в корневой дирректории

После запуска микросервиса открыть файл `index.html` в браузере, файл находится в папке `html` 

