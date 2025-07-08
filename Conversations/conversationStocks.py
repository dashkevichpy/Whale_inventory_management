"""Conversation flow for stock operations."""

from __future__ import annotations

import gc
import logging
import os
from collections import namedtuple
from datetime import datetime
from enum import Enum
from typing import Union

import pytz
from aiogram import Router
from aiogram.enums import ParseMode
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from dotenv import load_dotenv
from tabulate import tabulate

from Conversations.conversationChooseWhale import reset_store_employee
from Whale_inventory_management.class_WhaleSheet import (
    ACCEPTANCE_SHEET_NAME,
    INVENT_SHEET_NAME,
    MORNING_INVENT_SHEET_NAME,
    InventSheet,
    WriteOffType,
    wr_off_init,
)
from Whale_inventory_management.invent_postgres import (
    pg_get_acceptance_whale_template,
    pg_get_invent_template,
    pg_insert_fake_write_off,
)
from Whale_inventory_management.report_and_check import (
    check_completed_invent,
    check_invent_acceptance_done,
    check_invent_done,
    check_invent_morning_done,
    check_write_off_done,
)
from class_StartKeyboard import Employee, keyboard_start
from decorators import check_group
from keyboards import (
    BUTTON_CANCEL_CONVERSATION,
    BUTTON_STOCKS,
    keyboard_cancel_conversation,
    keyboard_from_list,
)
from postgres import pg_get_employee_in_store


load_dotenv()
CHAT_TIMEOUT = int(os.getenv("CHAT_TIMEOUT"))
ERROR_ADMIN_ID = os.getenv("ERROR_ADMIN_ID")
TIME_ZONE = os.getenv("TIME_ZONE")
STOCK_CLOSING_START = os.getenv("STOCK_CLOSING_START")
STOCK_CLOSING_END = os.getenv("STOCK_CLOSING_END")


router = Router()


class StockState(StatesGroup):
    """Conversation states for stock operations."""

    dispatch = State()


BUTTON_INVENT = "🧮 отправить Инвентаризацию"
BUTTON_WRITE_OFF = "🗑 отправить Списание"
BUTTON_TMRR_WRITE_OFF = "📅 отравить Завтра списание"
BUTTON_MORNING_INVENT = "☀️отправить Утро инвент"
BUTTON_WRITE_OFF_REJECTION = "Нет списаний"
BUTTON_SHIPMENT_ACCEPTANCE = "📦 Принять транспортировку"


START_STOCK_EVENING_TIME = datetime.strptime(STOCK_CLOSING_START, "%H:%M:%S")
END_STOCK_EVENING_TIME = datetime.strptime(STOCK_CLOSING_END, "%H:%M:%S")
START_SHIPMENT_ACCEPTANCE_TIME = datetime.strptime("08:00:00", "%H:%M:%S")
END_SHIPMENT_ACCEPTANCE_TIME = datetime.strptime("15:00:00", "%H:%M:%S")
START_STOCK_MORNING_TIME = datetime.strptime("08:00:00", "%H:%M:%S")
END_STOCK_MORNING_TIME = datetime.strptime("11:00:00", "%H:%M:%S")


StockEvent = namedtuple("StockEvent", "button time_start time_end check_func")
StockKeyboardText = namedtuple("StockKeyboardText", "text keyboard")


class StockEventList(Enum):
    """Available events for stock dialog."""

    INVENT = StockEvent(
        BUTTON_INVENT, START_STOCK_EVENING_TIME, END_STOCK_EVENING_TIME, check_invent_done
    )
    WRITE_OFF = StockEvent(
        BUTTON_WRITE_OFF, START_STOCK_EVENING_TIME, END_STOCK_EVENING_TIME, check_write_off_done
    )
    TMRR_WRITE_OFF = StockEvent(
        BUTTON_TMRR_WRITE_OFF, START_STOCK_EVENING_TIME, END_STOCK_EVENING_TIME, None
    )
    WRITE_OFF_REJECTION = StockEvent(
        BUTTON_WRITE_OFF_REJECTION, START_STOCK_EVENING_TIME, END_STOCK_EVENING_TIME, None
    )
    SHIPMENT_ACCEPTANCE = StockEvent(
        BUTTON_SHIPMENT_ACCEPTANCE,
        START_SHIPMENT_ACCEPTANCE_TIME,
        END_SHIPMENT_ACCEPTANCE_TIME,
        check_invent_acceptance_done,
    )
    MORNING_INVENT = StockEvent(
        BUTTON_MORNING_INVENT,
        START_STOCK_MORNING_TIME,
        END_STOCK_MORNING_TIME,
        check_invent_morning_done,
    )


