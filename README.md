# RAG помощник в телеграмме

## Настройка

1. Заполнить TODO в файле config.env.
   1. Получить креды для GigaChat API на https://developers.sber.ru/studio
   2. Получить токен тг бота после его создания https://telegram.me/BotFather
2. Заполнить прочие нужные настройки в файле config.env при желании.
3. Поместить свою базу знаний вместо текущего файла в папку src/rag_data.

## Установка
```sh
./init.sh
```

## Запуск 
```sh
 ./run.sh
 ```