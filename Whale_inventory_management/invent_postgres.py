from typing import Union
from class_StartKeyboard import Employee
from postgres import query_postgre_factory, query_postgre_one_value, query_postgre_list, query_postgre


def pg_get_invent_gs_token(id_store: int, column_name: str) -> str:
    '''
        получаем token листа с инвентаризацией кита по id
    :param id_store:
    :return:
    '''
    query = '''
            SELECT {column_name}
            FROM store
            WHERE id_store={id_store}
        '''.format(id_store=id_store,column_name=column_name)
    return query_postgre_one_value(query)



def pg_get_invent_gs_token_dept(dept: str) -> dict:
    '''

    '''
    query = '''
            SELECT id_store, {dept} 
            FROM store
            WHERE is_open is TRUE
        '''.format(dept=dept)
    return query_postgre_factory(query)


def pg_get_invent_template(id_store: int, bm_cash: str) -> dict:
    query = '''
                WITH cont AS(
                  SELECT *
                  FROM nomenclature
                  INNER JOIN container USING(id_container)
                )
                SELECT iiko_code, nomenclature_name,  cont.name_container, cont.weight as cont_weight, invent_type, question_invent
                FROM store_nomenclature
                INNER JOIN store USING(id_store)
                INNER JOIN cont USING(iiko_code)
                WHERE id_store = {id_store} AND department_code = '{bm_cash}'
                ORDER BY order_group, nomenclature_name;
                '''.format(id_store=id_store, bm_cash=bm_cash)
    return query_postgre_factory(query)


def pg_get_write_off_temp(id_store: int, bm_cash: str):
    '''
        возвращает список номенклатур в конкретном ките, а также тип инвента, контейнер, вес
    :param id_store:
    :param bm_cash: бм или кассир
    :return:
    '''
    query = '''
                WITH cont AS(
                  SELECT *
                  FROM nomenclature
                  INNER JOIN container USING(id_container)
                )
                SELECT iiko_code, nomenclature_name,  cont.name_container, cont.weight as cont_weight, invent_type
                FROM store_nomenclature
                INNER JOIN store USING(id_store)
                INNER JOIN cont USING(iiko_code)
                WHERE id_store = '{id_store}' AND department_code = '{bm_cash}'
                '''.format(id_store=id_store, bm_cash=bm_cash)
    return query_postgre_factory(query)


def pg_insert_fake_write_off(id_store: int, department_code: str) -> None:
    '''
        тайм зон - красноярск!
        списание делаем до отправки инвентаризации, чтобы можно было корректно посчитать перерасход с учетом списания
        по БД проверяем - были ли сегодня отправлены списания, если не были и юзер отмечает, что не было, то вносим
        в БД фейковое списание - чтобы проверка считала, что на сегодня уже было что- то проведено и позволила отправить
        инвент
    :param id_store:
    :param bm_cash:
    :return:
    '''
    fake_prov_code = '''
        SELECT iiko_code
        FROM nomenclature
        WHERE department_code = '{department_code}'
        LIMIT 1
    '''.format(department_code=department_code)
    fake_prov_code = query_postgre_one_value(fake_prov_code)

    query = '''
                INSERT INTO write_off_store (iiko_code, id_store, amount, comment_write_off) VALUES
                ('{iiko_code}',{id_store},0, 'fake');
                '''.format(iiko_code=fake_prov_code, id_store=id_store)
    query_postgre(query)


def pg_get_department_invent() -> list:
    query ='''
        SELECT department_code, invent_col
        FROM department
        WHERE invent_col is not NULL;
    '''
    return query_postgre_factory(query)


def pg_find_incompleted_invent(start_datetime: str, end_datetime: str, dept: tuple) -> list[dict]:
    '''
        список незавершенных инвентаризаций
    :return:  [{'id_store': 1, 'department_code': 'BM'}, {'id_store': 1, 'department_code': 'CASHIER'} ...
    '''

    query = '''
        SELECT id_store, department_code
        FROM store CROSS JOIN department
        WHERE department_code IN {dept} AND is_open is TRUE
        EXCEPT
        SELECT DISTINCT id_store, department_code
        FROM invent_whale
        INNER JOIN nomenclature USING(iiko_code)
        WHERE  date_invent >= '{start_date}'
        AND    date_invent <  '{end_date}'
        ORDER BY id_store
    '''.format(start_date=start_datetime, end_date=end_datetime, dept=dept)
    return query_postgre_factory(query)