def event_now(empl: Employee) -> dict[str, bool]:
    """Return events available for employee at the moment."""

    now = datetime.now(tz=pytz.timezone(TIME_ZONE))
    buttons: dict[str, bool] = {}
    for event in StockEventList:
        add_button = False
        if event.value.time_start.time() > event.value.time_end.time():
            if now.time() >= event.value.time_start.time() or now.time() <= event.value.time_end.time():
                add_button = True
        elif event.value.time_start.time() <= now.time() <= event.value.time_end.time():
            add_button = True

        if add_button:
            buttons[event.value.button] = (
                event.value.check_func(empl) if event.value.check_func else True
            )

    return buttons


def keyboard_stock(employee: Employee) -> StockKeyboardText | None:
    """Return text and keyboard for available stock actions."""

    buttons = event_now(employee)
    if not buttons:
        return None

    text_header = f"Запасы для {employee.store_name}\n\n"
    text = ""

    if BUTTON_INVENT in buttons and buttons[BUTTON_INVENT]:
        del buttons[BUTTON_INVENT]
        text = "инвентаризация уже отправлена, доступны только списания"

    if BUTTON_WRITE_OFF in buttons and BUTTON_INVENT in buttons:
        if not buttons[BUTTON_WRITE_OFF] and not buttons[BUTTON_INVENT]:
            del buttons[BUTTON_INVENT]
            text = "отправьте списание"

    if BUTTON_WRITE_OFF in buttons and BUTTON_WRITE_OFF_REJECTION in buttons:
        if buttons[BUTTON_WRITE_OFF]:
            del buttons[BUTTON_WRITE_OFF_REJECTION]

    if BUTTON_SHIPMENT_ACCEPTANCE in buttons and buttons[BUTTON_SHIPMENT_ACCEPTANCE]:
        del buttons[BUTTON_SHIPMENT_ACCEPTANCE]

    if BUTTON_MORNING_INVENT in buttons and buttons[BUTTON_MORNING_INVENT]:
        del buttons[BUTTON_MORNING_INVENT]

    if not buttons:
        return None

    return StockKeyboardText(
        text=f"{text_header}{text}",
        keyboard=keyboard_from_list(list(buttons.keys()), 1),
    )


@router.message(F.text == BUTTON_STOCKS)
@check_group
async def start_stock_conversation(message: Message, state: FSMContext) -> None:
    """Entry point for stock actions."""

    await state.update_data(id_user_chat=message.chat.id)
    if not pg_get_employee_in_store(message.chat.id):
        await message.answer(
            text="Сначала выбери точку, где работаешь",
            reply_markup=await keyboard_start(message.chat.id, state),
        )
        await state.clear()
        return

    data = await state.get_data()
    employee: Employee = data["employee"]

    await message.answer(
        text=(
            f"Ты работаешь сегодня в\n<b>{employee.store_name}</b>?\n"
            "Если нет, то поменяй точку /reset_store"
        ),
        reply_markup=keyboard_cancel_conversation(),
        parse_mode=ParseMode.HTML,
    )

    stock_keyb = keyboard_stock(employee)
    if not stock_keyb:
        await message.answer(
            text="Нет доступных интервалов",
            reply_markup=await keyboard_start(message.chat.id, state),
        )
        await state.clear()
        return

    await message.answer(text=stock_keyb.text, reply_markup=stock_keyb.keyboard)
    await state.update_data(
        id_message_to_delete=[message.message_id + 1, message.message_id + 2],
        service_message=None,
    )
    await state.set_state(StockState.dispatch)


