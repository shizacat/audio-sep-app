# Changelog

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/).
Версии нумеруются по [SemVer](https://semver.org/lang/ru/).

## [Unreleased]

### Изменено

- Минимальная версия Python — 3.12.
- Сборка пакета идёт через Hatchling.
- Версия пакета читается из `__version__` в `src/audiosep_app/__init__.py`.
- Образец конфигурации лежит в `contribute/config.example.toml`.
- Поддерживаемые форматы аудио заданы одним требованием; в остальных местах — «аудиофайл».

### Добавлено

- Каркас репозитория: пакет `src/audiosep_app`, тесты, образец конфигурации.
- Требования к разработке в `docs/development.md`.
- Правила для агентов в `.cursor/rules/`, каждое правило в своём файле.
- Обязательный changelog для дальнейших изменений.
