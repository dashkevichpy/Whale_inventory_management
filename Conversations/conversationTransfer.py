import numpy as np
import pytz
from telegram import ParseMode
from telegram.ext import MessageHandler
from telegram.ext import ConversationHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import Filters

from class_StartKeyboard import keyboard_start
import os
from dotenv import load_dotenv

load_dotenv()
CHAT_TIMEOUT = int(os.getenv('CHAT_TIMEOUT'))
ERROR_ADMIN_ID = os.getenv('ERROR_ADMIN_ID')

from gSheet import insert_to_error_krsk_bot
from keyboards import BUTTON_TRANSFER, BUTTON_TRANSFER_CANCEL, keyboard_cancel_transfer, keyboard_from_list, \
    keyboard_cancel_conversation
from postgres import get_stores_open
from datetime import datetime

DT_W_CARGO_O, CARGOTYPE_CARGOCOMMENT, CARGOCOMMENT_FROM, FROM_TO, TO_WRITE = range(5)
FROM, TO, CARGO_TYPE, CARGO_COMMENT, DELIVERY_TYPE = range(5)

ADDITIONAL_DIST_POINTS_FROM = ['ФК', 'Магазин', 'сэндвичи (GH и другие)', 'Прочее']
ADDITIONAL_DIST_POINTS_TO = ['ФК', 'Размен', 'Магазин', 'сэндвичи (GH и другие)', 'Прочее']
CARGO_TYPE_LIST = ['заготовки', 'хоз.средства', 'упаковка', 'деньги', 'прочее']
DELIVERY_TYPE_LIST = ['🚗 Курьер', '🚖 Такси', '🚘 Сотрудник']


def delivery_type(update, context):
    # context.user_data[ID_USER_TRANSFER] = update.message.chat_id
    update.message.reply_text(
        text='Выбрали ' + BUTTON_TRANSFER,
        reply_markup=keyboard_cancel_conversation(),
    )
    update.effective_message.reply_text(
        text='Кем перемещаем?',
        reply_markup=keyboard_from_list(DELIVERY_TYPE_LIST, 3),
    )
    return DT_W_CARGO_O


def deliverytype_cargo(update, context):
    query = update.callback_query
    context.user_data[DELIVERY_TYPE] = query.data
    query.edit_message_text(
        text='<b>Перемещаем: </b>{}\n'
             'Тип груза? '.format(context.user_data[DELIVERY_TYPE]),
        reply_markup=keyboard_from_list(CARGO_TYPE_LIST, 2),  # выбор точки
        parse_mode=ParseMode.HTML
    )
    return CARGOTYPE_CARGOCOMMENT


def cargotype_cargocomment(update, context):
    query = update.callback_query
    context.user_data[CARGO_TYPE] = query.data
    query.edit_message_text(
        text='<b>Перемещаем: </b>{}\n\n'
             '<b>Перевозим: </b>{}\n\n'
             'Что конкретно? Напишите'.format(context.user_data[DELIVERY_TYPE], context.user_data[CARGO_TYPE]),
        parse_mode=ParseMode.HTML
    )
    return CARGOCOMMENT_FROM


def cargocomment_from(update, context):
    context.user_data[CARGO_COMMENT] = update.message.text
    update.effective_message.reply_text(
        text='<b>Перемещаем: </b>{}\n\n'
             '<b>Перевозим: </b>{}\n'
             '<u>{}</u>\n\n'
             'Откуда?'.format(context.user_data[DELIVERY_TYPE],
                             context.user_data[CARGO_TYPE],
                             context.user_data[CARGO_COMMENT]),
        reply_markup=keyboard_from_list(np.concatenate((ADDITIONAL_DIST_POINTS_FROM,
                                                        get_stores_open('store_name')), axis=None), 2),  # выбор точки
        parse_mode=ParseMode.HTML
    )
    return FROM_TO


