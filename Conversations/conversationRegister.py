import numpy as np
from telegram.ext import ConversationHandler, MessageHandler, CallbackQueryHandler, Filters

from class_StartKeyboard import keyboard_start
import os
from dotenv import load_dotenv

load_dotenv()
CHAT_TIMEOUT = int(os.getenv('CHAT_TIMEOUT'))
from decorators import check_group
from keyboards import keyboard_from_list, keyboard_cancel_conversation, BUTTON_CANCEL_CONVERSATION, BUTTON_REGISTER
from postgres import  pg_get_department, pg_get_position_by_dept, pg_insert_new_employee

DEPT_NAME, POSITION_NAME, ID_MESSAGE_TO_DELETE = range(3)
CH_POSTION, WRITE = range(2)  # ch - значит choose - выбирать

@check_group
def register_check_choose_department(update, context):
    department_list = pg_get_department()
    update.message.reply_text(
        text='Привет! 👋 давай знакомиться',
        reply_markup=keyboard_cancel_conversation()
    )
    update.message.reply_text(
        text='Где ты работаешь?',
        reply_markup=keyboard_from_list(department_list, 2)
    )
    context.user_data[ID_MESSAGE_TO_DELETE] = update.message.message_id + 2
    return CH_POSTION


def register_wr_dept_ch_position(update, context):
    query = update.callback_query
    context.user_data[DEPT_NAME] = query.data
    position_list = pg_get_position_by_dept(context.user_data[DEPT_NAME])
    query.edit_message_text(
        text=f'Выбрали {context.user_data[DEPT_NAME]}\nдальше - должность?',
        reply_markup=keyboard_from_list(position_list, 1)
    )
    return WRITE


def register_write(update, context):
    query = update.callback_query
    context.user_data[POSITION_NAME] = query.data
    query.edit_message_text(
        text=f'Спасибо! Записались должность - {context.user_data[POSITION_NAME]}',
        reply_markup=None
    )
    pg_insert_new_employee(update.effective_chat.id,
                           context.user_data[POSITION_NAME],
                           update.effective_user.first_name,
                           update.effective_user.last_name,
                           update.effective_user.username)
    update.effective_message.reply_text(
        text='Вернулись в стартовое меню',
        reply_markup=keyboard_start(update.effective_chat.id, context),
    )
    return ConversationHandler.END


def register_timeout(update, context):
    # context.bot.delete_message(chat_id=update.message.chat.id, message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    # update.message.reply_text(
    #     text='Прервали регистрацию - не было активностей',
    #     reply_markup=keyboard_start(update.message.chat_id, context),
    # )

    chat_id = update.callback_query.message.chat.id
    context.bot.delete_message(chat_id=chat_id, message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    update.effective_message.reply_text(
        text='Прервали регистрацию - не было активностей',
        reply_markup=keyboard_start(chat_id, context),
    )
    return ConversationHandler.END


def register_end(update, context):
    context.bot.delete_message(chat_id=update.message.chat.id, message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    update.message.reply_text(
        text='Вернулись в cтартовое меню',
        reply_markup=keyboard_start(update.message.chat_id, context)
    )
    return ConversationHandler.END




def conversation_register(dispatcher):
    dispatcher.add_handler(ConversationHandler(
        # entry_points=[CommandHandler('register', register_check_choose_department, pass_user_data=True)],
        entry_points=[MessageHandler(Filters.regex(BUTTON_REGISTER), register_check_choose_department, pass_user_data=True)],
        states={
            CH_POSTION: [CallbackQueryHandler(register_wr_dept_ch_position, pass_user_data=True)],
            WRITE: [CallbackQueryHandler(register_write, pass_user_data=True)],
            ConversationHandler.TIMEOUT:[CallbackQueryHandler(register_timeout, pass_job_queue=True, pass_update_queue=True)],
        },
        fallbacks=[MessageHandler(Filters.regex(BUTTON_CANCEL_CONVERSATION), register_end, pass_user_data=True)],
        conversation_timeout=CHAT_TIMEOUT
    ))