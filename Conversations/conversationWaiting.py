from __future__ import annotations

import logging
import os
from typing import Any

import numpy as np
from aiogram import Router
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv

from class_StartKeyboard import keyboard_start
from decorators import check_group
from keyboards import (
    BUTTON_WAIT_TITLE,
    BUTTON_WAIT_CANCEL,
    BUTTON_REMOVE_WAIT,
    keyboard_cancel_wait,
    keyboard_from_list,
)
from postgres import query_postgre

load_dotenv()
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Krasnoyarsk")
ERROR_ADMIN_ID = os.getenv("ERROR_ADMIN_ID")
TG_GROUP_NAMES = eval(os.getenv("TG_GROUP_NAMES"))
OPERATION_BM = os.getenv("OPERATION_BM")
CASHIER_TG = os.getenv("CASHIER_TG")
CHAT_TIMEOUT = int(os.getenv("CHAT_TIMEOUT"))

router = Router()

WAIT_MINUTES = ["15", "20", "30", "45"]
PRODUCT_NAME_WAITING = ["🍕", "🍔", "🚚"]
PRODUCT_NAME = PRODUCT_NAME_WAITING[0:2]


class WaitingState(StatesGroup):
    """Conversation states for product waiting."""

    write_wait = State()


@router.message(F.text == BUTTON_WAIT_TITLE)
@check_group
async def wait_start(message: Message, state: FSMContext) -> None:
    """Start waiting conversation."""

    await state.update_data(id_user_chat=message.chat.id)
    query_db = f"""
        SELECT store_name
        FROM employee_in_store
        INNER JOIN store USING(id_store)
        WHERE chat_id_telegram = '{message.chat.id}'
    """
    whale_store = np.array(query_postgre(query_db))
    if whale_store.size == 0:
        await message.answer(
            text="Пожалуйста, выбери где сегодня работаешь",
            reply_markup=await keyboard_start(message.chat.id, state),
        )
        await state.clear()
        return

    await state.update_data(what_whale=whale_store[0, 0])
    await message.answer(
        text=f"Выбрали\n{BUTTON_WAIT_TITLE}",
        reply_markup=keyboard_cancel_wait(),
    )

    buttons_wait = [f"{i} {j}" for i in WAIT_MINUTES for j in PRODUCT_NAME]
    query_db = f"""
        SELECT now_wait, product_name, id_wait_session, max_wait
        FROM wait_session
        INNER JOIN store USING(id_store)
        WHERE store_name = '{whale_store[0, 0]}' and
              end_wait is NULL and
              product_name = ANY('{{🍔,🍕}}');
    """
    open_sessions = np.array(query_postgre(query_db))
    await state.update_data(open_sessions=open_sessions)
    text = ""
    if open_sessions.size > 0:
        text = f"Сейчас ожидание в {whale_store[0, 0]}\n"
        remove_wait = [" " for _ in PRODUCT_NAME]
        for item in open_sessions:
            text += f"{item[0]} {item[1]}\n"
            index_prod = PRODUCT_NAME.index(item[1])
            remove_wait[index_prod] = f"{BUTTON_REMOVE_WAIT} {item[1]}"
        remove_wait.extend(buttons_wait)
        buttons_wait = remove_wait
    else:
        text = f"Ожидания в {whale_store[0, 0]} нет\n"

    await message.answer(
        text=text + "поменять ожидание (в мин.):",
        reply_markup=keyboard_from_list(buttons_wait, len(PRODUCT_NAME)),
    )
    await state.set_state(WaitingState.write_wait)


