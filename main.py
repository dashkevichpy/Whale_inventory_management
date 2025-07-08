from datetime import datetime, date, time

import pytz
from telegram import Update
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, InlineQueryHandler, CallbackQueryHandler
from telegram.ext import CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler

from Conversations.conversationChooseWhale import conversation_choose_whale, reset_store_employee
from Conversations.conversationDeliveryWaiting import conversation_delivery_waiting, delivery_delay_look
from Conversations.conversationRegister import conversation_register
from Conversations.conversationStocks import conversation_stocks
from Conversations.conversationStoplist import BUTTON_STOP_START, stoplist_dispatch, add_stop_list, remove_stop_list, \
    StopButtonList, add_stop_handler, remove_stop_handler
from Conversations.conversationTransfer import transfer
from Conversations.conversationWaiting import conversation_waiting
from Whale_inventory_management.class_WhaleSheet import AllSheetInvent, INVENT_SHEET_NAME, update_invent_sheets, \
    update_write_off_sheets, update_acceptance_sheets, update_morning_invent_sheets
from Whale_inventory_management.invent_postgres import pg_get_invent_template
from class_StartKeyboard import keyboard_start
from dotenv import load_dotenv
import os

load_dotenv()
ERROR_ADMIN_ID = int(os.getenv('ERROR_ADMIN_ID'))
TIME_ZONE = os.getenv('TIME_ZONE')

# TODO: логгирование
# https://www.youtube.com/watch?v=Wg6brhq647Q&list=PLkeGs_OdUTP-uXDyLdCrn0yJeqsVAAjhY&index=5
# TODO: deploy
#  заменить токен бота
#  проверить чат таймаут
#
#
#z  z

from Conversations.conversationErrors import add_observer_error
from Conversations.conversationBreak import add_observer_broken
from configs import TG_TOKEN
from decorators import check_group
from keyboards import BUTTON_DELIVERY_TIME_WATCH, BUTTON_NOTIFICATION_REMIND_CALLBACK, keyboard_remind, \
    NOTIFICATION_SEPARATOR_SYMBOL
from notifications import time_to_utc, notification_in_store, notification_in_store, \
    mark_read_notification, NotifMessage
from postgres import del_emloyee_assignment, end_day_stop, end_day_wait, pgre_active_notifications
import logging


UPDATER_TELEGRAM = Updater(token=TG_TOKEN, use_context=True)

@check_group
def start(update, context):
    update.message.reply_text(
        text="Привет, {}!".format(update.message.from_user.first_name),
        reply_markup=keyboard_start(update.message.chat_id, context)
    )


# effective_message - {'message_id': 9, 'date': 1676671251, 'chat': {'id': -1001540992877, 'type': 'supergroup', 'title': 'Ошибки БМ Кассиры'}, 'reply_to_message': {'message_id': 3, 'date': 1676670863, 'chat': {'id': -1001540992877, 'type': 'supergroup', 'title': 'Ошибки БМ Кассиры'}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 189198380, 'first_name': 'Anton', 'is_bot': False, 'last_name': 'Sukhanov', 'username': 'sukhanovanton', 'language_code': 'ru'}}, 'text': '/start@kit_kras_bot', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 19}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 189198380, 'first_name': 'Anton', 'is_bot': False, 'last_name': 'Sukhanov', 'username': 'sukhanovanton', 'language_code': 'ru'}}
# message - {'message_id': 9, 'date': 1676671251, 'chat': {'id': -1001540992877, 'type': 'supergroup', 'title': 'Ошибки БМ Кассиры'}, 'reply_to_message': {'message_id': 3, 'date': 1676670863, 'chat': {'id': -1001540992877, 'type': 'supergroup', 'title': 'Ошибки БМ Кассиры'}, 'entities': [], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 189198380, 'first_name': 'Anton', 'is_bot': False, 'last_name': 'Sukhanov', 'username': 'sukhanovanton', 'language_code': 'ru'}}, 'text': '/start@kit_kras_bot', 'entities': [{'type': 'bot_command', 'offset': 0, 'length': 19}], 'caption_entities': [], 'photo': [], 'new_chat_members': [], 'new_chat_photo': [], 'delete_chat_photo': False, 'group_chat_created': False, 'supergroup_chat_created': False, 'channel_chat_created': False, 'from': {'id': 189198380, 'first_name': 'Anton', 'is_bot': False, 'last_name': 'Sukhanov', 'username': 'sukhanovanton', 'language_code': 'ru'}}

# effective_chat  -  {'id': -1001540992877, 'type': 'supergroup', 'title': 'Ошибки БМ Кассиры'}

def end_day(update, context):
    if update.message.chat_id == ERROR_ADMIN_ID:
        del_emloyee_assignment() #  удаляем сотрудников
        end_day_stop()  # очищаем стопы
        end_day_wait()
        update.message.reply_text(
            text="День закрыт",
            reply_markup=keyboard_start(update.message.chat_id, context)
        )
    else:
        update.message.reply_text(
            text="нет доступа",
            reply_markup=keyboard_start(update.message.chat_id, context)
        )


def closing_day():
    logging.info('closing_day\n')
    del_emloyee_assignment()  # удаляем сотрудников
    end_day_stop()
    end_day_wait()


