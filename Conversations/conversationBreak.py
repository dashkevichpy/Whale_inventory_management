import numpy as np
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
BREAKAGES_ENTRY_SHEET_NAME = os.getenv('BREAKAGES_ENTRY_SHEET_NAME')
from decorators import check_group
from keyboards import  keyboard_yes_no, keyboard_critical, keyboard_cancel_breakage, keyboard_from_list

from keyboards import BUTTON_BREAK_TITLE, BUTTON_BREAK_CANCEL

from gSheet import insert_entry_breakages_gs

# индексы для диалога с поломками
from postgres import query_postgre,  get_stores_open

ID_USER_CHAT, USER_NAME, WHICH_WHALE, WHAT_BROKEN, CRITICAL, COMMENT, CHECK_MESSAGE, \
ID_TG_CHAT_REPORT, TEXT_MESSAGE, ID_MESSAGE_TO_DELETE = range(10)


@check_group
def broken_start(update, context):
    print(context.user_data)
    context.user_data[ID_USER_CHAT] = update.message.chat_id
    # print(context.user_data[ID_USER_CHAT])
    context.user_data[USER_NAME] = update.message.from_user.last_name
    store_postgre = np.array(get_stores_open('store_name')).flatten()
    store_postgre = np.insert(store_postgre, 1, 'ФК')

    update.message.reply_text(
        text='Выбрали 🛠Поломка',
        reply_markup=keyboard_cancel_breakage(),
    )
    update.effective_message.reply_text(
        text='Выберите место поломки:',
        reply_markup=keyboard_from_list(store_postgre, 2),
    )

    context.user_data[ID_MESSAGE_TO_DELETE] = update.message.message_id + 2
    return WHICH_WHALE


def broken_what(update, context):
    query = update.callback_query
    whale = query.data
    context.user_data[WHICH_WHALE] = whale
    pg_query = '''
        SELECT equiment_type
        FROM breakages  
    '''
    equiment_type = np.array(query_postgre(pg_query)).flatten()

    query.edit_message_text(
        text=('<b>Точка:</b> {}\n'
              'Выберите тип оборудования'.format(whale)),
        reply_markup=keyboard_from_list(equiment_type, 2),
        parse_mode=ParseMode.HTML,
        # reply_markup=keyboard_from_column(EQUIP_SHEET_NAME, 2, 3, 0, 2)
    )

    return WHAT_BROKEN


def broken_is_crit(update, context):
    query = update.callback_query
    what_broken = query.data
    context.user_data[WHAT_BROKEN] = what_broken
    print(context.user_data[WHAT_BROKEN])
    pg_query = '''
            SELECT telegram_gr
            FROM breakages
            WHERE equiment_type = '{}'
        '''.format(context.user_data[WHAT_BROKEN])

    context.user_data[ID_TG_CHAT_REPORT] = str(np.array(query_postgre(pg_query))[0][0])
    # print(telegr_chat)
    # # ID_TG_CHAT_REPORT

    query.edit_message_text(
        text=('<b>Точка:</b> {}\n'
              '<b>Оборудование:</b> {}\n'
              'Дальнейшая работа возможна?:'.format(context.user_data[WHICH_WHALE], what_broken)),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_critical()
    )
    return CRITICAL


def broken_comment(update, context):
    query = update.callback_query
    critical = query.data
    context.user_data[CRITICAL] = critical

    query.edit_message_text(
        text=('<b>Точка:</b> {}\n'
              '<b>Оборудование:</b> {}\n'
              '<b>Дальнейшая работа возможна?:</b> {}\n'
              'Опишите поломку:'.format(context.user_data[WHICH_WHALE],
                                        context.user_data[WHAT_BROKEN], critical)),
        parse_mode=ParseMode.HTML,
    )
    return COMMENT


