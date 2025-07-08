import pytz

from Whale_inventory_management.invent_postgres import pg_check_write_off, pg_check_invent_already_done, \
    pg_find_incompleted_invent, pg_check_special_invent_already_done
from datetime import datetime, timedelta

from class_StartKeyboard import Employee

from dotenv import load_dotenv
import os

load_dotenv()
TIME_ZONE = os.getenv('TIME_ZONE')
STOCK_CLOSING_START = os.getenv('STOCK_CLOSING_START')
STOCK_CLOSING_END = os.getenv('STOCK_CLOSING_END')


def datetime_stock_day() -> dict:

    '''
        определеяем в каких интервалах искать результат, если сделать запрос сейчас

    :return:
        какой период запрашивать
    '''
    start_calculation_time = datetime.strptime(STOCK_CLOSING_START, "%H:%M:%S")
    end_calculation_time = datetime.strptime(STOCK_CLOSING_END, "%H:%M:%S")
    now = datetime.now(tz=pytz.timezone(TIME_ZONE))
    if now.time() >= start_calculation_time.time():
        invent_start_date = now.date()
    elif now.time() <= end_calculation_time.time():
        invent_start_date = now.date() - timedelta(days=1)
    else:
        raise Exception('не попавли в интервал')
    invent_end_date = invent_start_date + timedelta(days=1)
    start_datetime = datetime(invent_start_date.year, invent_start_date.month, invent_start_date.day,
                                       start_calculation_time.hour, start_calculation_time.minute,
                                       start_calculation_time.second).strftime("%Y-%m-%d %H:%M:%S")

    end_datetime = datetime(invent_end_date.year, invent_end_date.month, invent_end_date.day,
                                     end_calculation_time.hour, end_calculation_time.minute,
                                     end_calculation_time.second,
                                     ).strftime("%Y-%m-%d %H:%M:%S")
    return {'start_datetime': start_datetime, 'end_datetime': end_datetime}


def check_write_off_done(employee: Employee) -> bool:
    '''
        вносили ли списания на этой точке для этого dept
    :param start_time: с какого времени смотрим списание
    :param end_time:  по какое время смотрим списание
    :return:
    '''
    convert = datetime_stock_day()
    write_off_iiko_code = pg_check_write_off(convert['start_datetime'], convert['end_datetime'], employee)
    if write_off_iiko_code:
        return True
    return False


def check_invent_done(employee: Employee) -> bool:
    '''
        инвентанизация за день, точку и департамент уже выполнена
        true -
    :param start_time: с какого времени смотрим инвент
    :param end_time:  по какое время смотрим инвент
    :param employee - сотрудник
    :return: bool выполнен инвент или нет
    '''
    convert = datetime_stock_day()
    store_dept_incomplete_invent = pg_check_invent_already_done(start_datetime=convert['start_datetime'],
                                                              end_datetime=convert['end_datetime'], employee=employee)
    if store_dept_incomplete_invent:
        return True
    return False


def check_completed_invent() -> list:
    '''
        возвразщает точки и департ., которые еще не сделали инвент
    :return:
    '''
    convert = datetime_stock_day()
    store_dept_incomplete_invent = pg_find_incompleted_invent(start_datetime=convert['start_datetime'],
                                                              end_datetime=convert['end_datetime'],
                                                              dept=('BM', 'CASHIER'))
    return store_dept_incomplete_invent

#
def check_invent_acceptance_done(employee: Employee) -> bool:
    now = datetime.now(tz=pytz.timezone(TIME_ZONE))
    tmrr = now + timedelta(days=1)
    now_date = now.strftime("%Y-%m-%d")
    tmrr_date = tmrr.strftime("%Y-%m-%d")
    check = pg_check_special_invent_already_done(now_date, tmrr_date, employee, 'acceptance')
    if check:
        return True
    return False


def check_invent_morning_done(employee: Employee) -> bool:
    now = datetime.now(tz=pytz.timezone(TIME_ZONE))
    tmrr = now + timedelta(days=1)
    now_date = now.strftime("%Y-%m-%d")
    tmrr_date = tmrr.strftime("%Y-%m-%d")
    check = pg_check_special_invent_already_done(now_date, tmrr_date, employee, 'morning')
    if check:
        return True
    return False


#
# ee = Employee(department_code='BM', id_store=1, invent_col='invent_bm', employee_name=None, store_name='БК2', department_name='БМ_ПМ', position='БМ')
# # write_off = check_invent_done(ee)
# # print(write_off)
# rer = check_invent_acceptance_done(ee)
# print(rer)