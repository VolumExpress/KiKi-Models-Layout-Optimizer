# Установка, обновление и удаление KiKi Models

## Публичный релиз

Артефакты независимы: ZIP исходников, `windows-portable.zip`, `macos-portable.zip`, Windows `Setup.exe` (если собран CI). Проверяйте дату сборки, контрольные суммы `SHA256SUMS.json` и соответствие ОС. Архив исходников не обязан содержать готовый бинарник.

### Windows, без Python

1. Распаковать `windows-portable.zip` в отдельный каталог.
2. Запустить `installers/windows/install.cmd`. Сценарий вызывает читаемый `install.ps1`; см. его до выполнения.
3. Если доверяете неподписанной бета-панели, отдельно разрешить CEP PlayerDebugMode для текущего пользователя. Это настройка безопасности Adobe, поэтому установщик **спрашивает согласие**.
4. После завершения перезапустить Illustrator. Проект установлен в `%LOCALAPPDATA%\KiKiModels\LayoutOptimizer`, CEP — `%APPDATA%\Adobe\CEP\extensions\com.kikimodels.layoutoptimizer`.
5. Если CEP не виден, проверить версию Illustrator, наличие `config.js`, меню Extensions (Legacy), а затем вручную выполнить `install.ps1 -EnableUnsignedDev` *только при согласии*.

Ручная установка из портативного пакета:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\installers\windows\install.ps1
# Только при осознанном согласии:
powershell -NoProfile -ExecutionPolicy Bypass -File .\installers\windows\install.ps1 -EnableUnsignedDev
```

### macOS, без Python

Запуск `installers/macos/install.command`. Пакет **должен** быть собран на macOS; macOS Gatekeeper может потребовать явного разрешения для неподписанного пакета. Целевая папка: `~/Library/Application Support/KiKiModels/LayoutOptimizer`. Бета не подписана и не прошла нативную проверку на macOS.

## Обновление

Закрыть Illustrator, скачать новый пакет нужной ОС и повторно выполнить установщик. `workspace` и `presets` не удаляются. Перед обновлением сохранить резервную копию `workspace` и `.ai`. Не копировать предыдущий исполняемый файл на другую ОС.

## Удаление

Windows: закрыть Illustrator, удалить `%APPDATA%\Adobe\CEP\extensions\com.kikimodels.layoutoptimizer`; каталог `%LOCALAPPDATA%\KiKiModels\LayoutOptimizer` удалить вручную **после** сохранения `workspace` и `presets`. Не удалять их автоматически. Для выключения тестового CEP-режима удалить исключительно созданные значения `PlayerDebugMode` в `HKCU\Software\Adobe\CSXS.11/12` только если они больше не нужны другим расширениям.

macOS: удалить папку CEP и приложение из `~/Library/Application Support/`; предварительно сохранить нужные файлы. При необходимости вернуть настройку CEP по умолчанию командой `defaults delete com.adobe.CSXS.11 PlayerDebugMode` и `defaults delete com.adobe.CSXS.12 PlayerDebugMode`, только если её не используют другие расширения.

## Диагностика

- «Нет панели»: меню Extensions (Legacy), настройки неподписанного CEP, полная перезагрузка Illustrator.
- «Нет runtime»: вы открыли архив исходников вместо платформенного пакета; установите из исходников с Python или скачайте релиз с `runtime/kiki-worker(.exe)`.
- Ошибка после изменения макета: повторный экспорт, проверка `history/` и `export_audit.json`, особенно UUID и ограничений.
- «Нет результата»: смотрите журнал CEP и папку документа; не применяйте `best_so_far.json` или файлы из `alternatives/`.
- Mac/Windows кросс-компиляция не поддерживается: собирать исполняемый файл на целевой ОС.


## Контроль целостности и удаление в RC2

Портативный пакет включает `SHA256SUMS.txt` и `SHA256SUMS.json`. Скрипты установки проверяют SHA-256 **до** копирования. Это выявляет повреждения/случайные изменения, но не заменяет криптографическую подпись издателя. Сверяйте SHA-256 самого архива с опубликованным в GitHub Release.

Windows: `installers\windows\uninstall.cmd` (или `uninstall.ps1`). macOS: `installers/macos/uninstall.command`. По умолчанию удаляются исполняемые файлы и CEP-панель только если она указывает на эту установку; `workspace` и `presets` сохраняются. Для удаления пользовательских данных нужен отдельный явный параметр, описанный в исходном скрипте. Режим разработчика Adobe при удалении не отключается автоматически (мог использоваться другими расширениями).

**Испытания платформ:** сборки Windows/macOS должны проходить `smoke_runtime.py`, проверку контрольных сумм и нативный ручной тест с Illustrator. До этого установщики обозначаются как неподписанные кандидаты, а не проверенный стабильный релиз.

### Уведомления сторонних компонентов

После установки файлы `THIRD_PARTY_NOTICES.md` и `third_party_licenses/` доступны в каталоге KiKi. Инсталлятор проверяет контрольные суммы перед копированием, а проверка сборки отклоняет отсутствие лицензионного пакета. См. отдельное предупреждение о GEOS/LGPL перед публичным распространением.
