from __future__ import annotations

import os
from typing import Any

import numpy as np
from aiogram import Router
from aiogram.enums import ParseMode
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv

from Conversations.conversationWaiting import PRODUCT_NAME_WAITING
from class_StartKeyboard import keyboard_start
from decorators import check_group
from keyboards import (
    BUTTON_DELIVERY_WAIT,
    BUTTON_DELIVERY_WAIT_CANCEL,
    CALLBCK_WRONG_BT_MIN_DELV_WAIT,
    CALLBCK_WRONG_BT_WHALE_DELV_WAIT,
    MARKER_WAIT_DELIVERY_WAIT,
    OPEN_SESSION_DELIVERY_WAIT,
    keyboard_cancel_delivery_wait,
    keyboard_delivery_wait,
)
from postgres import query_postgre

load_dotenv()

router = Router()

INPUT_DELIVERY_MIN = "⏰"
DELIVERY_WAIT_MINUTES = ["30", "60", "90", INPUT_DELIVERY_MIN]
TG_NOTIFY_GROUP_ID = 189198380


class DeliveryWaitState(StatesGroup):
    """Conversation states for delivery waiting."""

    write_wait = State()
    input_time = State()


@router.message(Text(BUTTON_DELIVERY_WAIT))
@check_group
async def delivery_wait_start(message: Message, state: FSMContext) -> None:
    """Start delivery waiting conversation."""

    await state.update_data(id_user_chat=message.chat.id, tg_notify=TG_NOTIFY_GROUP_ID)

    query_open = """
        SELECT store_name, now_wait, product_name
        FROM wait_session
        INNER JOIN store USING(id_store)
        WHERE end_wait IS NULL
        ORDER BY store_name
    """
    now_wait = np.array(query_postgre(query_open))

    query_store = """
        SELECT store_name, basic_delivery_time
        FROM store
        WHERE delivery = TRUE
        ORDER BY store_name
    """
    delivery_store = np.array(query_postgre(query_store))
    delivery_now_wait: list[Any] | np.ndarray = []
    if now_wait.size > 0:
        delivery_now_wait = now_wait[np.where(now_wait[:, 2] == PRODUCT_NAME_WAITING[2])][:, [0, 1]]

    await state.update_data(store_list=delivery_store, current_text="")

    await message.answer(
        text=f"<pre>Выбрали {BUTTON_DELIVERY_WAIT}</pre>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_cancel_delivery_wait(),
    )
    await message.answer(
        text=(
            "<pre>поменять ожидание (в мин.):\n"
            "чтобы убрать ожидание с точки - нажмите на нее \n</pre>"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_delivery_wait(
            delivery_now_wait, delivery_store[:, 0], DELIVERY_WAIT_MINUTES
        ),
    )
    await state.set_state(DeliveryWaitState.write_wait)


@router.callback_query(DeliveryWaitState.write_wait)
async def callback_keyboard_processing(query: CallbackQuery, state: FSMContext) -> None:
    """Process inline keyboard callbacks."""

    data = await state.get_data()
    current_text = data.get("current_text", query.message.text or "")
    callback_data = query.data

    if callback_data == CALLBCK_WRONG_BT_WHALE_DELV_WAIT:
        await query.answer("Выбрать ожидание, а не точку", show_alert=True)
        return

    if callback_data == CALLBCK_WRONG_BT_MIN_DELV_WAIT:
        await query.answer("Ожидание уже выставлено", show_alert=True)
        return

    text = ""
    if callback_data.split()[0] == OPEN_SESSION_DELIVERY_WAIT:
        store_name = callback_data.split()[1]
        await state.update_data(choose_store=store_name)

        if callback_data.split()[2] == INPUT_DELIVERY_MIN:
            await query.message.edit_text(
                text=f"{store_name} - выставите время в мин от 90 до 240",
                parse_mode=ParseMode.HTML,
            )
            await state.set_state(DeliveryWaitState.input_time)
            return

        now_wait = int(callback_data.split()[2])
        query_wait = f"""
            SELECT max_wait, id_wait_session
            FROM wait_session
            INNER JOIN store USING(id_store)
            WHERE end_wait IS NULL AND product_name = '{PRODUCT_NAME_WAITING[2]}' AND store_name = '{store_name}'
        """
        session = np.array(query_postgre(query_wait))[0]
        id_wait_session = session[1]
        session_wait_max = session[0]
        max_wait = session_wait_max if session_wait_max > now_wait else now_wait
        q_update = f"""
            UPDATE wait_session
            SET max_wait = {max_wait}, now_wait = {now_wait}
            WHERE id_wait_session = {id_wait_session}
        """
        query_postgre(q_update)
        q_entry = f"""
            SET TIMEZONE='posix/Asia/Krasnoyarsk';
            INSERT INTO wait_entry (date_time, wait_min, id_wait_session)
            VALUES (date_trunc('minute', now()) ,{now_wait},{id_wait_session});
        """
        query_postgre(q_entry)
        text = f"\n⭕ изменили ожидание доставки в <b>{store_name}</b> ➔ {now_wait}\n"

    elif callback_data.split()[0] == MARKER_WAIT_DELIVERY_WAIT:
        store_name = callback_data.split()[1]
        q_close = f"""
            SET TIMEZONE='posix/Asia/Krasnoyarsk';
            UPDATE wait_session
            SET end_wait = date_trunc('minute', now()),
                duration_wait = date_trunc('minute', (NOW() - begin_wait)),
                now_wait = 0
            WHERE (
                SELECT id_store FROM store WHERE store_name = '{store_name}'
            ) = id_store AND end_wait IS NULL AND product_name = '{PRODUCT_NAME_WAITING[2]}'
            RETURNING id_wait_session
        """
        id_wait_session = np.array(query_postgre(q_close))[0][0]
        q_entry = f"""
            SET TIMEZONE='posix/Asia/Krasnoyarsk';
            INSERT INTO wait_entry (date_time, wait_min, id_wait_session) VALUES
            (date_trunc('minute', now()) ,0,{id_wait_session});
        """
        query_postgre(q_entry)
        text = f"\n🔆 в {store_name} нет ожиданий \n"

    else:
        store_name, wait_min = callback_data.split()
        if wait_min == INPUT_DELIVERY_MIN:
            await state.update_data(choose_store=store_name)
            await query.message.edit_text(
                text=f"{store_name} - выставите время в мин от 90 до 240",
                parse_mode=ParseMode.HTML,
            )
            await state.set_state(DeliveryWaitState.input_time)
            return

        q_new_session = f"""
            SET TIMEZONE='posix/Asia/Krasnoyarsk';
            INSERT INTO wait_session (begin_wait, id_store, max_wait, product_name, now_wait)
            SELECT date_trunc('minute', now()), store.id_store, {wait_min}, '{PRODUCT_NAME_WAITING[2]}',{wait_min}
            FROM store
            WHERE store.store_name = '{store_name}'
            RETURNING id_wait_session
        """
        id_wait_session = np.array(query_postgre(q_new_session))[0][0]
        q_entry = f"""
            SET TIMEZONE='posix/Asia/Krasnoyarsk';
            INSERT INTO wait_entry (date_time, wait_min, id_wait_session) VALUES
            (date_trunc('minute', now()) ,{wait_min},{id_wait_session});
        """
        query_postgre(q_entry)
        text = (
            f"\n❗️Поставили ожидание {PRODUCT_NAME_WAITING[2]} {wait_min} мин в {store_name}\n"
        )

    query_wait = f"""
        SELECT store_name, now_wait, product_name
        FROM wait_session
        INNER JOIN store USING(id_store)
        WHERE end_wait IS NULL AND product_name = '{PRODUCT_NAME_WAITING[2]}'
        ORDER BY store_name
    """
    delivery_now_wait = np.array(query_postgre(query_wait))
    delivery_store = np.array(data["store_list"])

    await query.bot.send_message(
        chat_id=data["tg_notify"], text=text, parse_mode=ParseMode.HTML
    )

    new_text = current_text + text
    await state.update_data(current_text=new_text)

    await query.message.edit_text(
        text=new_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_delivery_wait(
            delivery_now_wait, delivery_store[:, 0], DELIVERY_WAIT_MINUTES
        ),
    )
    await state.set_state(DeliveryWaitState.write_wait)


@router.message(Text(BUTTON_DELIVERY_WAIT_CANCEL))
async def delivery_wait_cancel(message: Message, state: FSMContext) -> None:
    """Finish conversation and show start keyboard."""

    data = await state.get_data()
    await message.answer(
        text="Ожидания выставлены",
        reply_markup=await keyboard_start(data.get("id_user_chat"), state),
    )
    await state.clear()


@router.message(DeliveryWaitState.input_time)
async def input_delivery_time(message: Message, state: FSMContext) -> None:
    """Handle manual time input."""

    if not message.text.isnumeric():
        await message.answer("это не число")
        return

    now_wait = int(message.text)
    data = await state.get_data()
    store_name = data.get("choose_store")

    query_wait = f"""
        SELECT max_wait, id_wait_session
        FROM wait_session
        INNER JOIN store USING(id_store)
        WHERE end_wait IS NULL AND product_name = '{PRODUCT_NAME_WAITING[2]}' AND store_name = '{store_name}'
    """
    session = np.array(query_postgre(query_wait))
    if session.size > 0:
        session = session[0]
        id_wait_session = session[1]
        session_wait_max = session[0]
        max_wait = session_wait_max if session_wait_max > now_wait else now_wait
        q_update = f"""
            UPDATE wait_session
            SET max_wait = {max_wait}, now_wait = {now_wait}
            WHERE id_wait_session = {id_wait_session}
        """
        query_postgre(q_update)
        q_entry = f"""
            SET TIMEZONE='posix/Asia/Krasnoyarsk';
            INSERT INTO wait_entry (date_time, wait_min, id_wait_session)
            VALUES (date_trunc('minute', now()) ,{now_wait},{id_wait_session});
        """
        query_postgre(q_entry)
    else:
        q_new_session = f"""
            SET TIMEZONE='posix/Asia/Krasnoyarsk';
            INSERT INTO wait_session (begin_wait, id_store, max_wait, product_name, now_wait)
            SELECT date_trunc('minute', now()), store.id_store, {now_wait}, '{PRODUCT_NAME_WAITING[2]}',{now_wait}
            FROM store
            WHERE store.store_name = '{store_name}'
            RETURNING id_wait_session
        """
        id_wait_session = np.array(query_postgre(q_new_session))[0][0]
        q_entry = f"""
            SET TIMEZONE='posix/Asia/Krasnoyarsk';
            INSERT INTO wait_entry (date_time, wait_min, id_wait_session) VALUES
            (date_trunc('minute', now()) ,{now_wait},{id_wait_session});
        """
        query_postgre(q_entry)

    query_sessions = """
        SELECT store_name, now_wait, product_name
        FROM wait_session
        INNER JOIN store USING(id_store)
        WHERE end_wait IS NULL
        ORDER BY store_name
    """
    wait_sessions = np.array(query_postgre(query_sessions))
    delivery_now_wait: list[Any] | np.ndarray = []
    if wait_sessions.size > 0:
        delivery_now_wait = wait_sessions[np.where(wait_sessions[:, 2] == PRODUCT_NAME_WAITING[2])][:, [0, 1]]
    delivery_store = np.array(data["store_list"])

    text = f"\n⭕ изменили ожидание доставки в <b>{store_name}</b> ➔ {now_wait}\n"
    current_text = data.get("current_text", "") + text
    await state.update_data(current_text=current_text)

    await message.answer(
        text=current_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_delivery_wait(
            delivery_now_wait, delivery_store[:, 0], DELIVERY_WAIT_MINUTES
        ),
    )
    await message.bot.send_message(
        chat_id=data.get("tg_notify"), text=text, parse_mode=ParseMode.HTML
    )
    await state.set_state(DeliveryWaitState.write_wait)


def conversation_delivery_waiting() -> Router:
    """Return router with delivery waiting handlers."""

    return router