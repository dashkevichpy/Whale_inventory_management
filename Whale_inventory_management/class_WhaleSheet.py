import abc
import gc
from collections import namedtuple
from enum import Enum, auto

import numpy as np
import pandas as pd
import pygsheets
from googleapiclient.errors import HttpError

from Whale_inventory_management.invent_postgres import pg_get_write_off_temp, pg_get_invent_gs_token, \
    get_all_invent_token, pg_get_invent_template, pg_get_acceptance_whale_template
from class_StartKeyboard import Employee

from dotenv import load_dotenv
import os

load_dotenv()
LINK_GS_JSON = os.getenv('LINK_GS_JSON')
from typing import Union

from postgres import append_df_pgre

INVENT_SHEET_NAME = 'Инвентаризация'
WRITE_OFF_SHEET_NAME = 'Списание'
WRITE_OFF_TMRR_SHEET_NAME = 'Спишется завтра'
ACCEPTANCE_SHEET_NAME = '📦 Прием транспортировки'
MORNING_INVENT_SHEET_NAME = '☀️Утро инвентаризация'




class WhaleSheet(abc.ABC):
    forbidden_symbols = [',', '.', '/', '\xa0', '%', '@','#','$','^','&','*','(',')','"','!','`']
    symbol_empty = '-1'


    @abc.abstractmethod
    def __init__(self, em: Employee) -> None:
        """Initialize Google spreadsheet handler.

        Args:
            em: Employee information with store identifiers.
        """
        token = pg_get_invent_gs_token(em.id_store, em.invent_col)
        gs = pygsheets.authorize(service_file=LINK_GS_JSON)
        self.em = em
        self.wb = gs.open_by_key(token)

    @abc.abstractmethod
    def clear(self) -> None:
        """Clear worksheet content."""
        raise NotImplemented

    @abc.abstractmethod
    def new_sheet(self) -> None:
        """Create a new worksheet."""
        raise NotImplemented

    @abc.abstractmethod
    def check_sheet(self, df: pd.DataFrame) -> pd.Series:
        """Return a series with errors for the provided dataframe."""
        raise NotImplemented

    @abc.abstractmethod
    def get_result(self) -> None:
        """Process worksheet and return status."""
        raise NotImplemented

    @abc.abstractmethod
    def update_error(self, *args) -> None:
        """Write error information to sheet."""
        raise NotImplemented

    @abc.abstractmethod
    def write_db(self, df: pd.DataFrame) -> None:
        """Write dataframe to database."""
        raise NotImplemented


