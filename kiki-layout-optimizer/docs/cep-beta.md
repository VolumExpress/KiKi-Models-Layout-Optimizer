> **Архивная инструкция для CEP v0.4.3.** Актуальная v0.7.2 использует единую CEP-панель и фоновый Python без внешнего GUI. **Не следуйте описанному ниже COM/Tk workflow для современной версии.** См. [рабочий цикл](gui-workflow.md), [совместимость](compatibility.md) и [установку](ru/INSTALL.md).

> **Актуальная версия:** для v0.5.2 используйте [unified-interface-v0.5.2.md](unified-interface-v0.5.2.md). Этот файл описывает старую архитектуру с отдельным Python-окном.

> **v0.5.1:** CEP дополнена выбором эмблем по клику в Illustrator и настройкой фиксации/поворотов. Для этой функции повторите экспорт новой версией, затем выбирайте отдельные объекты без повторного экспорта. Подробности: [visual-selection-v0.5.1.md](visual-selection-v0.5.1.md).

# KiKi CEP Beta — альтернатива Windows COM для Illustrator 30.x

## Назначение

Экспериментальная *панель внутри Illustrator* для экспорта и применения
существующими JSX (`illustrator/export_selection.jsx`, `illustrator/apply_layout.jsx`).
Отдельный Python/Tk GUI по-прежнему выполняет расчёт и показывает прогресс.
Нет Windows COM / AppleScript для кнопок экспорта и применения из CEP.
Основной оптимизатор, JSON-протокол и исходные векторы не меняются.

**Важно: работа CEP-панели на вашей конкретной Illustrator 30.6.0.109 ещё не
подтверждена**. Illustrator может не показывать меню Legacy Extensions в
отдельных конфигурациях. Это НЕ исправление уже имеющейся Tk-кнопки экспорта
(COM) — пользуйтесь кнопками именно из CEP-панели, если она появилась.

## Windows: установка без терминала

1. Распакуйте проект v0.4.3 в постоянную папку без переименования и переноса
   впоследствии (CEP содержит ссылку на эту папку).
2. Один раз запустите `install_windows.bat`, затем `install_cep_windows.bat`.
3. Подтвердите `Y` для режима разработки, только если согласны включить
   **неподписанные локальные расширения** для своего профиля Windows.
4. Полностью перезапустите Illustrator 30.6.
5. В меню **Window / Окно → Extensions (Legacy) / Расширения (устаревшие)**
   найдите `KiKi Layout Optimizer (Beta)`.
6. В CEP-панели: «Экспорт выделения» → «Настройки и расчёт» (открывает
   существующее окно Python) → после SVG-проверки «Применить раскладку».

Установка копирует файлы в `%APPDATA%\Adobe\CEP\extensions\com.kikimodels.layoutoptimizer`.
Данные документа остаются в `<папка проекта>/workspace/<имя документа>`.

Если панель не появилась:
- посмотрите, есть ли в Illustrator само меню `Extensions (Legacy)`;
- проверьте `%APPDATA%\Adobe\CEP\extensions\com.kikimodels.layoutoptimizer\config.js`;
- проверьте `HKEY_CURRENT_USER\Software\Adobe\CSXS.11` и `.12`:
  `PlayerDebugMode` — строка `1`;
- не пытайтесь вызвать из Tk кнопки COM по кругу: выполните экспорт и применение
  через **File → Scripts → Other Script**, как в v0.3.

## macOS

`install_macos.command` → `install_cep_macos.command` (право на запуск может
потребоваться дать через Finder). Папка CEP:
`~/Library/Application Support/Adobe/CEP/extensions/com.kikimodels.layoutoptimizer`.
Настройки unsigned developer mode — `com.adobe.CSXS.11/12 PlayerDebugMode`.
CEP на macOS, особенно Apple Silicon, требует отдельного испытания.

## Диагностика / контракт

- CEP UI вызывает `kikiCepAction(action, projectRoot, nonce)` через
  `window.__adobe_cep__.evalScript`, без COM.
- `host.jsx` вызывает исходный JSX, проверяет receipt с уникальным nonce и
  возвращает `{"status":"ok|error|cancelled", ...}`.
- `File.execute()` только открывает **существующий** GUI для расчёта;
  никакой исполняемый путь из пользовательского JSON не интерпретируется.
- В CEP-панели нет прав на произвольный доступ к сети и Node.js не включён.
- Получив ошибку `CEP bridge unavailable`, копируйте её текст и скриншот.
- Если потребовалось переименовать/переместить папку проекта, ещё раз
  запустите установщик CEP для обновления абсолютного пути.

## Долгосрочная миграция UXP

Панель (`cep/.../panel.js`) содержит только представление и вызовы адаптера.
JSX остаётся авторитетным для геометрии; Python engine отвечает за расчёт.
После выхода Illustrator UXP API новый UI/адаптер заменит CEP-мост, без
необходимости переписывать геометрию и JSON-протокол. Миграция не равна
копированию CEP-манифеста: у UXP другие права доступа и API.

Официальные материалы:
- https://helpx.adobe.com/creative-cloud/apps/integration-with-other-apps/manage-plugins/cep-uxp-plugin-transition.html
- https://developer.adobe.com/uxp/migration-center/
- https://github.com/Adobe-CEP/CEP-Resources
