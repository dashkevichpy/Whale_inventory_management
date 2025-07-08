import numpy as np
from telegram import ParseMode
from telegram.ext import ConversationHandler, MessageHandler, CallbackQueryHandler, Filters
import time

from class_StartKeyboard import keyboard_start
import os
from dotenv import load_dotenv

load_dotenv()
ERROR_ADMIN_ID = os.getenv('ERROR_ADMIN_ID')
TG_GROUP_NAMES = eval(os.getenv('TG_GROUP_NAMES'))
OPERATION_BM = os.getenv('OPERATION_BM')
CASHIER_TG = os.getenv('CASHIER_TG')
CHAT_TIMEOUT = int(os.getenv('CHAT_TIMEOUT'))
from decorators import check_group
from keyboards import BUTTON_WHAT_WHALE, keyboard_cancel_choose_whale, keyboard_from_list, BUTTON_CHOOSE_WHALE_CANCEL, \
    BUTTON_WAIT_TITLE, keyboard_cancel_wait, BUTTON_WAIT_CANCEL, BUTTON_REMOVE_WAIT
from postgres import query_postgre
import logging
logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

ID_USER_CHAT, WHAT_WHALE, OPEN_SESSIONS, WAIT = range(4)
WRITE_WAIT = range(1)

WAIT_MINUTES = ['15', '20', '30', '45']
# PRODUCT_NAME = ['🍕', '🍔']
PRODUCT_NAME_WAITING = ['🍕', '🍔', '🚚']
PRODUCT_NAME = PRODUCT_NAME_WAITING[0:2]


@check_group
def wait_start(update, context):
    context.user_data[ID_USER_CHAT] = update.message.chat_id
    query_db = """SELECT store_name
                            FROM employee_in_store
                            INNER JOIN store USING(id_store)
                            WHERE chat_id_telegram = '{}'
                    """.format(context.user_data[ID_USER_CHAT])
    whale_store = np.array(query_postgre(query_db))
    if whale_store.size > 0:
        context.user_data[WHAT_WHALE] = whale_store[0, 0]
        update.effective_message.reply_text(
            text='Выбрали \n' + BUTTON_WAIT_TITLE,
            reply_markup=keyboard_cancel_wait(),
        )

        #  create buttons
        buttons_wait = []
        for i in WAIT_MINUTES:
            for j in PRODUCT_NAME:
                cur = i + " " + j
                buttons_wait.append(cur)

        query_db = '''
            SELECT now_wait, product_name, id_wait_session, max_wait
            FROM wait_session
            INNER JOIN store USING(id_store)
            WHERE store_name = '{}' and
                  end_wait is NULL and
                  product_name = ANY('{prod_id}');'''.format(context.user_data[WHAT_WHALE], prod_id='{🍔,🍕}')

        context.user_data[OPEN_SESSIONS] = np.array(query_postgre(query_db))
        if len(context.user_data[OPEN_SESSIONS]) > 0:
            text = "Сейчас ожидание в " + context.user_data[WHAT_WHALE] + '\n'
            remove_wait = [" " for _ in range(len(PRODUCT_NAME))]
            for i in context.user_data[OPEN_SESSIONS]:
                text = text + i[0] + " " + i[1] + '\n'
                index_prod = PRODUCT_NAME.index(i[1])
                remove_wait[index_prod] = BUTTON_REMOVE_WAIT + " " + i[1]
            remove_wait.extend(buttons_wait)
            buttons_wait = remove_wait
        else:
            text = "Ожидания в " + context.user_data[WHAT_WHALE] + ' нет\n'

        update.effective_message.reply_text(
            text=text + "поменять ожидание (в мин.):",
            reply_markup=keyboard_from_list(buttons_wait, len(PRODUCT_NAME)),
        )
        return WRITE_WAIT
    else:
        update.message.reply_text(
            text='Пожалуйста, выбери где сегодня работаешь',
            reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
        )
        return ConversationHandler.END
# ['убрать ожидание 🍔', '15 🍕', '15 🍔', '20 🍕', '20 🍔', '25 🍕', '25 🍔', '30 🍕', '30 🍔', '40 🍕', '40 🍔']
# ['убрать ожидание 🍕', '15 🍕', '15 🍔', '20 🍕', '20 🍔', '25 🍕', '25 🍔', '30 🍕', '30 🍔', '40 🍕', '40 🍔']

