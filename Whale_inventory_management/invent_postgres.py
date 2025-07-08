from class_StartKeyboard import Employee
from postgres import (
    query_postgre_factory,
    query_postgre_one_value,
    query_postgre,
)


def pg_get_invent_gs_token(id_store: int, column_name: str) -> str:
    """Возвращает токен листа инвентаризации по идентификатору магазина."""

    query = (
        "SELECT {column_name}\n"
        "FROM store\n"
        "WHERE id_store={id_store}"
    ).format(id_store=id_store, column_name=column_name)
    return query_postgre_one_value(query)


def pg_get_invent_gs_token_dept(dept: str) -> dict:
    """Возвращает токен листа инвентаризации для открытых магазинов отдела."""

    query = (
        "SELECT id_store, {dept}\n"
        "FROM store\n"
        "WHERE is_open is TRUE"
    ).format(dept=dept)
    return query_postgre_factory(query)


def pg_get_invent_template(id_store: int, bm_cash: str) -> dict:
    """Возвращает шаблон инвентаризации для указанного отдела магазина."""

    query = (
        "WITH cont AS ("
        " SELECT *"
        " FROM nomenclature"
        " INNER JOIN container USING(id_container)"
        ") "
        "SELECT iiko_code, nomenclature_name, cont.name_container, "
        "cont.weight as cont_weight, invent_type, question_invent "
        "FROM store_nomenclature "
        "INNER JOIN store USING(id_store) "
        "INNER JOIN cont USING(iiko_code) "
        f"WHERE id_store = {id_store} AND department_code = '{bm_cash}' "
        "ORDER BY order_group, nomenclature_name;"
    )
    return query_postgre_factory(query)


def pg_get_write_off_temp(id_store: int, bm_cash: str):
    """Возвращает список номенклатур магазина с типом инвента и контейнером."""

    query = (
        "WITH cont AS ("
        " SELECT *"
        " FROM nomenclature"
        " INNER JOIN container USING(id_container)"
        ") "
        "SELECT iiko_code, nomenclature_name, cont.name_container, "
        "cont.weight as cont_weight, invent_type "
        "FROM store_nomenclature "
        "INNER JOIN store USING(id_store) "
        "INNER JOIN cont USING(iiko_code) "
        f"WHERE id_store = '{id_store}' AND department_code = '{bm_cash}'"
    )
    return query_postgre_factory(query)


def pg_insert_fake_write_off(id_store: int, department_code: str) -> None:
    """Создаёт фиктивное списание для корректной отправки инвентаризации."""

    fake_code_query = (
        "SELECT iiko_code\n"
        "FROM nomenclature\n"
        "WHERE department_code = '{department_code}'\n"
        "LIMIT 1"
    ).format(department_code=department_code)
    fake_prov_code = query_postgre_one_value(fake_code_query)

    query = (
        "INSERT INTO write_off_store (iiko_code, id_store, amount, "
        "comment_write_off) VALUES "
        "('{iiko_code}', {id_store}, 0, 'fake');"
    ).format(iiko_code=fake_prov_code, id_store=id_store)
    query_postgre(query)


def pg_get_department_invent() -> list:
    """Возвращает отделы, в которых разрешена инвентаризация."""

    query = (
        "SELECT department_code, invent_col\n"
        "FROM department\n"
        "WHERE invent_col IS NOT NULL;"
    )
    return query_postgre_factory(query)


def pg_find_incompleted_invent(
    start_datetime: str, end_datetime: str, dept: tuple
) -> list[dict]:
    """Возвращает список магазинов с незавершённой инвентаризацией."""

    query = (
        "SELECT id_store, department_code\n"
        "FROM store CROSS JOIN department\n"
        f"WHERE department_code IN {dept} AND is_open IS TRUE\n"
        "EXCEPT\n"
        "SELECT DISTINCT id_store, department_code\n"
        "FROM invent_whale\n"
        "INNER JOIN nomenclature USING(iiko_code)\n"
        f"WHERE  date_invent >= '{start_datetime}'\n"
        f"AND    date_invent <  '{end_datetime}'\n"
        "ORDER BY id_store"
    )
    return query_postgre_factory(query)


def pg_check_invent_already_done(
    start_datetime: str, end_datetime: str, employee: Employee
) -> dict:
    """Проверяет, выполнена ли инвентаризация без указания типа."""

    query = (
        "FROM nomenclature\n"
        f"WHERE department_code ='{employee.department_code}'\n"
        "INTERSECT\n"
        "SELECT iiko_code\n"
        "FROM invent_whale\n"
        f"WHERE  date_invent >= '{start_datetime}'\n"
        f"AND    date_invent <  '{end_datetime}'\n"
        f"AND id_store = {employee.id_store}\n"
        "AND invent_type IS NULL"
    )
    return query_postgre_factory(query)


# AND invent_type is NULL
def pg_check_special_invent_already_done(
    start_datetime: str,
    end_datetime: str,
    employee: Employee,
    invent_type: str,
) -> dict:
    """Проверяет наличие инвентаризации заданного типа."""

    query = (
        "SELECT iiko_code\n"
        "FROM nomenclature\n"
        f"WHERE department_code ='{employee.department_code}'\n"
        "INTERSECT\n"
        "SELECT iiko_code\n"
        "FROM invent_whale\n"
        f"WHERE  date_invent >= '{start_datetime}'\n"
        f"AND    date_invent <  '{end_datetime}'\n"
        f"AND id_store = {employee.id_store}\n"
        f"AND invent_type = '{invent_type}'"
    )
    return query_postgre_factory(query)


def pg_check_write_off(
    start_datetime: str, end_datetime: str, employee: Employee
) -> dict:
    """Возвращает списания товаров за выбранный период."""

    query = (
        "SELECT iiko_code\n"
        "FROM nomenclature\n"
        f"WHERE department_code ='{employee.department_code}'\n"
        "INTERSECT\n"
        "SELECT iiko_code\n"
        "FROM write_off_store\n"
        f"WHERE  date_write_off >= '{start_datetime}'\n"
        f"AND    date_write_off <  '{end_datetime}'\n"
        f"AND id_store = {employee.id_store}"
    )
    return query_postgre_factory(query)


def get_all_invent_token() -> list[dict]:
    """Собирает токены листов инвентаризации для всех отделов магазинов."""

    department_with_invent = pg_get_department_invent()
    result = []
    for dep in department_with_invent:
        dept_token = pg_get_invent_gs_token_dept(dep["invent_col"])
        for entry in dept_token:
            result.append(
                {
                    "id_store": entry["id_store"],
                    "col_name": dep["invent_col"],
                    "department_code": dep["department_code"],
                    "token": entry[dep["invent_col"]],
                }
            )

    return result


def pg_get_acceptance_whale_template(id_store: int, bm_cash: str) -> dict:
    """Возвращает шаблон приёмки товаров для указанного отдела."""

    query = (
        "WITH cont AS ("
        " SELECT *"
        " FROM nomenclature"
        " INNER JOIN container USING(id_container)"
        ") "
        "SELECT iiko_code, nomenclature_name, cont.name_container, "
        "cont.weight as cont_weight, invent_type, question_invent "
        "FROM store_nomenclature "
        "INNER JOIN store USING(id_store) "
        "INNER JOIN cont USING(iiko_code) "
        f"WHERE id_store = {id_store} AND department_code = '{bm_cash}' "
        "AND prov_acceptance IS TRUE "
        "ORDER BY order_group, nomenclature_name;"
    )
    return query_postgre_factory(query)