class InventSheet(WhaleSheet):
    '''
        инвентариазацонные листы: регулярная, контроль поставки, проверка вечерней инвентаризации
        self.invent_type  - что указываем при записи
    '''
    start_cell: tuple = (2, 1)
    end_cell: tuple = (150, 7)
    suff_invent = '_invent'
    suff_templ = '_templ'
    error_col_num: int = 7
    headers = {'iiko_code': 'iiko_code', 'nomenclature_name': 'заготовка', 'un': 'шт.', 'weight': 'гр.',
               'container': 'тара', 'y_or_n': '0 или 1', 'error': 'ошибка заполнения'}
    check_columns = ['weight', 'container', 'y_or_n', 'un']


    def __init__(
        self,
        em: Employee,
        sheet: Union[str, pygsheets.worksheet.Worksheet],
        func_get_nomenclature,
        invent_type: Union[str, None],
    ) -> None:
        """Initialize inventory worksheet.

        Args:
            em: Employee information.
            sheet: Worksheet title or object.
            func_get_nomenclature: Callable to fetch nomenclature.
            invent_type: Inventory type for DB records.
        """
        if isinstance(sheet, str):
            super().__init__(em)
            self.ws = self.wb.worksheet_by_title(sheet)
        elif isinstance(sheet, pygsheets.worksheet.Worksheet):
            self.em = em
            self.ws = sheet
        else:
            raise ValueError('InventSheet.sheet incorrect type')

        self.func_get_nomenclature = func_get_nomenclature
        self.invent_type = invent_type  # какой тип инвентаризации используем


    def clear(self) -> None:
        """Clear worksheet."""
        self.ws.clear('*')

        def template(self) -> pd.DataFrame:
            """Return template dataframe for the worksheet."""

        df = pd.DataFrame(
            self.func_get_nomenclature(id_store=self.em.id_store, bm_cash=self.em.department_code)
        )
        df.loc[df['name_container'] == 'штуки', 'un'] = ''  # добавляем столбец 'штуки'
        df.loc[df['name_container'] == 'да/нет', 'y_or_n'] = ''  # столбец с да/ нет - 1 или 0
        df.loc[df['name_container'] == 'да/нет', 'nomenclature_name'] = df['nomenclature_name'] + ' ' + df['question_invent']
        df.loc[(df['name_container'] != 'штуки') & (df['name_container'] != 'да/нет'), 'weight'] = ''
        df.loc[(df['name_container'] != 'штуки') & (df['name_container'] != 'да/нет') & (df['name_container'] != 'вес/шт.'), 'container'] = ''
        df = df.fillna(super().symbol_empty)
        df['error'] = super().symbol_empty
        return df

    def new_sheet(self) -> None:
        """Create new worksheet with template."""

        df = self.template()
        df = df[self.headers.keys()]  # оставляем только нужные столбцы
        df.columns = self.headers.values()  # переименовываем
        self.clear()
        self.ws.set_dataframe(df=df, start=(1, 1), copy_head=True)

    def check_sheet(self, df: pd.DataFrame) -> pd.Series:
        """Validate worksheet data and return error column."""

        df['error'] = super().symbol_empty
        for key_field in self.check_columns:
            key_invent = key_field + self.suff_invent
            key_templ = key_field + self.suff_templ
            df.loc[df[key_invent] == '', 'error'] = f'{self.headers[key_field]} - пусто'

            df.loc[(df[key_templ] == super().symbol_empty) & (df[key_invent] != super().symbol_empty), 'error'] = \
                f'{self.headers[key_field]} - не надо заполнять - поставьте "-1"'

            df.loc[(df[key_templ] == "") & (df[key_invent] == super().symbol_empty), 'error'] = \
                f'{self.headers[key_field]} - должна быть цифра больше 0'

            for symbol in super().forbidden_symbols:
                df.loc[df[key_invent].str.find(
                    symbol) != -1, 'error'] = f'{self.headers[key_field]} - уберите "{symbol}"'
        return df['error']

    def write_db(self, df: pd.DataFrame) -> None:
        """Write inventory results to database."""

        invent = df[['iiko_code', 'invent_result']]
        invent.insert(1, 'id_store', self.em.id_store)
        if self.invent_type:
            invent.insert(1, 'invent_type', self.invent_type)
        append_df_pgre(df=invent, table_name='invent_whale', index=False, index_label=None)

    def update_error(self, sr: pd.Series,) -> None:
        """Update error column on worksheet."""

        df = pd.DataFrame(sr)
        self.ws.set_dataframe(df=df, start=(self.start_cell[0], self.error_col_num), copy_head=False)

    def get_result(self):
        """Read worksheet, validate and save result."""

        df = self.template()
        # считываем без учета колонки ошибки
        df_inv = self.ws.get_as_df(has_header=False, empty_value='', start=self.start_cell,
                                   end=(self.end_cell[0], self.end_cell[1] - 1), numerize=False,
                                   include_tailing_empty=True)
        df_inv.columns = list(self.headers.keys())[:-1]  # без столбца error - он всегда последний
        c_df = pd.merge(df, df_inv, on=['iiko_code', 'nomenclature_name'], how='left',
                        suffixes=(self.suff_templ, self.suff_invent))
        error_flag = self.check_sheet(c_df)
        if all(error_flag == super().symbol_empty):
            c_df = c_df.astype({col + self.suff_invent: 'int' for col in self.check_columns})  # в int кололнки, с которыми проводим операции
            c_df['invent_result'] = np.where(c_df['name_container'] == 'да/нет', c_df['y_or_n_invent'],
                                             np.where(c_df['name_container'] == 'штуки', c_df['un_invent'],
                                                      c_df['weight_invent'] - c_df['cont_weight'] * c_df[
                                                          'container_invent']))
            c_df = c_df.astype({'invent_result': 'int'})
            c_df.loc[c_df['invent_result'] < 0, 'error'] = 'чистый вес отрицательный'
            error_flag = c_df['error']
            if all(error_flag == super().symbol_empty):
                self.write_db(c_df)
        self.update_error(error_flag)
        if all(error_flag == super().symbol_empty):
            return True
        else:
            return False

