import logging
import os

import pandas as pd
import psycopg2
from psycopg2.extras import DictCursor
import numpy as np
from tabulate import tabulate
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

from dotenv import load_dotenv

load_dotenv()
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Krasnoyarsk")
TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"

DBNAME_PG = os.getenv('DBNAME_PG')
USER_PG = os.getenv('USER_PG')
PASSWORD_PG = os.getenv('PASSWORD_PG')
HOST_PG = os.getenv('HOST_PG')
PORT_PG = os.getenv('PORT_PG')


def append_df_pgre(df: pd.DataFrame, table_name: str, index: bool, index_label):
    """Append :class:`pandas.DataFrame` to PostgreSQL table."""

    if TEST_MODE:
        logging.info("TEST_MODE: skip append to %s", table_name)
        logging.debug(df.to_string())
        return

    conn_string = (
        "postgresql://" + USER_PG + ":" + PASSWORD_PG + "@" + HOST_PG + ":" + PORT_PG + "/" + DBNAME_PG
    )
    db = create_engine(conn_string, poolclass=NullPool)
    conn = db.connect()
    df.to_sql(table_name, con=conn, if_exists="append", index=index, index_label=index_label)
    conn.close()
    db.dispose()


def query_postgre(query: str):
    """Execute SQL query and return all fetched rows."""

    logging.debug("Postgre query: %s", query)
    if TEST_MODE and not query.strip().lower().startswith("select"):
        logging.info("TEST_MODE: skip query execution")
        return None

    conn = psycopg2.connect(
        dbname=DBNAME_PG, user=USER_PG, password=PASSWORD_PG, host=HOST_PG, port=PORT_PG
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(query)
                if cur.description:
                    full_fetch = cur.fetchall()
                    logging.debug("Result: %s", full_fetch)
                    return full_fetch
    except Exception as e:
        logging.error(e)
    finally:
        conn.close()


def query_postgre_list(query: str):
    """Return list with first column of each row for given query."""

    result = query_postgre(query)
    if not result:
        return []
    return [row[0] for row in result]



def query_postgre_one_value(query: str):
    """Return single value from query or ``None`` if no data."""

    result = query_postgre(query)
    if result:
        return result[0][0]
    return None


def query_postgre_factory(query: str):
    """Return query result as list of dictionaries."""

    result = query_postgre(query)
    if not result:
        return []
    return [dict(row) for row in result]


def view_all_stoplist():
    """Return table with stop list items for every store."""
    stop_provision = query_postgre("""SELECT store_name, provision_name
                        FROM provision
                        INNER JOIN stoplist USING(id_provision)
                        INNER JOIN store USING(id_store)
                        """)

    stop_meal = query_postgre("""SELECT DISTINCT store_name, meal_name
                        FROM provision
                        INNER JOIN stoplist USING(id_provision)
                        INNER JOIN store USING(id_store)
                        INNER JOIN meal_provision USING(id_provision)
                        INNER JOIN meal USING(id_meal)
                        ORDER BY store_name
                            """)
    store = np.sort(np.array(query_postgre("SELECT store_name FROM store"))).flatten()
    if stop_provision:
        stop_provision = np.array(stop_provision)
        provision = np.unique(stop_provision[:, 1])
        output_prov = np.array([[" " for x in store] for y in provision])

        output_prov = np.c_[provision, output_prov]
        for i in stop_provision:
            column_index = np.where(store == i[0])[0]+1
            row_index = np.where(provision == i[1])[0]
            output_prov[row_index, column_index] = "Х"

        stop_meal = np.array(stop_meal)
        meal = np.unique(stop_meal[:, 1])

        output_meal = np.array([[" " for x in store] for y in meal])
        output_meal = np.c_[meal, output_meal]
        for j in stop_meal:
            column_index = np.where(store == j[0])[0] + 1
            row_index = np.where(meal == j[1])[0]
            output_meal[row_index, column_index] = "Х"
        devider_line= [['=======', '=====', '=====', '=====', '=====', '=====']]
        output_meal =  np.concatenate((devider_line, output_meal), axis=0)
        result_table = np.concatenate((output_prov, output_meal), axis=0)
        table_meal = tabulate(result_table, store, tablefmt="rst", stralign='center')
        return table_meal
    else:
        return None



def del_emloyee_assignment():
    """Remove all rows from ``employee_in_store`` table."""

    query_postgre(
        """
        DELETE FROM employee_in_store;
        """
    )


def end_day_wait():
    """Close all open wait sessions and create zero entries."""
    query_db = '''
            SET TIMEZONE='posix/{TIME_ZONE}';
            UPDATE wait_session
            SET end_wait = date_trunc('minute', now()), duration_wait = date_trunc('minute', (now() - begin_wait))
            WHERE end_wait is NULL
            RETURNING id_wait_session                   
                   '''
    open_sessions = np.array(query_postgre(query_db)).flatten()
    for i in open_sessions:
        query_db = '''
                    SET TIMEZONE='posix/{TIME_ZONE}';
                    INSERT INTO wait_entry (date_time,wait_min,id_wait_session)
                    VALUES (date_trunc('minute', now()), 0, {})
                    '''.format(i)
        query_postgre(query_db)


def get_stores_open(*args):
    """Return array of requested columns for stores currently open."""
    query = '''
        SELECT {} FROM store
        WHERE is_open is TRUE
        '''.format(','.join(args))
    pgre_result = np.array(query_postgre(query))
    return pgre_result


def pg_store(id_store) -> dict:
    """Return store data by ``id_store``."""
    query = '''
        SELECT *
        FROM store
        WHERE id_store = {id_store}
    '''.format(id_store=id_store)
    return query_postgre_factory(query)[0]

def pg_get_position_by_id(tel_id: int):
    """Return employee position and department by telegram id."""
    query ='''
        WITH temp AS(
          SELECT *
          FROM job_titles
          INNER JOIN department USING(id_department)
        )
        SELECT  employee_name, temp.title as position, department_name, department_code, invent_col
        FROM employee
        INNER JOIN job_titles USING(id_job_titles)
        INNER JOIN temp USING(id_job_titles)
        WHERE employee_tlgr = {tel_id}
    '''.format(tel_id=tel_id)
    return query_postgre_factory(query)


def pg_get_department() -> list:
    """Return list of all department names."""
    query ='''
        SELECT DISTINCT department_name
        FROM department
        ORDER BY department_name
    '''
    return query_postgre_list(query)


def pg_get_position_by_dept(dept: str) -> list:
    """Return job titles for provided department."""
    query = '''
        SELECT title
        FROM job_titles
        INNER JOIN department USING (id_department)
        WHERE department_name = '{dept}'
        '''.format(dept=dept)
    return query_postgre_list(query)


def pg_insert_new_employee(
    tel_id: int,
    position: str,
    tel_first_name: str,
    tel_last_name: str,
    tel_username: str,
) -> None:
    """Insert new employee using information from Telegram."""
    query = '''INSERT INTO employee (employee_tlgr, job_title, id_job_titles, tel_first_name, tel_last_name, tel_username)
                SELECT {tel_id}, '{position}', job_titles.id_job_titles, '{tel_first_name}', '{tel_last_name}', '{tel_username}'
                FROM job_titles
                WHERE job_titles.title = '{position}'
                '''.format(tel_id=tel_id, position=position, tel_first_name=tel_first_name,
                           tel_last_name=tel_last_name, tel_username=tel_username)
    query_postgre(query)


def pg_del_employee_from_store(id_tel):
    """Delete employee store assignment by telegram id."""
    '''
        удаляем запись сотрудника из магазина
    :param id_tel:
    :return: id возврвращаем если запись была в БД, если нет, то пусто
    '''

    query = '''
                DELETE FROM employee_in_store
            WHERE chat_id_telegram = {id_tel}
            RETURNING id_employee_in_store
    '''.format(id_tel=id_tel)
    return query_postgre(query)


def pg_get_employee_in_store(tel_id: int):
    """Return store info for employee currently assigned."""
    query = f"""SELECT store_name, id_store
                FROM employee_in_store
                INNER JOIN store USING (id_store)
                WHERE chat_id_telegram = '{tel_id}'
                """
    return query_postgre_factory(query)


def pg_get_employee_position(tel_id: int):
    """Return employee identifier for telegram user."""
    query = f"""SELECT id_employee
                FROM employee
                WHERE employee_tlgr = '{tel_id}'
                """
    return query_postgre_factory(query)




def get_stores_open_list(*args) -> list:
    """Return list of requested columns for open stores."""
    query = '''
        SELECT {} FROM store
        WHERE is_open is TRUE
        '''.format(','.join(args))
    return query_postgre_list(query)


def pgre_read_to_class(query: str, class_name):
    """Execute query and return objects built from rows."""
    conn = psycopg2.connect(dbname=DBNAME_PG, user=USER_PG, password=PASSWORD_PG, host=HOST_PG, port=PORT_PG)
    try:
        with conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(query)
                if cur.description:
                    full_fetch = cur.fetchall()
                    res = []
                    for row in full_fetch:
                        res.append(class_name(**row))
                    return res
    except Exception as e:
        print('ошибка БД query_postgre - c запросом:', str, e)
    finally:
        conn.close()


def pgre_active_notifications(class_to_read) -> list:
    """Return active notifications mapped to ``class_to_read``."""
    query = '''
        SELECT id_department, id_notification, type, notification_text, notification_date, weekdays, stores, notification_time,
                minutes_to_do, department_name, department_code, group_id_telegram
        FROM notification
        INNER JOIN department USING(id_department)
    '''
    return pgre_read_to_class(query, class_to_read)


def pgre_employee_dept_in_store(id_dept: int, id_store: int) -> list:
    """Return telegram ids of employees by department and store."""
    query = '''
            SELECT employee_tlgr
            FROM employee
            INNER JOIN job_titles jt on jt.id_job_titles = employee.id_job_titles
            WHERE id_department = {id_dept}
            INTERSECT
            SELECT chat_id_telegram
            FROM employee_in_store
            WHERE id_store = {id_store};
    '''.format(id_dept=id_dept, id_store=id_store)
    return query_postgre_list(query)


def pg_insert_send_notification(
    id_notification: int, employee_tlgr: int, time_zone: str
) -> int:
    """Insert record about sent notification and return its id."""
    query = '''
        SET TIMEZONE='posix/{time_zone}';
        INSERT INTO send_notification (id_notification, id_employee, datetime_send)
        SELECT {id_notification}, employee.id_employee,  date_trunc('minute', now())
        FROM employee
        WHERE employee.employee_tlgr = {employee_tlgr}
        RETURNING id_send_notification;
    '''.format(time_zone=time_zone, id_notification=id_notification, employee_tlgr=employee_tlgr)
    return query_postgre_one_value(query)


def pg_update_send_notification_press_button(
    id_send_notification: int, time_zone: str
) -> None:
    """Update send_notification when user presses a button."""
    query = '''
        SET TIMEZONE='posix/{time_zone}';
        UPDATE send_notification SET datetime_press_button = date_trunc('minute', now())
        WHERE id_send_notification = {id_send_notification};
    '''.format(time_zone=time_zone, id_send_notification=id_send_notification)
    query_postgre(query)


def pgre_get_employee_by_tel_id(tel_id: int) -> dict:
    """Return employee information by telegram id."""
    query = '''
        SELECT *
        FROM employee
        WHERE employee_tlgr = {tel_id};
    '''.format(tel_id=tel_id)
    return query_postgre_factory(query)[0]


def pg_get_send_notification_by_id(id_send_notification: int) -> dict:
    """Return send_notification record by id."""
    query = '''
        SELECT *
        FROM send_notification
        WHERE id_send_notification = {id_send_notification}
    '''.format(id_send_notification=id_send_notification)
    return query_postgre_factory(query)[0]


def pg_get_nomenclature_to_stop_list(id_store: int) -> list:
    """Return nomenclature names that can be stopped for given store."""
    query = '''
        (SELECT nomenclature_name
            FROM nomenclature
            WHERE stop_list is TRUE
            EXCEPT
            SELECT nomenclature_name
            FROM stop_list
            INNER JOIN store USING(id_store)
            INNER JOIN nomenclature USING(iiko_code)
            WHERE id_store = {id_store} AND date_end_stop is NULL)
            INTERSECT
            SELECT nomenclature_name
            FROM store_nomenclature
            INNER JOIN nomenclature USING(iiko_code)
            WHERE id_store = {id_store}
            ORDER BY nomenclature_name;
    '''.format(id_store=id_store)
    return query_postgre_list(query)


def pg_add_stop_list(id_store: int, nomenclature_name: str) -> None:
    """Add nomenclature item to stop list for store."""
    query = '''
            SET TIMEZONE='posix/{TIME_ZONE}';
            INSERT INTO stop_list (id_store, iiko_code, date_start_stop)
            SELECT {id_store}, nomenclature.iiko_code,  date_trunc('minute', now())
            FROM nomenclature
            WHERE nomenclature.nomenclature_name = '{nomenclature_name}';
    '''.format(id_store=id_store, nomenclature_name=nomenclature_name)
    query_postgre(query)


def pg_get_stop_list(id_store: int) -> list:
    """Return active stop list for store."""
    query = '''
        SELECT nomenclature_name
        FROM stop_list
        INNER JOIN nomenclature USING(iiko_code)
        WHERE id_store = {id_store} AND date_end_stop is NULL;
    '''.format(id_store=id_store)
    return query_postgre_list(query)




def pg_remove_stop_list(id_store: int, nomenclature_name: str) -> None:
    """Close stop list item for store."""
    query = '''
               WITH n as (
                    SELECT iiko_code as iiko
                    FROM nomenclature
                    WHERE nomenclature_name = '{nomenclature_name}'
               )
               UPDATE stop_list
               SET date_end_stop = date_trunc('minute', now())
               FROM n
               WHERE date_end_stop is NULL AND  id_store = {id_store} AND stop_list.iiko_code=n.iiko               
    '''.format(id_store=id_store, nomenclature_name=nomenclature_name)
    query_postgre(query)




def end_day_stop():
    """Finish all active stop list records."""
    query = '''
                SET TIMEZONE='posix/{TIME_ZONE}';
                UPDATE stop_list
                SET date_end_stop = date_trunc('minute', now())
                WHERE date_end_stop is NULL            
                       '''
    query_postgre(query)


def rererr():
    """Return count of active PostgreSQL sessions (debug)."""
    query = '''
                SELECT count(*) FROM pg_stat_activity;
                       '''
    query_postgre(query)




