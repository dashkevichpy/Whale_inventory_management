import pandas as pd


# def update_gsheet(df: pd.DataFrame, gs_token: str, ws_name: str, start_cell: tuple, end_cell: tuple, addrr_time_cell: tuple):
#     '''
#     выводим в GS с настройками (откуда начинаем, время обновления)
#     :param df:
#     :param gs_token:
#     :param ws_name:
#     :param cell_start:
#     :param cell_end:
#     :param columns_to_float:
#     :param addrr_time_cell:
#     :return:
#     '''
#     gs = pygsheets.authorize(service_file = LINK_GS_JSON)
#     # gs = pygsheets.authorize(service_file="creds1.json")
#     service_file = LINK_GS_JSON
#     wb = gs.open_by_key(gs_token)
#     ws = wb.worksheet_by_title(ws_name)
#     ws.clear(start=start_cell, end=end_cell)
#
#     if isinstance(df, pd.Series):  # если понадобиться записать столбец
#         df = pd.DataFrame(df)
#
#     float_col = df.select_dtypes(include=['float64'])
#     for col in float_col.columns.values:
#         df[col] = df[col].astype('int64')
#
#     ws.set_dataframe(df=df, start=start_cell, copy_head=False)
#     ws.cell(addrr_time_cell).set_value(
#         datetime.now(tz=pytz.timezone('Asia/Krasnoyarsk')).strftime("%d.%m.%Y %H:%M")
#     )


def update_gsheet(df: pd.DataFrame, ws, start_cell: tuple, end_cell: tuple):
    '''
    выводим в GS с настройками (откуда начинаем, время обновления)
    :param df:
    :param gs_token:
    :param ws_name:
    :param cell_start:
    :param cell_end:
    :param columns_to_float:
    :param addrr_time_cell:
    :return:
    '''
    ws.clear(start=start_cell, end=end_cell)
    if isinstance(df, pd.Series):  # если понадобиться записать столбец
        df = pd.DataFrame(df)

    float_col = df.select_dtypes(include=['float64'])
    for col in float_col.columns.values:
        df[col] = df[col].astype('int64')

    ws.set_dataframe(df=df, start=start_cell, copy_head=False)