class AllSheetInvent(InventSheet):
    def __init__(self, sheet_name: str, func_get_nomenclature):
        """Initialize inventory sheets for all stores."""

        gs = pygsheets.authorize(service_file=LINK_GS_JSON)
        self.token = get_all_invent_token()
        self.allsheet = []
        self.sheet = sheet_name
        for t in self.token:
            employee = Employee(
                department_code=t['department_code'],
                id_store=t['id_store'],
                invent_col=t['col_name'],
                employee_name=None,
                store_name=None,
                department_name=None,
                position=None,
            )
            wb = gs.open_by_key(t['token'])
            ws = wb.worksheet_by_title(self.sheet)
            sheet = InventSheet(
                em=employee,
                sheet=ws,
                func_get_nomenclature=func_get_nomenclature,
                invent_type=None,
            )
            self.allsheet.append(sheet)

    def update(self):
        """Update worksheets for all stores."""

        for sheet in self.allsheet:
            sheet.new_sheet()




class WriteOffSheet(WhaleSheet):
    start_cell: tuple = (2, 1)
    end_row: int = 30
    symbol_contribute = '✅'
    symbol_input_container = 'да->'

    def __init__(
        self,
        em: Employee,
        sheet: Union[str, pygsheets.worksheet.Worksheet],
        headers: dict,
        check_columns: list[str],
        formula_columns: dict,
        columns_pgre: list,
    ) -> None:
        """Initialize write-off worksheet."""
        if isinstance(sheet, str):
            super().__init__(em)
            self.ws = self.wb.worksheet_by_title(sheet)
        elif isinstance(sheet, pygsheets.worksheet.Worksheet):
            self.em = em
            self.ws = sheet
        else:
            raise ValueError('WriteOffSheet.sheet incorrect type')

        self.headers = {}
        SheetHeaders = namedtuple('SheetHeaders', ('column_name', 'column_num'))
        for num, value in enumerate(headers.items()):
            self.headers[value[0]] = SheetHeaders(value[1], num+1)
        self.check_columns = check_columns
        self.formula_columns = formula_columns
        self.columns_check_int = ['input_amount', 'container_amount']
        self.end_column = len(headers)
        self.columns_pgre = columns_pgre
        # проверяем, что check_columns есть в headers
        for i in check_columns:
            if i not in headers:
                raise ValueError(f'check_columns - cтолбец {i} не принадлежит {self.headers.keys()}')

        if 'error' not in headers:
            raise ValueError(f'Нет столбца error в  {self.headers.keys()}')

        if 'contribute' not in headers:
            raise ValueError(f'Нет столбца contribute в  {self.headers.keys()}')

        for i in formula_columns.keys():
            if i not in headers:
                raise ValueError(f'formula_columns - столбец {i} не принадлежит {self.headers.keys()}')

    def clear(self) -> None:
        """Clear worksheet."""
        self.ws.clear('*')

    def new_sheet(self) -> None:
        """Create a new worksheet with formulas."""

        self.clear()
        if self.formula_columns:
            for fc in self.formula_columns:
                self.ws.update_col(index=self.headers[fc].column_num,
                                   values=[self.formula_columns[fc] for _ in range(0, self.end_row)],
                                   row_offset=0)
        self.ws.update_row(index=1, values=[i.column_name for i in self.headers.values()], col_offset=0)

    def check_sheet(self, df: pd.DataFrame) -> pd.Series:
        """Validate worksheet data and return error column."""

        df['error'] = super().symbol_empty
        for col in self.check_columns:
            df.loc[df[col] == '', 'error'] = 'не внесено ' + str(col)

        for col in self.columns_check_int:
            for symbol in super().forbidden_symbols:
                df.loc[df[col].str.find(symbol) != -1, 'error'] = f'{col} - уберите "{symbol}"'
        # проверка на заполнение тары
        df.loc[(df['is_container?'] == self.symbol_input_container) & (df['container_amount'] == ''), 'error'] \
            = 'заполните ' + str('Кол-во контейнера')
        return df['error']

    def update_error(self, sr: pd.Series, count_contribute) -> None:
        """Update error column on worksheet."""

        df = pd.DataFrame(sr)
        self.ws.set_dataframe(df=df, start=(self.start_cell[0] + count_contribute, self.headers['error'].column_num), copy_head=False)

    def write_db(self, df: pd.DataFrame) -> None:
        """Write write-off information to database."""

        df_pgre = df[self.columns_pgre]
        df_pgre.insert(loc=2, column='id_store', value=self.em.id_store)
        append_df_pgre(df=df_pgre, table_name='write_off_store', index=False, index_label=None)


    def contribute(self, offset_row: int, count_contribute: int) -> None:
        """Mark rows as processed."""

        self.ws.update_col(
            self.headers['contribute'].column_num,
            [self.symbol_contribute for _ in range(count_contribute)],
            row_offset=offset_row + self.start_cell[0] - 1,
        )

    def get_result(self):
        """Read sheet, validate and save results."""

        df = self.ws.get_as_df(
            has_header=False,
            start=self.start_cell,
            end=(self.end_row, self.end_column),
            numerize=False,
            include_tailing_empty=True,
        )
        df.columns = self.headers.keys()
        already_contribute = df[df['contribute'] == self.symbol_contribute]
        already_count_contribute = len(already_contribute.index)
        df = df.drop(already_contribute.index)  # исключаем строки со внесенныыми в БД
        if df.eq('').all(axis=None):
            return None
        error_flag = self.check_sheet(df)
        if all(error_flag == super().symbol_empty):
            df_weight = df.loc[df['is_container?'] == self.symbol_input_container]  # позиции, для которых надо считать вес
            if not df_weight.empty:
                nomenclature = pd.DataFrame(pg_get_write_off_temp(id_store=self.em.id_store, bm_cash=self.em.department_code))
                df_weight_index = df_weight.index  # сохраняем порядок индексов, в merge он обнулится
                df_weight = df_weight.merge(nomenclature[['iiko_code', 'cont_weight']], on=['iiko_code'], how='left')
                # рассчитываем чистый вес
                df_weight = df_weight.astype({'input_amount': 'int64', 'container_amount': 'int64'})
                df_weight['amount'] = df_weight['input_amount'] - df_weight['container_amount'] * df_weight['cont_weight']
                df_weight.loc[df_weight['amount'] < 0, 'error_net_weight'] = 'чистый вес отрицательный'

                df_weight.index = df_weight_index  # возвращаем исходные индексы
                error_flag = df.merge(df_weight[['error_net_weight']], left_index=True, right_index=True, how='left')
                error_flag = error_flag['error_net_weight']
                error_flag.fillna(super().symbol_empty, inplace=True)

                if all(error_flag == super().symbol_empty):
                    df['amount'] = df['input_amount']
                    # df_weight.index = df_weight_index
                    df.loc[df['is_container?'] == self.symbol_input_container, 'amount'] = df_weight['amount']
            else:
                df['amount'] = df['input_amount']

        self.update_error(error_flag, already_count_contribute)
        if all(error_flag == super().symbol_empty):  # если нет ошибок
            self.write_db(df)
            self.contribute(count_contribute=df.shape[0], offset_row=already_count_contribute)
            return True
        else:
            return False