def pg_check_invent_already_done(start_datetime: str, end_datetime: str, employee: Employee) -> dict:
    '''

    :param start_date:
    :param end_date:
    :param employee:
    :return:
    '''
    query = '''
        FROM nomenclature
        WHERE department_code ='{dept}'
        INTERSECT
        SELECT iiko_code
        FROM invent_whale
        WHERE  date_invent >= '{start_datetime}'
        AND    date_invent <  '{end_datetime}'
        AND id_store = {id_store}
        AND invent_type is NULL
    '''.format(start_datetime=start_datetime, end_datetime=end_datetime, dept=employee.department_code,
               id_store=employee.id_store)
    return query_postgre_factory(query)

# AND invent_type is NULL
def pg_check_special_invent_already_done(start_datetime: str, end_datetime: str, employee: Employee, invent_type: str):
    '''

    :param start_date:
    :param end_date:
    :param employee:
    :return:
    '''
    query = '''
        SELECT iiko_code
        FROM nomenclature
        WHERE department_code ='{dept}'
        INTERSECT
        SELECT iiko_code
        FROM invent_whale
        WHERE  date_invent >= '{start_datetime}'
        AND    date_invent <  '{end_datetime}'
        AND id_store = {id_store}
        AND invent_type = '{invent_type}'
    '''.format(start_datetime=start_datetime, end_datetime=end_datetime, dept=employee.department_code,
               id_store=employee.id_store, invent_type=invent_type)
    return query_postgre_factory(query)


def pg_check_write_off(start_datetime: str, end_datetime: str, employee: Employee):
    '''
        возвращает списания в ките
    :param start_datetime:
    :param end_datetime:
    :param employee:
    :return:
    '''
    query = '''
        SELECT iiko_code
        FROM nomenclature
        WHERE department_code ='{dept}'
        INTERSECT
        SELECT iiko_code
        FROM write_off_store
        WHERE  date_write_off >= '{start_datetime}'
        AND    date_write_off <  '{end_datetime}'
        AND id_store = {id_store}
    '''.format(start_datetime=start_datetime, end_datetime=end_datetime, dept=employee.department_code, id_store=employee.id_store)
    return query_postgre_factory(query)


def get_all_invent_token() -> list[dict]:
    '''
        возвращает список с айди точки, колонку инв и токен листа
    :return:
            [{'id_store': 2, 'col_name': 'invent_bm', 'department_code': 'BM',
            'token': '1b1st-dFrpMf6FEKiERHVq30Yr8usV_2PUnZEi4Ltjgc'},
            {'id_store': 3, 'col_name': 'invent_bm', 'department_code': 'BM',.....
    '''
    department_with_invent = pg_get_department_invent()  # {'department_code': 'BM', 'invent_col': 'invent_bm'}
    result = []
    for dep in department_with_invent:
        dept_token = pg_get_invent_gs_token_dept(dep['invent_col'])
        for entry in dept_token:
            result.append({'id_store': entry['id_store'], 'col_name': dep['invent_col'],
                           'department_code': dep['department_code'], 'token': entry[dep['invent_col']]})

    return result


def pg_get_acceptance_whale_template(id_store: int, bm_cash: str) -> dict:
    query = '''
                WITH cont AS(
                  SELECT *
                  FROM nomenclature
                  INNER JOIN container USING(id_container)
                )
                SELECT iiko_code, nomenclature_name,  cont.name_container, cont.weight as cont_weight, invent_type, question_invent
                FROM store_nomenclature
                INNER JOIN store USING(id_store)
                INNER JOIN cont USING(iiko_code)
                WHERE id_store = {id_store} AND department_code = '{bm_cash}' AND prov_acceptance is TRUE
                ORDER BY order_group, nomenclature_name;
                '''.format(id_store=id_store, bm_cash=bm_cash)
    return query_postgre_factory(query)
