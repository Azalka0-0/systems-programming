# Ядро агента (C)

Ядро собирается в динамическую библиотеку: `sentry_core.dll` в Windows, `libsentry_core.dylib` в macOS,
`libsentry_core.so` в Linux. Первая функция появляется на паре 2. Какие файлы и в какой главе появляются здесь — в [`agent/README.md`](../README.md).

| Файл | Что в нём |
|---|---|
| core.h | структура core_info и объявление core_get_info |
| core_info.c | функция core_get_info |
| show_info.c | проверка функции |

