import gc
import logging
import os
from datetime import datetime

import numpy as np
import pygsheets
import pytz
from dotenv import load_dotenv

load_dotenv()
GS_BOT_ADMIN_TOKEN = os.getenv("GS_BOT_ADMIN_TOKEN")
GS_BOT_ENTRY_TOKEN = os.getenv("GS_BOT_ENTRY_TOKEN")
LINK_GS_JSON = os.getenv("LINK_GS_JSON")
ERRORS_POSITIONS_SHEET_NAME = os.getenv("ERRORS_POSITIONS_SHEET_NAME")
GS_BOT_STOP_LIST_TOKEN = os.getenv("GS_BOT_STOP_LIST_TOKEN")
GS_AVERAGE_CHECK = os.getenv("GS_AVERAGE_CHECK")
AVERAGE_CHECK_SHEET_NAME = os.getenv("AVERAGE_CHECK_SHEET_NAME")
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Krasnoyarsk")

logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

gs = pygsheets.authorize(service_file=LINK_GS_JSON)


def open_sheet(gs_token: str, ws_name: str) -> pygsheets.worksheet.Worksheet:
    gs = pygsheets.authorize(service_file=LINK_GS_JSON)
    wb = gs.open_by_key(gs_token)
    ws = wb.worksheet_by_title(ws_name)
    return ws


def insert_to_error_krsk_bot(sheet_name: str, entry: list):

    entry_sheet = gs.open_by_key(GS_BOT_ENTRY_TOKEN)
    worksheet = entry_sheet.worksheet_by_title(sheet_name)
    worksheet.refresh()
    row_to_write = worksheet.cell('A1').value
    worksheet.insert_rows(int(row_to_write), values=entry, inherit=True)
    del worksheet
    gc.collect()



def get_column_values(sheet_name, column_num: int, start: int, finish: int):
    """
    из столбца получаем 1 мерный массив значений в ячейках

    :param sheet_name: c какого листа берем значения
    :param column: с какой колонки в листе берем
    :param start: с какой строки начать (обрезаем массив)
    :param finish: на какой строке закончить (обрезаем массив)
    :return: 1 мерный массив
    """
    admin_sheet = gs.open_by_key(GS_BOT_ADMIN_TOKEN)
    worksheet = admin_sheet.worksheet_by_title(sheet_name)
    cells = worksheet.get_col(column_num, include_tailing_empty=False)

    if start == 0 and finish == 0:
        return cells

    if start == finish and (finish <= len(cells) and start > 0):
        return cells[start - 1]

    if 0 < start <= len(cells) and finish == 0:
        return cells[start - 1:len(cells)]

    if start > 0 and finish > 0 and (finish, start <= len(cells)) and start < finish:
        return cells[start - 1:finish]
    del worksheet
    gc.collect()


def get_error_postions_from_gs():
    """
    название позиций из строки в admin
    :return: массив должностей
    """
    admin_sheet = gs.open_by_key(GS_BOT_ADMIN_TOKEN)
    ws = admin_sheet.worksheet_by_title(ERRORS_POSITIONS_SHEET_NAME)
    cells = ws.get_row(1, include_tailing_empty=False)
    cells.pop(0)
    del ws
    gc.collect()
    return cells


def get_list_of_errors_by_positions(position):
    """
    возращает список ошибок для позиции + chat_id кому слать сообщения
    :param position: какую позицию выбрали на клавиатуре
    :return:
    """
    admin_sheet = gs.open_by_key(GS_BOT_ADMIN_TOKEN)
    p = 0
    ws = admin_sheet.worksheet_by_title(ERRORS_POSITIONS_SHEET_NAME)
    position_list = ws.get_row(1, include_tailing_empty=False)
    for p in range(len(position_list)):
        if position_list[p] == position:
            break
    list_of_errors_by_positions = ws.get_col(p + 1, include_tailing_empty=False)
    list_of_errors_by_positions.pop(0)
    del ws
    gc.collect()
    return list_of_errors_by_positions


def insert_entry_breakages_gs(
    id_user, which_whale, what_broken, critical, comment, sheet
) -> None:
    """Write breakage entry to Google Sheet."""

    krsk_now = datetime.now(tz=pytz.timezone(TIME_ZONE))
    entry_sheet = gs.open_by_key(GS_BOT_ENTRY_TOKEN)
    worksheet = entry_sheet.worksheet_by_title(sheet)
    worksheet.insert_rows(worksheet.rows, values=[krsk_now.strftime("%d-%m-%Y %H:%M"),
                                                  id_user,
                                                  which_whale,
                                                  what_broken,
                                                  critical,
                                                  comment],
                          inherit=True)
    del worksheet
    gc.collect()


def insert_entry_errors_gs(
    id_user, which_whale, when, error_type, comment, sheet
) -> None:
    """Write error entry to Google Sheet."""

    krsk_now = datetime.now(tz=pytz.timezone(TIME_ZONE))
    entry_sheet = gs.open_by_key(GS_BOT_ENTRY_TOKEN)
    worksheet = entry_sheet.worksheet_by_title(sheet)
    worksheet.refresh()
    row_to_write = worksheet.cell('A1').value
    worksheet.insert_rows(int(row_to_write), values=[krsk_now.strftime("%d-%m-%Y %H:%M"),
                                                  id_user,
                                                  which_whale,
                                                  when,
                                                  error_type,
                                                  comment], inherit=True)
    del worksheet
    gc.collect()

def get_average_check_plan(date: str):

    date_col, store_col = 0, 1
    wb = gs.open_by_key(GS_AVERAGE_CHECK)
    ws = wb.worksheet_by_title(AVERAGE_CHECK_SHEET_NAME)

    date_values = np.array(ws.get_values((1, 1), (None, None)))
    filter_date = date_values[np.where(date_values[:, date_col] == date)[0]][:, [store_col, 4, 5, 6]]
    del ws
    gc.collect()
    return  filter_date