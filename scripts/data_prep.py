import pandas as pd
from sqlalchemy import create_engine


def load_raw_csv(path: str) -> pd.DataFrame:
    """Загружает исходный CSV-файл с данными о вкладах"""
    return pd.read_csv(path)


def load_raw_db(conn_str: str, table_name: str) -> pd.DataFrame:
    """Загружает данные о вкладах из базы данных через SQLAlchemy"""
    engine = create_engine(conn_str)
    query = f"SELECT * FROM {table_name}"
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
    return df


def clean_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Чистит текстовые поля, убирая неразрывные пробелы и лишние символы"""
    # Замена NBSP на обычный пробел
    df['name'] = df['name'].astype(str).str.replace('\u00A0', ' ', regex=False)
    # Убираем лишние пробелы
    df['name'] = df['name'].str.strip()
    return df


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Удаляет полные дубликаты строк"""
    return df.drop_duplicates().reset_index(drop=True)


def fill_missing(df: pd.DataFrame) -> pd.DataFrame:
    """
    Заполняет пропущенные значения:
      - rate: медианой по названию вклада
      - term_months: модой во всём датасете
      - остальные пропуски удаляет
    """
    df['rate'] = df['rate'].fillna(df.groupby('name')['rate'].transform('median'))
    df['term_months'] = df['term_months'].fillna(df['term_months'].mode()[0])
    df = df.dropna(subset=['currency', 'min_amount'])
    return df


def normalize_types(df: pd.DataFrame) -> pd.DataFrame:
    """Приводит колонки к правильным типам"""
    df['term_months']   = df['term_months'].astype(int)
    df['min_amount']    = df['min_amount'].astype(int)
    df['rate']          = df['rate'].astype(float)
    df['can_replenish'] = df['can_replenish'].map({True: 1, False: 0})
    return df


def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """One-hot кодирование для категориальных признаков"""
    return pd.get_dummies(df, columns=['currency', 'payout_mode'], drop_first=True)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Добавляет новые признаки:
      - risk_level: уровень риска
      - goal_accumulation: индикатор накопительной цели (срок >= 12 месяцев)
    """
    df['risk_level'] = pd.cut(
        df['term_months'],
        bins=[0, 6, 12, 24, df['term_months'].max()],
        labels=['high', 'medium', 'low', 'very_low']
    )
    df['risk_level'] = df['risk_level'].map({'high': 3, 'medium': 2, 'low': 1, 'very_low': 0})
    df['goal_accumulation'] = (df['term_months'] >= 12).astype(int)
    return df


def preprocess_csv(input_path: str) -> pd.DataFrame:
    """Полная цепочка препроцессинга из CSV"""
    df = load_raw_csv(input_path)
    df = clean_strings(df)
    df = drop_duplicates(df)
    df = fill_missing(df)
    df = normalize_types(df)
    df = encode_features(df)
    df = add_features(df)
    return df


def preprocess_db(conn_str: str, table_name: str) -> pd.DataFrame:
    """Полная цепочка препроцессинга из БД"""
    df = load_raw_db(conn_str, table_name)
    df = clean_strings(df)
    df = drop_duplicates(df)
    df = fill_missing(df)
    df = normalize_types(df)
    df = encode_features(df)
    df = add_features(df)
    return df


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Подготовка данных по вкладам из CSV или БД')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--input_csv',  help='Путь к raw CSV')
    group.add_argument('--db_conn',    help='Строка подключения к БД')
    parser.add_argument('--table',      help='Имя таблицы при использовании БД')
    parser.add_argument('--output',     required=True, help='Путь для сохранения очищенного CSV')
    args = parser.parse_args()

    if args.input_csv:
        df_clean = preprocess_csv(args.input_csv)
    else:
        df_clean = preprocess_db(args.db_conn, args.table)

    df_clean.to_csv(args.output, index=False)
    print(f"Сохранено очищенных данных: {args.output}")