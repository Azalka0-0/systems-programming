
import csv
import json
import shutil

from pathlib import Path


# Обязательные поля документа
REQUIRED_FIELDS = [
    "document_id",
    "order_id",
    "document_type",
    "date",
    "customer",
    "amount",
]


def validate_document(data):
    """Проверяет наличие обязательных полей."""

    if not isinstance(data, dict):
        return ["Документ должен быть JSON-объектом"]

    errors = []

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Отсутствует поле: {field}")

    return errors


def load_document(path):
    """Читает JSON-файл и возвращает данные или ошибку."""

    try:
        text = Path(path).read_text(encoding="utf-8")
        data = json.loads(text)
        return data, None

    except json.JSONDecodeError:
        return None, "Некорректный JSON"

    except UnicodeDecodeError:
        return None, "Ошибка кодировки файла"

    except OSError as error:
        return None, f"Ошибка чтения файла: {error}"


def find_duplicate_ids(incoming_dir):
    """Находит все повторяющиеся document_id."""

    documents = {}

    for path in Path(incoming_dir).rglob("*.json"):
        data, error = load_document(path)

        if error or not isinstance(data, dict):
            continue

        document_id = data.get("document_id")

        if document_id:
            documents.setdefault(document_id, []).append(path)

    duplicates = {
        document_id
        for document_id, paths in documents.items()
        if len(paths) > 1
    }

    return duplicates


def get_unique_path(path):
    """Возвращает свободный путь, если имя уже занято."""

    if not path.exists():
        return path

    counter = 1

    while True:
        new_path = path.with_name(
            f"{path.stem}_{counter}{path.suffix}"
        )

        if not new_path.exists():
            return new_path

        counter += 1


def copy_document(source, destination):
    """Копирует файл без повторов и перезаписи других документов."""

    source = Path(source)
    destination = Path(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():

        # При повторном запуске одинаковый файл не копируем
        if destination.read_bytes() == source.read_bytes():
            return destination

        # Если содержимое отличается, создаём отдельное имя
        parent_name = source.parent.name or "document"

        candidate = destination.with_name(
            f"{destination.stem}__{parent_name}{destination.suffix}"
        )

        counter = 1

        while candidate.exists():

            if candidate.read_bytes() == source.read_bytes():
                return candidate

            candidate = destination.with_name(
                f"{destination.stem}__{parent_name}_{counter}"
                f"{destination.suffix}"
            )

            counter += 1

        destination = candidate

    shutil.copy2(source, destination)

    return destination


def process_document(source, duplicate_ids):
    """Проверяет документ и копирует его в нужную папку."""

    data, error = load_document(source)

    # Проверяем повторяющийся ID
    if not error and isinstance(data, dict):
        document_id = data.get("document_id")

        if document_id in duplicate_ids:
            destination = Path("output/quarantine") / source.name
            actual_path = copy_document(source, destination)

            return (
                "problem",
                actual_path,
                f"Повторяющийся ID: {document_id}",
            )

    # Если файл невозможно прочитать
    if error:
        destination = Path("output/quarantine") / source.name
        actual_path = copy_document(source, destination)

        return "problem", actual_path, error

    # Проверяем обязательные поля
    errors = validate_document(data)

    if errors:
        destination = Path("output/quarantine") / source.name
        actual_path = copy_document(source, destination)

        return "problem", actual_path, "; ".join(errors)

    # Получаем дату и тип документа
    date = str(data["date"])
    document_type = str(data["document_type"])

    # Формируем путь YYYY-MM/тип
    month = date[:7]

    destination = (
        Path("output/sorted")
        / month
        / document_type
        / source.name
    )

    actual_path = copy_document(source, destination)

    return "success", actual_path, ""


def run_processing():
    """Обрабатывает все документы и записывает журнал."""

    incoming_dir = Path("data/incoming")

    if not incoming_dir.exists():
        print("Папка data/incoming не найдена.")
        return

    duplicate_ids = find_duplicate_ids(incoming_dir)

    print("Повторяющиеся ID:", sorted(duplicate_ids))

    total = 0
    successful = 0
    problematic = 0

    log_rows = []

    for source in sorted(incoming_dir.rglob("*.json")):
        total += 1

        status, destination, reason = process_document(
            source,
            duplicate_ids,
        )

        if status == "success":
            successful += 1
        else:
            problematic += 1

        log_rows.append({
            "source": str(source),
            "destination": str(destination),
            "status": status,
            "reason": reason,
        })

    # Записываем CSV-журнал
    log_path = Path("output/processing_log.csv")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "source",
                "destination",
                "status",
                "reason",
            ],
        )

        writer.writeheader()
        writer.writerows(log_rows)

    # Выводим итоговую статистику
    print("\n========== РЕЗУЛЬТАТ ==========")
    print(f"Всего документов: {total}")
    print(f"Успешных: {successful}")
    print(f"Проблемных: {problematic}")
    print(f"Журнал: {log_path}")


if __name__ == "__main__":
    run_processing()