def broken_check(update, context):
    context.user_data[COMMENT] = update.message.text

    if update.message.text == BUTTON_BREAK_CANCEL:
        broken_cancel(update, context)
        return ConversationHandler.END
    else:
        context.user_data[TEXT_MESSAGE] = ('Спасибо! Все верно?'
                                           '\n\n<b>Точка:</b> {}'
                                           '\n <b>Оборудование:</b> {}'
                                           '\n <b>Критическая:</b> {}'
                                           '\n <b>Комментарий:</b> {}'.format(context.user_data[WHICH_WHALE],
                                                                              context.user_data[WHAT_BROKEN],
                                                                              context.user_data[CRITICAL],
                                                                              context.user_data[COMMENT],
                                                                              ))

        update.effective_message.reply_text(
            text=context.user_data[TEXT_MESSAGE],
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_yes_no()
        )
        return CHECK_MESSAGE


def broken_finish(update, context):
    data = update.callback_query.data
    if data == "Yes":
        insert_entry_breakages_gs(context.user_data[ID_USER_CHAT],
                                  context.user_data[WHICH_WHALE],
                                  context.user_data[WHAT_BROKEN],
                                  context.user_data[CRITICAL],
                                  context.user_data[COMMENT], BREAKAGES_ENTRY_SHEET_NAME)

        update.effective_message.reply_text(
            text='Спасибо!',
            reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
        )

        # отправляем сообщение в чат о поломке
        context.bot.send_message(
            chat_id=context.user_data[ID_TG_CHAT_REPORT],
            text=context.user_data[TEXT_MESSAGE],
            parse_mode=ParseMode.HTML,
        )

    if data == "No":
        update.effective_message.reply_text(
            text='Сообщение удалено',
            reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
        )

    return ConversationHandler.END


def broken_cancel(update, context):
    """ Отменить весь процесс диалога. Данные будут утеряны
    """
    context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT], message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    update.message.reply_text(
        text='Внесение поломки прервано, вернулись в стартовое меню:',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
    )

    return ConversationHandler.END


def timeout_callback_broken(update, context):
    query = update.callback_query
    # context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT], message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    query.edit_message_text(
        text='Прервали внесение 🛠 поломки, не было активностей',
    )
    update.effective_message.reply_text(
        text='Вернулись в стартовое меню',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context),
    )


def timeout_message_broken(update, context):
    # context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT], message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    update.message.reply_text(
        text='Прервали внесение 🛠 поломки, не было активностей',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context),
    )


def add_observer_broken(dispatcher):
    dispatcher.add_handler(
        ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(BUTTON_BREAK_TITLE), broken_start, pass_user_data=True)],

        states={
            WHICH_WHALE: [CallbackQueryHandler(broken_what, pass_user_data=True)],
            WHAT_BROKEN: [CallbackQueryHandler(broken_is_crit, pass_user_data=True),
                          MessageHandler(Filters.regex(BUTTON_BREAK_CANCEL), broken_cancel, pass_user_data=True)],
            CRITICAL: [CallbackQueryHandler(broken_comment, pass_user_data=True),
                       MessageHandler(Filters.regex(BUTTON_BREAK_CANCEL), broken_cancel, pass_user_data=True)],
            COMMENT: [MessageHandler(Filters.text, broken_check, pass_user_data=True),
                      MessageHandler(Filters.regex(BUTTON_BREAK_CANCEL), broken_cancel, pass_user_data=True)],
            CHECK_MESSAGE: [CallbackQueryHandler(broken_finish, pass_user_data=True),
                            MessageHandler(Filters.regex(BUTTON_BREAK_CANCEL), broken_cancel, pass_user_data=True)],
            ConversationHandler.TIMEOUT:
                [CallbackQueryHandler(timeout_callback_broken, pass_job_queue=True, pass_update_queue=True),
                 MessageHandler(Filters.text | Filters.command, timeout_message_broken)],
        },

        fallbacks=[MessageHandler(Filters.regex(BUTTON_BREAK_CANCEL), broken_cancel, pass_user_data=True)],
        conversation_timeout=CHAT_TIMEOUT
    ))