def from_to(update, context):
    query = update.callback_query
    context.user_data[FROM] = query.data

    to_points = np.concatenate((ADDITIONAL_DIST_POINTS_TO, get_stores_open('store_name')), axis=None)
    index = np.where(to_points==context.user_data[FROM])[0]
    if index.size > 0:
        to_points = np.delete(to_points, index)

    query.edit_message_text(
        text='<b>Перемещаем: </b>{}\n\n'
             '<b>Перевозим: </b>{}\n'
             '<u>{}</u>\n\n'
             '<b>Откуда: </b>{}\n\n'
             'Куда?'.format(context.user_data[DELIVERY_TYPE],
                            context.user_data[CARGO_TYPE],
                            context.user_data[CARGO_COMMENT],
                            context.user_data[FROM]),
        reply_markup=keyboard_from_list(to_points, 2),  # выбор точки
        parse_mode=ParseMode.HTML
    )
    return TO_WRITE


def to_write(update, context):
    query = update.callback_query
    context.user_data[TO] = query.data
    krsk_now = datetime.now(tz=pytz.timezone('Asia/Krasnoyarsk')).strftime("%d-%m-%Y %H:%M")
    try:
        insert_to_error_krsk_bot('Перемещения', [krsk_now, update.effective_user.id, update.effective_user.username,
                                                 context.user_data[FROM], context.user_data[TO],
                                                 context.user_data[DELIVERY_TYPE],
                                                 context.user_data[CARGO_TYPE], context.user_data[CARGO_COMMENT]])
        update.effective_message.reply_text(
            text='<b>Перемещаем: </b>{}\n\n'
                 '<b>Перевозим: </b>{}\n'
                 '<u>{}</u>\n\n'
                 '<b>Откуда: </b>{}\n\n'
                 '<b>Куда: </b>{}'.format(context.user_data[DELIVERY_TYPE],
                                            context.user_data[CARGO_TYPE],
                                            context.user_data[CARGO_COMMENT],
                                            context.user_data[FROM], context.user_data[TO]),
            parse_mode=ParseMode.HTML
        )

    except Exception as e:
        update.effective_message.reply_text(
                text='Возникла ошибка записи, вернулись обратно',
                reply_markup=keyboard_start(update.effective_message.chat.id, context)
        )
        context.bot.sendMessage(
                chat_id=ERROR_ADMIN_ID,
                text='Ошибка при внесении перемещения {}'.format(str(e))
        )
    finally:
        update.effective_message.reply_text(
            text='Вернулись в меню:',
            reply_markup=keyboard_start(update.effective_chat.id, context),
        )
        return ConversationHandler.END


def transfer_cancel(update, context):
    update.message.reply_text(
        text='Вернулись в меню:',
        reply_markup=keyboard_start(update.message.chat_id, context),
    )
    return ConversationHandler.END


def transfer(dispatcher):
    dispatcher.add_handler(ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(BUTTON_TRANSFER), delivery_type, pass_user_data=True)],

        states={
            DT_W_CARGO_O: [CallbackQueryHandler(deliverytype_cargo, pass_user_data=True)],
            CARGOTYPE_CARGOCOMMENT: [CallbackQueryHandler(cargotype_cargocomment, pass_user_data=True)],
            CARGOCOMMENT_FROM: [MessageHandler(Filters.regex(BUTTON_TRANSFER_CANCEL), transfer_cancel, pass_user_data=True),
                                MessageHandler(Filters.text, cargocomment_from, pass_user_data=True)],
            FROM_TO: [CallbackQueryHandler(from_to, pass_user_data=True)],
            TO_WRITE: [CallbackQueryHandler(to_write, pass_user_data=True)],

        },
        fallbacks=[MessageHandler(Filters.regex(BUTTON_TRANSFER_CANCEL), transfer_cancel, pass_user_data=True)],
        conversation_timeout=CHAT_TIMEOUT
    ))