@router.callback_query(WaitingState.write_wait)
async def write_wait(query: CallbackQuery, state: FSMContext) -> None:
    """Record waiting time for selected product."""

    await query.answer()
    callback_data = query.data
    await state.update_data(wait=callback_data)
    wait_min, product = callback_data.split()
    data = await state.get_data()
    open_sessions: list[Any] | np.ndarray = data.get("open_sessions", [])

    id_wait_session = 0
    text = ""
    if len(open_sessions) > 0:
        logging.info(
            "waiting - %s нажали кнопку ожиданий-  ожидания есть ",
            data["id_user_chat"],
        )
        for item in open_sessions:
            if item[1] == product:
                id_wait_session = item[2]
                if wait_min == BUTTON_REMOVE_WAIT:
                    text = f"{BUTTON_REMOVE_WAIT} {product} в {data['what_whale']}"
                    q_close_wait_session = f"""
                        SET TIMEZONE='posix/{TIME_ZONE}';
                        UPDATE wait_session
                        SET end_wait = date_trunc('minute', now()),
                            duration_wait = date_trunc('minute', (NOW() - begin_wait)),
                            now_wait = 0
                        WHERE id_wait_session = {id_wait_session}
                    """
                    query_postgre(q_close_wait_session)
                    q_wait_entry = f"""
                        SET TIMEZONE='posix/{TIME_ZONE}';
                        INSERT INTO wait_entry (date_time, wait_min, id_wait_session) VALUES
                        (date_trunc('minute', now()) ,{0},{id_wait_session});
                    """
                    query_postgre(q_wait_entry)
                else:
                    text = (
                        "Изменили ожидание "
                        f"{product} на {wait_min} {data['what_whale']}"
                    )
                    max_wait = item[3] if item[3] > wait_min else wait_min
                    q_update_session = f"""
                        UPDATE wait_session
                        SET max_wait = {max_wait}, now_wait = {wait_min}
                        WHERE id_wait_session = {id_wait_session}
                    """
                    query_postgre(q_update_session)
                    q_wait_entry = f"""
                        SET TIMEZONE='posix/{TIME_ZONE}';
                        INSERT INTO wait_entry (date_time, wait_min, id_wait_session)
                        VALUES (date_trunc('minute', now()) ,{wait_min},{id_wait_session});
                    """
                    query_postgre(q_wait_entry)
                break

    if len(open_sessions) == 0 or id_wait_session == 0:
        text = f"Поставили ожидание {product} на {wait_min} {data['what_whale']}"
        q_new_wait_session = f"""
            SET TIMEZONE='posix/{TIME_ZONE}';
            INSERT INTO wait_session (begin_wait, id_store, max_wait, product_name, now_wait)
            SELECT date_trunc('minute', now()), store.id_store, {wait_min}, '{product}',{wait_min}
            FROM store
            WHERE store.store_name = '{data['what_whale']}'
            RETURNING id_wait_session
        """
        id_wait_session = np.array(query_postgre(q_new_wait_session))[0, 0]
        q_wait_entry = f"""
            SET TIMEZONE='posix/{TIME_ZONE}';
            INSERT INTO wait_entry (date_time, wait_min, id_wait_session) VALUES
            (date_trunc('minute', now()) ,{wait_min},{id_wait_session});
        """
        query_postgre(q_wait_entry)

    await query.message.edit_text(text=text)
    await query.message.answer(
        text="вернулись в меню",
        reply_markup=await keyboard_start(data["id_user_chat"], state),
    )
    await query.bot.send_message(
        chat_id=TG_GROUP_NAMES[OPERATION_BM], text=text
    )
    await query.bot.send_message(
        chat_id=TG_GROUP_NAMES[CASHIER_TG], text=text
    )
    await state.clear()


@router.message(F.text == BUTTON_WAIT_CANCEL)
async def wait_cancel(message: Message, state: FSMContext) -> None:
    """Cancel waiting conversation."""

    data = await state.get_data()
    await message.answer(
        text="Стартовое меню",
        reply_markup=await keyboard_start(data.get("id_user_chat", message.chat.id), state),
    )
    await state.clear()


def conversation_waiting() -> Router:
    """Return router with waiting handlers."""

    return router