class WriteOffType(Enum):
    WRITE_OFF_TODAY = auto()
    ALL_WRITE_OFF_TODAY = auto()
    WRITE_OFF_TMRR = auto()


def wr_off_init(em: Employee, write_off_type: WriteOffType, wb) -> WriteOffSheet:
    """Create write-off sheet based on type."""
    if write_off_type == WriteOffType.WRITE_OFF_TMRR:
        headers = {'iiko_code': 'iiko_code', 'nomenclature_name': 'заготовка', 'measure_un': 'Единицы внесения',
                   'input_amount': 'Кол-во', 'is_container?': 'Вносить тару?', 'container_amount': 'Кол-во тары',
                   'hour_write_off': 'Час списания', 'comment_write_off': 'Комментарий', 'contribute': 'Внесено',
                   'error': 'ошибка заполнения'}
        check_columns = ['nomenclature_name', 'input_amount', 'hour_write_off']
        formula_columns = {
            'iiko_code': '=ifna(indirect(' + '"Инвентаризация!A"' + ' & MATCH(indirect("R[0]C[1]";FALSE);' + "'Инвентаризация'" + '!B:B;0));"")',
            'measure_un': '=ifna(ifs( and(VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;2;0)=-1; '
                           'VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;3;0)=-1);"вес или шт";'
                           'and(VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;2;0)=-1; '
                           'VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;3;0)<>-1); "гр";'
                           'and(VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;2;0)<>-1; '
                           'VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;3;0)=-1); "шт");"")',
            'is_container?': '=ifna(if(VLOOKUP(indirect("R[0]C[-3]";FALSE);' + "'Инвентаризация'" + '!B:E;4;0)>-1;"да->";"нет");"")'

        }
        columns_pgre = ['iiko_code', 'amount', 'hour_write_off']
        sheet_name = WRITE_OFF_TMRR_SHEET_NAME

    elif write_off_type == WriteOffType.WRITE_OFF_TODAY or write_off_type == WriteOffType.ALL_WRITE_OFF_TODAY:
        headers = {'iiko_code': 'iiko_code', 'nomenclature_name': 'заготовка', 'measure_un': 'Единицы внесения',
                   'input_amount': 'Кол-во', 'is_container?': 'Вносить тару?', 'container_amount': 'Кол-во тары',
                   'reason_write_off':'Причина списания', 'comment_write_off': 'Комментарий', 'contribute': 'Внесено',
                   'error': 'ошибка заполнения'}
        check_columns = ['nomenclature_name', 'input_amount', 'reason_write_off']
        formula_columns = {
            'iiko_code':'=ifna(indirect('+ '"Инвентаризация!A"' + ' & MATCH(indirect("R[0]C[1]";FALSE);' + "'Инвентаризация'" + '!B:B;0));"")',

            'measure_un':'=ifna(ifs( and(VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;2;0)=-1; '
                         'VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;3;0)=-1);"вес или шт";'
                         'and(VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;2;0)=-1; '
                         'VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;3;0)<>-1); "гр";'
                         'and(VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;2;0)<>-1; '
                         'VLOOKUP(indirect("R[0]C[-1]";FALSE);' + "'Инвентаризация'" + '!B:D;3;0)=-1); "шт");"")',
            'is_container?':'=ifna(if(VLOOKUP(indirect("R[0]C[-3]";FALSE);' + "'Инвентаризация'" + '!B:E;4;0)>-1;"да->";"нет");"")'
        }
        columns_pgre = ['iiko_code', 'amount', 'reason_write_off', 'comment_write_off']

        if write_off_type == WriteOffType.ALL_WRITE_OFF_TODAY:
            sheet_name = wb.worksheet_by_title(WRITE_OFF_SHEET_NAME)
        else:
            sheet_name = WRITE_OFF_SHEET_NAME
    else:
        raise ValueError(str(write_off_type) + 'нет такого атрибута в  WriteOffType')

    write_off = WriteOffSheet(em=em, sheet=sheet_name, headers=headers, check_columns=check_columns,
                               formula_columns=formula_columns, columns_pgre=columns_pgre)

    return write_off



