# AudioSep Application

Настольное приложение на Python и Qt: открывает запись и отделяет звук по текстовому описанию. Разделение делает [AudioSep](https://github.com/Audio-AGI/AudioSep). Код, зависимости и окружение приложения находятся в этом репозитории.

## Стек

Python 3.12, Qt 6 через PySide6. Зависимости ставит uv в `.venv`. PyInstaller собирает готовый пакет с Qt 6 отдельно для Linux, macOS и Windows.

## Документы

- [Требования к разработке](docs/development.md)
- [Changelog](CHANGELOG.md)