def main():
    updater = UPDATER_TELEGRAM
    dispatcher = updater.dispatcher
    start_handler = CommandHandler('start', start)
    end_day_handler = CommandHandler('end_day', end_day)
    change_store = CommandHandler('reset_store', reset_store_employee)
    notification_handler = CallbackQueryHandler(mark_read_notification,
                                                pattern='(\d+|^)[' + NOTIFICATION_SEPARATOR_SYMBOL + ']' +
                                                        BUTTON_NOTIFICATION_REMIND_CALLBACK + '$')

    # посмотреть ожидания в КИТах
    dispatcher.add_handler(MessageHandler(Filters.regex(BUTTON_DELIVERY_TIME_WATCH), delivery_delay_look))

    # STOPlIST
    dispatcher.add_handler(MessageHandler(Filters.regex(BUTTON_STOP_START), stoplist_dispatch))
    dispatcher.add_handler(InlineQueryHandler(callback=add_stop_list,
                                              pattern=StopButtonList.BUTTON_ADD_STOP.value.code_inline))
    dispatcher.add_handler(InlineQueryHandler(callback=remove_stop_list,
                                              pattern=StopButtonList.BUTTON_REMOVE_STOP.value.code_inline))

    dispatcher.add_handler(MessageHandler(Filters.regex('^'+StopButtonList.BUTTON_ADD_STOP.value.code_split)
                                          & Filters.via_bot(username='@'+updater.bot.username), add_stop_handler))

    dispatcher.add_handler(MessageHandler(Filters.regex('^' + StopButtonList.BUTTON_REMOVE_STOP.value.code_split)
                                          & Filters.via_bot(username='@' + updater.bot.username), remove_stop_handler))

    add_observer_broken(dispatcher)
    add_observer_error(dispatcher)
    conversation_choose_whale(dispatcher)
    conversation_waiting(dispatcher)
    conversation_delivery_waiting(dispatcher)

    transfer(dispatcher)
    conversation_register(dispatcher)
    conversation_stocks(dispatcher)
    dispatcher.add_handler(change_store)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(end_day_handler)
    dispatcher.add_handler(notification_handler)

    updater.start_polling()
    updater.idle()


def get_job_queue() -> None:
    notifications = pgre_active_notifications(NotifMessage)
    # notifications = [{
    #     'id_notification': 2,
    #     'type': 'remind',
    #                  'id_department': 2,
    #                  'notification_text': 'это и то',
    #                  'notification_date': date(2022, 9, 6),
    #                  'weekdays': None,
    #                  'stores': [3, 2],
    #                  'is_done': False,
    #                  'notification_time': time(hour=13, minute=53),
    #                  'minutes_to_do': 1,
    #                   'department_name': 'БМ_ПМ',
    #                   'department_code': 'BM',
    #                  'invent_col': 'invent_bm',
    #                  'group_id_telegram': '189198380'
    #                   }]
    if not notifications:
        return

    job = UPDATER_TELEGRAM.job_queue
    today = datetime.now(tz=pytz.timezone(TIME_ZONE))
    for n in notifications:
        logging.info(f'Постановка напоминания {n}')

        if n.type == 'remind':
            # блок проверки - ставить или нет в очередь job
            if n.weekdays:  # если событие повторяется
                if (today.date() >= n.notification_date) and (today.weekday()+1 in n.weekdays):
                    date_time = datetime(today.year, today.month, today.day, n.notification_time.hour,
                                         n.notification_time.minute)
                else:
                    continue
            else:  # если событие не повторяется
                if today.date() == n.notification_date:
                    date_time = datetime(n.notification_date.year, n.notification_date.month,
                                         n.notification_date.day, n.notification_time.hour,
                                         n.notification_time.minute)
                else:
                    continue

            date_time = time_to_utc(date_time=date_time, time_zone="Asia/Krasnoyarsk")
            logging.info(f'Создаем напоминания -{n} \n')
            job.run_once(callback=notification_in_store, when=date_time, context=n)
        elif n.type == 'standart':
            # отправляем всем сотрудникам department вне зависимости от пристутствия на точки?
            pass
        else:
            raise ValueError('incorrect notification type')


def set_scheduler() -> None:
    # ставим ежедневное обновление напоминаний
    sched = BackgroundScheduler(timezone="Asia/Krasnoyarsk")
    sched.add_job(get_job_queue, 'cron', day='*', hour='13', minute='30')  # срабатывание не позже 8:30
    sched.add_job(closing_day, 'cron', day='*', hour='01', minute='30')
    sched.add_job(update_invent_sheets, 'cron', day='*', hour='12', minute='55')
    sched.add_job(update_write_off_sheets, 'cron', day='*', hour='12', minute='56')
    sched.add_job(update_acceptance_sheets, 'cron', day='*', hour='04', minute='10')
    sched.add_job(update_morning_invent_sheets, 'cron', day='*', hour='04', minute='15')
    sched.start()

    # sched.add_job(get_job_queue, 'cron', day='*', hour='07', minute='20')  # срабатывание не позже 8:30
    # sched.add_job(closing_day, 'cron', day='*', hour='01', minute='30')
    # sched.add_job(update_invent_sheets, 'cron', day='*', hour='06', minute='40')
    # sched.add_job(update_write_off_sheets, 'cron', day='*', hour='06', minute='50')
    # sched.add_job(update_acceptance_sheets, 'cron', day='*', hour='07', minute='05')
    # sched.add_job(update_morning_invent_sheets, 'cron', day='*', hour='07', minute='15')
    # sched.start()



if __name__ == '__main__':
    # set_scheduler()
    main()
    # update_invent_sheets()
