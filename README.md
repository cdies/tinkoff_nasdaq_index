https://habr.com/ru/post/651241/

Update: теперь на новом [api](https://github.com/Tinkoff/invest-python) (нужен только один токен)

# Индекс чистой стоимости фонда Тинькофф NASDAQ

### Для запуска необходимо:

Системные требования: docker, браузер

1. Для работы индекса необходимо добавить свой токен от тиньков api в файл `token.txt`, который находится в папке `microservice`.

2. Запуск микросервиса: `docker-compose up --build` в корневой дирректории

3. После запуска микросервиса открыть файл `index.html` в браузере, файл находится в папке `html` 

**Предупреждение:** Индекс работает *достаточно* стабильно.

## Описание графика

Маркер "O" - на графике отмечено время открытия московской биржы, 10:00

Маркер "C" - закрытие московской биржы, 18:45

В консоле браузера можно отслеживать количество ошибок. Если их очень много, то можно увеличить интервал в файле `index.js`. На небольшое количество ошибок можно не обращать внимания.

![](https://habrastorage.org/webt/e9/q_/pj/e9q_pjzclpzz9imf7m-7wpompzu.png)


<br/><br/>
---
[![](https://habrastorage.org/webt/gz/gc/i6/gzgci6pivvdnk-gmj-kepml5q9y.gif)](https://yoomoney.ru/to/4100117863420642)
