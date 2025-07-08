import logging
from collections import namedtuple
from datetime import datetime, timedelta

import pytz
from dotenv import load_dotenv
import os

load_dotenv()
TIME_ZONE = os.getenv('TIME_ZONE')

from class_StartKeyboard import keyboard_start

from keyboards import keyboard_accept_read, keyboard_remind, NOTIFICATION_SEPARATOR_SYMBOL
from postgres import pgre_employee_dept_in_store, pg_insert_send_notification, pg_update_send_notification_press_button, \
    pg_get_send_notification_by_id, pgre_get_employee_by_tel_id, pg_store, pgre_active_notifications

NotifMessage = namedtuple('NotifMessage', {'id_department', 'id_notification', 'type', 'notification_text',
                                           'notification_date', 'weekdays', 'stores', 'notification_time',
                                           'minutes_to_do', 'department_name', 'department_code',
                                           'group_id_telegram'})




# errr = pgre_active_notifications(NotifMessage)
# print(errr)



def time_to_utc(date_time: datetime, time_zone: str):
    local = pytz.timezone(time_zone)
    local_dt = local.localize(date_time, is_dst=None)
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt


def check_notification(context):
    n = context.job.context
    # context_data = {
    #     'id_send_notification': id_send_notification,
    #     'notification_text': notification.notification_text,
    #     'id_store': store,
    #     'department_code': notification.department_code,
    #     'group_id_telegram': notification.group_id_telegram,
    #     'employee_tel_id': tel_id
    # }
    notification_send = pg_get_send_notification_by_id(n['id_send_notification'])
    # [{'id_send_notification': 12, 'id_notification': 2, 'id_employee': 145,
    #   'datetime_send': datetime.datetime(2022, 9, 3, 18, 51), 'datetime_press_button': None}]
    if not notification_send:  # не нашли сообщения
        return

    if not notification_send['datetime_press_button']:
        empl = pgre_get_employee_by_tel_id(tel_id=n['employee_tel_id'])
        store_name = pg_store(id_store=n['id_store'])['store_name']
        context.bot.sendMessage(chat_id=n['group_id_telegram'],
                                text=f"📯 {store_name} {n['department_code']} \n"
                                     f"сотрудник {empl['tel_username']} - {empl['tel_first_name']} - {empl['tel_last_name']}"
                                     f" не сделано/не прочитано сообщение \n"
                                     f"{n['notification_text']}",
                                reply_markup=None)


def notification_in_store(context):
    notification = NotifMessage(*context.job.context)
    logging.info(f'Отправляем напоминания {notification}')
    for store in notification.stores:
        tel_id_list = pgre_employee_dept_in_store(id_dept=notification.id_department, id_store=store)
        # tel_id_list = [5174907351, 189198380]
        if not tel_id_list:  # нет сотрудников прикрепленных к точке
            context.bot.sendMessage(chat_id=notification.group_id_telegram,
                                    text=f"📯 Хотели отправить {notification.notification_text} \n"
                                         f"но в {store} нет никого из {notification.department_name}")
            return

        for tel_id in tel_id_list:
            try:
                logging.info(f'Отправка напоминания {notification} в КИТе {store} для {tel_id}')
                # создаем запись об отправке сообщения
                id_send_notification = pg_insert_send_notification(id_notification=notification.id_notification,
                                                                   employee_tlgr=tel_id,
                                                                   time_zone=TIME_ZONE)
                context.bot.sendMessage(chat_id=tel_id,
                                        text=f"📨 {notification.notification_text} \n",
                                        reply_markup=keyboard_remind(id_notification=id_send_notification))
                # если поствлено время, через которое проверить заполнение
                if notification.minutes_to_do:
                    date_time = context.job.next_t + timedelta(minutes=notification.minutes_to_do)

                    context_data = {
                        'id_send_notification': id_send_notification,
                        'notification_text': notification.notification_text,
                        'id_store': store,
                        'department_code': notification.department_code,
                        'group_id_telegram': notification.group_id_telegram,
                        'employee_tel_id': tel_id
                    }

                    context.job_queue.run_once(callback=check_notification, when=date_time,
                                               context=context_data)
            except Exception as e:
                logging.error(f'ошибка отправки notification {store} -- {tel_id} - {notification} error - {str(e)}')


def mark_read_notification(update, context) -> None:
    query = update.callback_query
    id_notification = query.data.split(NOTIFICATION_SEPARATOR_SYMBOL)[0]
    query.answer(text='📭 прочитано')
    try:
        # отмечаем, что нажали кнопку
        pg_update_send_notification_press_button(id_send_notification=int(id_notification), time_zone=TIME_ZONE)
        query.edit_message_text(
            text='📭 сделано|прочтено:\n' + query.message.text,

        )
        update.effective_message.reply_text(
            text='Вернулись в меню',
            reply_markup=keyboard_start(update.effective_message.chat_id, context)
        )
    except Exception as e:
        logging.error(f'ошибка mark_read_notification {query.data}  error - {str(e)}')

