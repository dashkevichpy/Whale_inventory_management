import pandas as pd


def update_gsheet(
    df: pd.DataFrame,
    worksheet,
    start_cell: tuple,
    end_cell: tuple,
) -> None:
    """Записывает DataFrame в заданный лист Google Sheets.

    Args:
        df: Таблица для отправки.
        worksheet: Объект листа из pygsheets.
        start_cell: Координаты левой верхней ячейки.
        end_cell: Координаты правой нижней ячейки, очищаемой перед записью.
    """

    worksheet.clear(start=start_cell, end=end_cell)
    if isinstance(df, pd.Series):
        df = pd.DataFrame(df)

    float_columns = df.select_dtypes(include=["float64"])
    for col in float_columns.columns:
        df[col] = df[col].astype("int64")

    worksheet.set_dataframe(df=df, start=start_cell, copy_head=False)