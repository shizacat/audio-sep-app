# Экспорт разделителя в ONNX

Отдельная подзадача. Этот каталог не входит в приложение и не использует его `.venv`.

Окружение — уже существующий клон AudioSplit рядом с этим репозиторием: `../AudioSplit/.venv`. Позже тот же путь будет у `git clone`. Сейчас клон заново не скачивается.

Скрипт экспортирует сеть разделения ResUNet30: один фрагмент 5 секунд, 32 кГц. На вход волна и вектор условия, на выход волна. Текстовый кодировщик CLAP сюда не входит.

Из корня AudioSepApp:

```shell
../AudioSplit/.venv/bin/python -m pip install -r script/requirements.txt
../AudioSplit/.venv/bin/python script/export_separator.py
```

Файл модели пишется в `local/separator.onnx` и в git не коммитится. Чекпоинт читается из `../AudioSplit/AudioSep/checkpoint/`.