# ee = Employee(department_code='BM', id_store=7, invent_col='invent_bm', employee_name=None, store_name='БК2', department_name='БМ_ПМ', position='БМ')
# write_off_tmrr = wr_off_init(em=ee, write_off_type=WriteOffType.WRITE_OFF_TODAY, wb=None)
# write_off_tmrr.get_result()


class AllSheetWriteOff(WriteOffSheet):
    def __init__(self):
        """Initialize write-off sheets for all stores."""

        gs = pygsheets.authorize(service_file=LINK_GS_JSON)
        token = get_all_invent_token()
        self.allsheet = []
        for t in token:
            employee = Employee(
                department_code=t['department_code'],
                id_store=t['id_store'],
                invent_col=t['col_name'],
                employee_name=None,
                store_name=None,
                department_name=None,
                position=None,
            )

            wb = gs.open_by_key(t['token'])
            sheet = wr_off_init(employee, WriteOffType.ALL_WRITE_OFF_TODAY, wb)
            self.allsheet.append(sheet)

    def update(self):
        """Update write-off worksheets for all stores."""

        for sheet in self.allsheet:
            sheet.new_sheet()
            del sheet
            gc.collect()




def update_invent_sheets():
    """Refresh inventory sheets for all stores."""

    invent_sheets = AllSheetInvent(INVENT_SHEET_NAME, pg_get_invent_template)
    invent_sheets.update()
    del invent_sheets
    gc.collect()


def update_acceptance_sheets():
    """Refresh acceptance sheets for all stores."""

    invent_sheets = AllSheetInvent(ACCEPTANCE_SHEET_NAME, pg_get_acceptance_whale_template)
    invent_sheets.update()
    del invent_sheets
    gc.collect()


def update_write_off_sheets():
    """Refresh write-off sheets for all stores."""

    write_off_sheets = AllSheetWriteOff()
    write_off_sheets.update()
    del write_off_sheets
    gc.collect()


def update_morning_invent_sheets():
    """Refresh morning inventory sheets for all stores."""

    invent_sheets = AllSheetInvent(
        MORNING_INVENT_SHEET_NAME,
        pg_get_acceptance_whale_template,
    )  # позиции у утр. инвент и приёмки транспортировки совпадают
    invent_sheets.update()
    del invent_sheets
    gc.collect()


