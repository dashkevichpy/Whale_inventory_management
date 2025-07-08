import logging

import numpy as np
from telegram.ext import ConversationHandler, MessageHandler, CallbackQueryHandler, Filters

from class_StartKeyboard import keyboard_start
import os
from dotenv import load_dotenv

load_dotenv()
CHAT_TIMEOUT = int(os.getenv('CHAT_TIMEOUT'))
from decorators import check_group
from keyboards import BUTTON_WHAT_WHALE, keyboard_from_list
from postgres import query_postgre, pg_del_employee_from_store, get_stores_open

ID_USER_CHAT, WHAT_WHALE, ID_MESSAGE_TO_DELETE = range(3)
ASSIGN_WHALE = range(1)


def reset_store_employee(update, context):
    '''
        сбрасываем точку
    :param update:
    :param context:
    :return:
    '''
    id_employee = pg_del_employee_from_store(update.message.chat_id)
    if id_employee:
        text = f'Сбросили текущую точку,\n{BUTTON_WHAT_WHALE} - чтобы выбрать новую'
    else:
        text = 'Пожалуйста, выбери где сегодня работаешь'
    update.message.reply_text(
        text=text,
        reply_markup=keyboard_start(update.message.chat_id, context)
    )

@check_group
def choose_whale_start(update, context):
    context.user_data[ID_USER_CHAT] = update.message.chat_id
    store_postgre = np.array(get_stores_open('store_name')).flatten()
    update.effective_message.reply_text(
        text='Выбери точку:',
        reply_markup=keyboard_from_list(store_postgre, 2),
    )
    context.user_data[ID_MESSAGE_TO_DELETE] = update.message.message_id + 1
    return ASSIGN_WHALE


def assign_whale(update, context):  # внести кита в БД
    query = update.callback_query
    context.user_data[WHAT_WHALE] = query.data
    query_db = """
        INSERT INTO employee_in_store (id_store, chat_id_telegram)
            SELECT store.id_store, '{}'
            FROM store
            WHERE store.store_name = '{}'
    """.format(context.user_data[ID_USER_CHAT], context.user_data[WHAT_WHALE])
    query_postgre(query_db)
    context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT], message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    update.effective_message.reply_text(
            text=f"Выбрали {context.user_data[WHAT_WHALE]}",
            reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
        )
    log_text = 'user - {}, точка - {}'.format(update.effective_user,context.user_data[WHAT_WHALE] )
    return ConversationHandler.END


def timeout_message_choose_whale(update, context):
    try:
        context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT],
                                   message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    except:
        logging.error(f'Ошибка удаления сообщения choose_whale_cancel chat_id={context.user_data[ID_USER_CHAT]} - '
                      f'context: {context}')
    update.message.reply_text(
        text='Прервали выбор точки - не было активностей',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context),
    )
    return ConversationHandler.END


def choose_whale_cancel(update, context):
    try:
        context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT],
                                   message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    except:
        logging.error(f'Ошибка удаления сообщения choose_whale_cancel chat_id={context.user_data[ID_USER_CHAT]} - '
                      f'context: {context}')

    update.message.reply_text(
        text='Стартовое меню',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
    )
    return ConversationHandler.END


def conversation_choose_whale(dispatcher):
    dispatcher.add_handler(ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(BUTTON_WHAT_WHALE), choose_whale_start, pass_user_data=True)],
        states={
            ASSIGN_WHALE: [CallbackQueryHandler(assign_whale, pass_user_data=True)],
            ConversationHandler.TIMEOUT:
                [MessageHandler(Filters.text | Filters.command, timeout_message_choose_whale, pass_user_data=True)],
        },
        fallbacks=[MessageHandler(Filters.text | Filters.command, choose_whale_cancel, pass_user_data=True)],
        conversation_timeout=CHAT_TIMEOUT
    ))