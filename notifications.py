"""Utility functions for sending notifications."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import List, Optional

import pytz
from aiogram import Bot
from aiogram.types import CallbackQuery
from dotenv import load_dotenv

from class_StartKeyboard import keyboard_start
from keyboards import NOTIFICATION_SEPARATOR_SYMBOL, keyboard_remind
from postgres import (
    pg_get_send_notification_by_id,
    pg_insert_send_notification,
    pg_store,
    pg_update_send_notification_press_button,
    pgre_employee_dept_in_store,
    pgre_get_employee_by_tel_id,
)

load_dotenv()
TIME_ZONE = os.getenv("TIME_ZONE")


@dataclass
class NotifMessage:
    """Data required to send notification."""

    id_department: int
    id_notification: int
    type: str
    notification_text: str
    notification_date: date
    weekdays: Optional[List[int]]
    stores: List[int]
    notification_time: time
    minutes_to_do: Optional[int]
    department_name: str
    department_code: str
    group_id_telegram: int




def time_to_utc(date_time: datetime, time_zone: str) -> datetime:
    """Return ``date_time`` converted from ``time_zone`` to UTC."""

    local = pytz.timezone(time_zone)
    local_dt = local.localize(date_time, is_dst=None)
    return local_dt.astimezone(pytz.utc)


async def check_notification(bot: Bot, data: dict) -> None:
    """Check that employee reacted to notification and remind if needed."""

    notification_send = pg_get_send_notification_by_id(
        data["id_send_notification"]
    )
    if not notification_send:
        return

    if notification_send["datetime_press_button"]:
        return

    empl = pgre_get_employee_by_tel_id(tel_id=data["employee_tel_id"])
    store_name = pg_store(id_store=data["id_store"])["store_name"]
    text = (
        f"📯 {store_name} {data['department_code']} \n"
        f"сотрудник {empl['tel_username']} - {empl['tel_first_name']} - "
        f"{empl['tel_last_name']}\n"
        f"не сделано/не прочитано сообщение \n"
        f"{data['notification_text']}"
    )
    await bot.send_message(chat_id=data["group_id_telegram"], text=text)


async def _check_later(bot: Bot, data: dict, delay: int) -> None:
    """Sleep ``delay`` seconds and run :func:`check_notification`."""

    await asyncio.sleep(delay)
    await check_notification(bot, data)


async def notification_in_store(bot: Bot, notification: NotifMessage) -> None:
    """Send notification to employees in specified stores."""

    logging.info("Отправляем напоминания %s", notification)

    for store in notification.stores:
        tel_id_list = pgre_employee_dept_in_store(
            id_dept=notification.id_department, id_store=store
        )
        if not tel_id_list:
            await bot.send_message(
                chat_id=notification.group_id_telegram,
                text=(
                    f"📯 Хотели отправить {notification.notification_text} \n"
                    f"но в {store} нет никого из "
                    f"{notification.department_name}"
                ),
            )
            return

        for tel_id in tel_id_list:
            try:
                logging.info(
                    "Отправка напоминания %s в КИТе %s для %s",
                    notification,
                    store,
                    tel_id,
                )
                id_send_notification = pg_insert_send_notification(
                    id_notification=notification.id_notification,
                    employee_tlgr=tel_id,
                    time_zone=TIME_ZONE,
                )
                await bot.send_message(
                    chat_id=tel_id,
                    text=f"📨 {notification.notification_text} \n",
                    reply_markup=keyboard_remind(
                        id_notification=id_send_notification
                    ),
                )

                if notification.minutes_to_do:
                    context_data = {
                        "id_send_notification": id_send_notification,
                        "notification_text": notification.notification_text,
                        "id_store": store,
                        "department_code": notification.department_code,
                        "group_id_telegram": notification.group_id_telegram,
                        "employee_tel_id": tel_id,
                    }

                    asyncio.create_task(
                        _check_later(
                            bot, context_data, notification.minutes_to_do * 60
                        )
                    )
            except Exception as e:
                logging.error(
                    "ошибка отправки notification %s -- %s - %s error - %s",
                    store,
                    tel_id,
                    notification,
                    str(e),
                )


async def mark_read_notification(query: CallbackQuery, bot: Bot) -> None:
    """Mark notification as read when user presses the button."""

    id_notification = query.data.split(NOTIFICATION_SEPARATOR_SYMBOL)[0]
    await query.answer(text="📭 прочитано")
    try:
        pg_update_send_notification_press_button(
            id_send_notification=int(id_notification), time_zone=TIME_ZONE
        )
        await query.message.edit_text(
            text="📭 сделано|прочтено:\n" + query.message.text
        )
        await bot.send_message(
            chat_id=query.message.chat.id,
            text="Вернулись в меню",
            reply_markup=keyboard_start(query.message.chat.id, None),
        )
    except Exception as e:
        logging.error(
            "ошибка mark_read_notification %s  error - %s",
            query.data,
            str(e),
        )