def write_wait(update, context):

    query = update.callback_query
    context.user_data[WAIT] = query.data

    wait_min = context.user_data[WAIT].split()[0]
    product = context.user_data[WAIT].split()[1]
    id_wait_session, max_wait, text = 0, 0, " "
    if len(context.user_data[OPEN_SESSIONS]) > 0:  # если уже есть ожидания
        logging.info('waiting -  ' + str(context.user_data[ID_USER_CHAT]) + ' нажали кнопку ожиданий- '  +' ожидания есть '  +'\n')
        #  на 1 точке может быть открыто несколько сессий ищем с нужным продуктом
        for i in context.user_data[OPEN_SESSIONS]:
            if i[1] == product:  # сессия ожидания открыта у продукта
                id_wait_session = i[2]
                # если закрываем сессию ожидания
                if wait_min == BUTTON_REMOVE_WAIT:
                    text = BUTTON_REMOVE_WAIT + " " + product + "в " + context.user_data[WHAT_WHALE]
                    # при закрытии закрываем сессию
                    q_close_wait_session = '''
                            SET TIMEZONE='posix/Asia/Krasnoyarsk';
                             UPDATE wait_session
                             SET end_wait = date_trunc('minute', now()), duration_wait = date_trunc('minute', (NOW() - begin_wait)), now_wait = 0
                             WHERE id_wait_session = {}
                         '''.format(id_wait_session)
                    query_postgre(q_close_wait_session)
                    # при закрытии добавляем entry
                    q_wait_entry ='''
                        SET TIMEZONE='posix/Asia/Krasnoyarsk';  
                        INSERT INTO wait_entry (date_time, wait_min, id_wait_session) VALUES
                        (date_trunc('minute', now()) ,{},{});
                    '''.format(0, id_wait_session)
                    query_postgre(q_wait_entry)

                # сессия открыта, но меняем текущее ожидание
                else:
                    text = 'Изменили ожидание ' + product + "на " + wait_min + " " +context.user_data[WHAT_WHALE]
                    max_wait = i[3] if i[3] > wait_min else wait_min
                    q_update_session = '''
                        UPDATE wait_session
                        SET max_wait = {}, now_wait = {}
                        WHERE id_wait_session = {}'''.format(max_wait, wait_min, id_wait_session)
                    query_postgre(q_update_session)
                    q_wait_entry = '''
                        SET TIMEZONE='posix/Asia/Krasnoyarsk';
                        INSERT INTO wait_entry (date_time, wait_min, id_wait_session) 
                        VALUES (date_trunc('minute', now()) ,{},{});
                        '''.format(wait_min, id_wait_session)
                    query_postgre(q_wait_entry)
                break
    # сессии закрыты для продукта, т.е. новое ожидание
    if len(context.user_data[OPEN_SESSIONS]) == 0 or id_wait_session == 0:
        text = 'Поставили ожидание ' + product + 'на ' + wait_min + " " +context.user_data[WHAT_WHALE]
        q_new_wait_session = '''
            SET TIMEZONE='posix/Asia/Krasnoyarsk';
            INSERT INTO wait_session (begin_wait, id_store, max_wait, product_name, now_wait)
            SELECT date_trunc('minute', now()), store.id_store, {}, '{}',{}
            FROM store
            WHERE store.store_name = '{}'
            RETURNING id_wait_session'''.format(wait_min, product, wait_min,context.user_data[WHAT_WHALE])
        # id_wait_session = query_postgre(q_new_wait_session)[0]
        id_wait_session = np.array(query_postgre(q_new_wait_session))[0, 0]
        q_wait_entry = '''
            SET TIMEZONE='posix/Asia/Krasnoyarsk';
            INSERT INTO wait_entry (date_time, wait_min, id_wait_session) VALUES
            (date_trunc('minute', now()) ,{},{});'''.format(wait_min, id_wait_session)
        query_postgre(q_wait_entry)
    query.edit_message_text(text=text)
    update.effective_message.reply_text(
        text=('вернулись в меню'),
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
    )
    context.bot.sendMessage(chat_id=TG_GROUP_NAMES[OPERATION_BM], text=text)
    context.bot.sendMessage(chat_id=TG_GROUP_NAMES[CASHIER_TG], text=text)
    return ConversationHandler.END


def wait_cancel(update, context):
    update.message.reply_text(
        text='Стартовое меню',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
    )
    return ConversationHandler.END


def timeout_callback_wait(update, context):
    query = update.callback_query
    query.edit_message_text(
        text='Прервали ⏳Ожидание, не было активностей',
        # reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP])
    )
    update.effective_message.reply_text(
        text='Вернулись в стартовое меню',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context),
    )

def timeout_message_wait(update, context):
    update.message.reply_text(
        text='Прервали ⏳Ожидание, не было активностей',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
    )


def conversation_waiting(dispatcher):
    dispatcher.add_handler(ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(BUTTON_WAIT_TITLE), wait_start, pass_user_data=True)],

        states={
            WRITE_WAIT: [CallbackQueryHandler(write_wait, pass_user_data=True)],
            ConversationHandler.TIMEOUT: [
                CallbackQueryHandler(timeout_callback_wait, pass_job_queue=True, pass_update_queue=True),
                MessageHandler(Filters.text | Filters.command, timeout_message_wait)],
        },
        fallbacks=[MessageHandler(Filters.regex(BUTTON_WAIT_CANCEL), wait_cancel, pass_user_data=True)],
        conversation_timeout=CHAT_TIMEOUT
    ))