@router.callback_query(StockState.dispatch)
async def stock_dispatch_handler(query: CallbackQuery, state: FSMContext) -> None:
    """Handle stock operation selection."""

    await query.message.edit_text(text="⏳ обработка...")
    data = await state.get_data()
    employee: Employee = data["employee"]
    text = ""

    if query.data == BUTTON_INVENT:
        if check_invent_done(employee):
            await query.answer(text="❌ Инвентаризация уже внесена", show_alert=True)
            text = "\n❌ инвент внесена"
        else:
            invent_sheet = InventSheet(
                em=employee,
                sheet=INVENT_SHEET_NAME,
                func_get_nomenclature=pg_get_invent_template,
                invent_type=None,
            )
            if invent_sheet.get_result():
                await query.answer(text="🙌 Отлично, инвентаризация внесена", show_alert=True)
                text = "\n✔️инвент отправлен"
                incompleted = check_completed_invent()
                if incompleted:
                    table_inc = tabulate(incompleted, tablefmt="rst")
                    await query.bot.send_message(
                        chat_id=ERROR_ADMIN_ID,
                        text=(
                            "📨 Заполнили инвент {store_name} - {dept} осталось ещё \n {inc}".format(
                                store_name=employee.store_name,
                                dept=employee.department_code,
                                inc=table_inc,
                            )
                        ),
                    )
                else:
                    await query.bot.send_message(
                        chat_id=ERROR_ADMIN_ID, text="🎉 Все инвент заполнены"
                    )
            else:
                await query.answer(
                    text="❌ Что-то внесли не так🤨, смотри в колонке Ошибка заполнения",
                    show_alert=True,
                )
                text = "\n❌ ошибка инвент"
            del invent_sheet
            gc.collect()

    elif query.data == BUTTON_WRITE_OFF:
        write_off = wr_off_init(em=employee, write_off_type=WriteOffType.WRITE_OFF_TODAY, wb=None)
        result = write_off.get_result()
        if result is None:
            await query.answer(text="🙄 Нечего вносить в списание", show_alert=True)
            text = "\n - в списание нечего вносить"
        elif result:
            await query.answer(text="👍 Списание внесено", show_alert=True)
            text = "\n✔️списание за сегодня отправлено"
        else:
            await query.answer(
                text="❌ Ошибка в листе Списание, колонка Ошибка заполнения",
                show_alert=True,
            )
            text = "\n❌ ошибка списания"
        del write_off
        gc.collect()

    elif query.data == BUTTON_WRITE_OFF_REJECTION:
        pg_insert_fake_write_off(employee.id_store, employee.department_code)
        text = "\n⚠ списаний не было"

    elif query.data == BUTTON_TMRR_WRITE_OFF:
        text = f"\n\n {BUTTON_TMRR_WRITE_OFF} пока неактивно, запустим позже"

    elif query.data == BUTTON_SHIPMENT_ACCEPTANCE:
        invent_sheet = InventSheet(
            em=employee,
            sheet=ACCEPTANCE_SHEET_NAME,
            func_get_nomenclature=pg_get_acceptance_whale_template,
            invent_type="acceptance",
        )
        if invent_sheet.get_result():
            await query.answer(text="🙌 Приемка транспортировки внесена", show_alert=True)
            text = "\n✔️приемка отправлена"
            await query.bot.send_message(
                chat_id=ERROR_ADMIN_ID,
                text="📦 Приемка внесена {dept} - {store_name}.".format(
                    store_name=employee.store_name, dept=employee.department_code
                ),
            )
        else:
            await query.answer(
                text="❌ Что-то внесли не так🤨, смотри в колонке Ошибка заполнения",
                show_alert=True,
            )
            text = "\n❌ ошибка приемка"
        del invent_sheet
        gc.collect()

    elif query.data == BUTTON_MORNING_INVENT:
        invent_sheet = InventSheet(
            em=employee,
            sheet=MORNING_INVENT_SHEET_NAME,
            func_get_nomenclature=pg_get_acceptance_whale_template,
            invent_type="morning",
        )
        if invent_sheet.get_result():
            await query.answer(text="☀️Утро инвентаризация внесена", show_alert=True)
            text = "\n✔️утро инвентаризация внесена"
            await query.bot.send_message(
                chat_id=ERROR_ADMIN_ID,
                text="☀️Утро инвент внесена {dept} - {store_name}.".format(
                    store_name=employee.store_name, dept=employee.department_code
                ),
            )
        else:
            await query.answer(
                text="❌ Что-то внесли не так🤨, смотри в колонке Ошибка заполнения",
                show_alert=True,
            )
            text = "\n❌ ошибка утро инвентаризация"
        del invent_sheet
        gc.collect()

    else:
        await state.clear()
        return

    stock_keyb = keyboard_stock(employee)
    if not stock_keyb:
        await query.message.answer(
            text="Нет доступных интервалов",
            reply_markup=await keyboard_start(data["id_user_chat"], state),
        )
        await state.clear()
        return

    service_message = (query.message.text or "") + text
    await state.update_data(service_message=service_message)
    await query.message.edit_text(text=service_message, reply_markup=stock_keyb.keyboard)
    await state.set_state(StockState.dispatch)


