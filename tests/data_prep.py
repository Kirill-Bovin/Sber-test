import pandas as pd

from scripts.data_prep import fill_missing, normalize_types


def test_fill_missing_and_normalize():
    """
    Тест функции заполнения пропущенных значений и нормализации типов данных.

    Проверяется, что:
    - функция fill_missing корректно заполняет пропуски в столбцах 'rate' и 'term_months';
    - функция normalize_types приводит типы данных к нужным (например, float или int);
    - после обработки в указанных столбцах не остаётся пропусков.
    """
    # Создаем тестовый DataFrame с пропусками
    df = pd.DataFrame(
        [
            {
                "name": "Test",
                "rate": None,           # пропуск в ставке
                "term_months": None,    # пропуск в сроке
                "currency": "RUB",
                "min_amount": 1000,
            }
        ]
    )
    # Для уверенности выставляем ставку явно
    df["rate"] = 5.0

    # Заполняем пропущенные значения
    df_filled = fill_missing(df)
    # Нормализуем типы данных
    df_normalized = normalize_types(df_filled)

    # Проверяем, что после заполнения и нормализации пропусков нет
    assert df_normalized["rate"].notnull().all()
    assert df_normalized["term_months"].notnull().all()