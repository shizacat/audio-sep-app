# Экспорт разделителя в ONNX

Отдельная подзадача. Этот каталог не входит в приложение и не использует его `.venv`.

Окружение — уже существующий клон AudioSplit рядом с этим репозиторием: `../AudioSplit/.venv`. Позже тот же путь будет у `git clone`. Сейчас клон заново не скачивается.

Два скрипта:

- `export_separator.py` — сеть разделения ResUNet30, один фрагмент 5 секунд, 32 кГц. На вход волна и вектор условия, на выход волна. Файл: `local/separator.onnx`.
- `export_clap.py` — текстовая ветка CLAP. На вход токены RoBERTa длиной 512 и маска внимания, на выход нормализованный вектор условия. Токенайзер в файл не входит. Файл: `local/clap_text.onnx`.

Готовые файлы читает библиотека `audiosep_app.infer.OnnxSeparator`. Окно вызывает её через адаптер. У библиотеки нет командной строки.

Из корня AudioSepApp:

```shell
../AudioSplit/.venv/bin/python -m pip install -r script/requirements.txt
../AudioSplit/.venv/bin/python script/export_separator.py
../AudioSplit/.venv/bin/python script/export_clap.py
```

Файлы моделей в git не коммитятся. Чекпоинты читаются из `../AudioSplit/AudioSep/checkpoint/`.