async def _delete_service_messages(bot, user_id: int, message_ids: list[int]) -> None:
    for mes_id in message_ids:
        try:
            await bot.delete_message(chat_id=user_id, message_id=mes_id)
        except Exception:
            logging.error("Failed to delete service message")


async def _cancel_reply(
    sender: Union[Message, CallbackQuery], text: str, state: FSMContext
) -> None:
    data = await state.get_data()
    send: Message
    if isinstance(sender, CallbackQuery):
        send = sender.message
        await sender.answer()
    else:
        send = sender

    await send.answer(
        text=text,
        reply_markup=await keyboard_start(data["id_user_chat"], state),
    )
    await state.clear()


@router.message(F.text == BUTTON_CANCEL_CONVERSATION)
async def stock_cancel_message(message: Message, state: FSMContext) -> None:
    """Cancel stock dialog via message."""

    data = await state.get_data()
    await _delete_service_messages(message.bot, data.get("id_user_chat"), data.get("id_message_to_delete", []))
    await _cancel_reply(message, f"Прервали ,\n{BUTTON_STOCKS}\n\nВернулись в cтартовое меню", state)


@router.callback_query(F.data == BUTTON_CANCEL_CONVERSATION)
async def stock_cancel_callback(query: CallbackQuery, state: FSMContext) -> None:
    """Cancel stock dialog via callback."""

    data = await state.get_data()
    await _delete_service_messages(query.bot, data.get("id_user_chat"), data.get("id_message_to_delete", []))
    await _cancel_reply(query, f"Прервали ,\n{BUTTON_STOCKS}\n\nВернулись в cтартовое меню", state)


@router.callback_query(F.data == "timeout")
async def stock_timeout_callback(query: CallbackQuery, state: FSMContext) -> None:
    """Handle callback timeout."""

    await query.message.edit_text(text=f"Прервали ,\n{BUTTON_STOCKS} - не было активностей")
    await _cancel_reply(query, "Вернулись в стартовое меню", state)


@router.message(F.text == "timeout")
async def stock_timeout_message(message: Message, state: FSMContext) -> None:
    """Handle message timeout."""

    data = await state.get_data()
    await _delete_service_messages(message.bot, data.get("id_user_chat"), data.get("id_message_to_delete", []))
    await _cancel_reply(message, f"Прервали ,\n{BUTTON_STOCKS} - не было активностей", state)


@router.message(F.text == "/reset_store")
async def stock_reset_store(message: Message, state: FSMContext) -> None:
    """Reset current store assignment."""

    data = await state.get_data()
    await _delete_service_messages(message.bot, data.get("id_user_chat"), data.get("id_message_to_delete", []))
    await reset_store_employee(message, state)


def conversation_stocks() -> Router:
    """Return router with stock handlers."""

    return router