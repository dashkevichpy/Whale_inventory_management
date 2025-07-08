import urllib.parse
import logging

import numpy as np
from telegram import ParseMode
from telegram.ext import MessageHandler
from telegram.ext import ConversationHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import Filters
# import telegramcalendar
from class_StartKeyboard import keyboard_start
from decorators import check_group
from keyboards import keyboard_yes_no, keyboard_accept_read, keyboard_from_list, keyboard_cancel_error

from gSheet import insert_entry_errors_gs

import os
from dotenv import load_dotenv

load_dotenv()
CHAT_TIMEOUT = int(os.getenv('CHAT_TIMEOUT'))
ERROR_ADMIN_ID = os.getenv('ERROR_ADMIN_ID')

from keyboards import BUTTON_ERROR_TITLE, BUTTON_ERROR_CANCEL

# индексы для диалога с ошибками
from postgres import query_postgre, get_stores_open

# кони, люди: тут смешаны и ключи словаря и индексы, ужасно
ID_USER_CHAT_ERROR, USER_NAME_ERROR, WHICH_POST, WHAT_ERROR, WHAT_LOCATION, DATE_ERROR, DETAIL_COMMENT, \
CHECK_MESSAGE_ERROR, CHAT_ID_NOT1, CHAT_ID_NOT2, PHOTO_ID, ADD_PHOTO, PHOTO_FILE_ID, GET_PHOTO, ID_MESSAGE_TO_DELETE = range(15)


logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

s = urllib.parse.quote('clck.ru/QyYfR')

PHOTO_ERROR_TYPE = ['Качество заготовок', 'документы Корниенко', 'документы GH']

# -------------------------ERRORS---------------------------------


@check_group
def error_start(update, context):
    context.user_data[ID_USER_CHAT_ERROR] = update.message.chat_id
    context.user_data[USER_NAME_ERROR] = update.message.from_user.username
    context.user_data[PHOTO_FILE_ID] = None
    update.message.reply_text(
        text='<b> Выбрали: </b> 📯Ошибка',
        reply_markup=keyboard_cancel_error(),
        parse_mode=ParseMode.HTML,
    )
    pgre = '''
                SELECT department_name
                FROM errors_departments;
    '''
    department = np.array(query_postgre(pgre)).flatten()

    update.effective_message.reply_text(
        text='Кто ошибся?',
        # reply_markup=keyboard_position(),
        reply_markup=keyboard_from_list(department, 2),

    )
    context.user_data[ID_MESSAGE_TO_DELETE] = update.message.message_id + 2
    return WHICH_POST


def error_type(update, context):
    query = update.callback_query
    context.user_data[WHICH_POST] = query.data
    # print('WHICH_POST - ', context.user_data[WHICH_POST])

    pgre = '''
        SELECT error_name,group_telegram_id,personal_telegram_id
        FROM error_types
        INNER JOIN errors_departments USING(id_errors_categories)
        WHERE department_name = '{}';
        '''.format(context.user_data[WHICH_POST])
    type_error = np.array(query_postgre(pgre))
    try:
        context.user_data[CHAT_ID_NOT1] = type_error[0, 1]
        context.user_data[CHAT_ID_NOT2] = type_error[0, 2]
    except:
        logging.info(f'type_error[0, 1] error in ConversError {type_error},  '
                     f'{context.user_data[WHICH_POST]} \n')
        error_cancel(update, context)

    query.edit_message_text(
        text=('<b>Ошиблись:</b> {}\n'
              'Тип ошибки:'.format(context.user_data[WHICH_POST])),
        reply_markup=keyboard_from_list(type_error[:, 0].flatten(), 2),
        parse_mode=ParseMode.HTML,
    )
    return WHAT_ERROR


def error_location(update, context):
    query = update.callback_query
    context.user_data[WHAT_ERROR] = query.data
    store_postgre = np.array(get_stores_open('store_name')).flatten()
    store_postgre = np.insert(store_postgre, len(store_postgre), 'B2B')
    query.edit_message_text(
        text=('<b>Ошиблись: </b>{}\n'
              '<b>Тип ошибки: </b>{}\n\n'
              'Точка: '.format(context.user_data[WHICH_POST], context.user_data[WHAT_ERROR])),
        reply_markup=keyboard_from_list(store_postgre, 2),  # выбор точки
        parse_mode=ParseMode.HTML
    )
    return WHAT_LOCATION


def error_date_time(update, context):
    query = update.callback_query
    context.user_data[WHAT_LOCATION] = query.data
    query.edit_message_text(
        text=('<b>Ошиблись:  </b>{}\n'
              '<b>Тип ошибки:  </b>{}\n'
              '<b>Точка:  </b>{}\n\n'
              'Укажите дату / время ошибки, номер заказа: '.format(context.user_data[WHICH_POST], context.user_data[WHAT_ERROR],
                                            context.user_data[WHAT_LOCATION])),
        parse_mode=ParseMode.HTML
    )
    return DATE_ERROR


def error_comment(update, context):
    context.user_data[DATE_ERROR] = update.message.text
    if update.message.text == BUTTON_ERROR_CANCEL:
        error_cancel(update, context)
        return ConversationHandler.END
    else:
        update.effective_message.reply_text(
            text=('<b>Ошиблись:</b> {}\n'
                  '<b>Тип ошибки:</b> {}\n'
                  '<b>Точка:</b> {}\n'
                  '<b>Дату / время ошибки, номер заказа:</b> {}\n\n'
                  '<b>Комментарии к ошибке </b>'.format(context.user_data[WHICH_POST], context.user_data[WHAT_ERROR],
                                                 context.user_data[WHAT_LOCATION], context.user_data[DATE_ERROR])),
            parse_mode=ParseMode.HTML
        )
        return DETAIL_COMMENT


def error_check(update, context):
    context.user_data[DETAIL_COMMENT] = update.message.text
    if context.user_data[WHAT_ERROR] in PHOTO_ERROR_TYPE and context.user_data[PHOTO_FILE_ID] is None:
    # if context.user_data[WHAT_ERROR] == 'Качество заготовок' and context.user_data[PHOTO_FILE_ID] is None:
        update.effective_message.reply_text(
            text='📷 Фото прикрепим?',
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_yes_no()
            )
        return ADD_PHOTO

    else:
        update.effective_message.reply_text(
            text='Спасибо! Все верно?\n\n<b>Должность:</b> {}\n<b>Ошибка:</b> {}\n<b>Точка:</b> {}\n<b>Дата/время:</b> {}\n<b>Комментарий:</b> {}'.format(
                context.user_data[WHICH_POST],
                context.user_data[WHAT_ERROR],
                context.user_data[WHAT_LOCATION],
                context.user_data[DATE_ERROR],
                context.user_data[DETAIL_COMMENT],
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_yes_no()
        )
        return CHECK_MESSAGE_ERROR


def error_request_photo(update, context):
    query = update.callback_query
    data = query.data
    if data == "Yes":
        query.edit_message_text(
            text='Можно прямо в бот 📸',
        )
        return GET_PHOTO
    else:  # без фото
        query.edit_message_text(
            text='Нет, так нет! \nПроверь, что всё верно 👇\n\n<b>Должность:</b> {}\n<b>Ошибка:</b> {}\n<b>Точка:</b> {}\n<b>Дата/время:</b> {}\n<b>Комментарий:</b> {}'.format(
                context.user_data[WHICH_POST],
                context.user_data[WHAT_ERROR],
                context.user_data[WHAT_LOCATION],
                context.user_data[DATE_ERROR],
                context.user_data[DETAIL_COMMENT],
            ),
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_yes_no()
        )
        return CHECK_MESSAGE_ERROR


def error_receive_photo(update, context):
    context.user_data[PHOTO_FILE_ID] = update.message.photo[-1].file_id

    update.effective_message.reply_text(
        text='Спасибо! Все верно?\n\n<b>Должность:</b> {}\n<b>Ошибка:</b> {}\n<b>Точка:</b> {}\n<b>Дата/время:</b> {}\n<b>Комментарий:</b> {}'.format(
            context.user_data[WHICH_POST],
            context.user_data[WHAT_ERROR],
            context.user_data[WHAT_LOCATION],
            context.user_data[DATE_ERROR],
            context.user_data[DETAIL_COMMENT],
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_yes_no()
    )
    return CHECK_MESSAGE_ERROR


def error_finish(update, context):
    data = update.callback_query.data
    check_message = data
    context.user_data[CHECK_MESSAGE_ERROR] = check_message

    if data == "Yes":
        try:
            insert_entry_errors_gs(context.user_data[ID_USER_CHAT_ERROR],
                                   context.user_data[WHAT_LOCATION],
                                   context.user_data[DATE_ERROR],
                                   context.user_data[WHAT_ERROR],
                                   context.user_data[DETAIL_COMMENT],
                                   context.user_data[WHICH_POST])
            update.effective_message.reply_text(
                text='Спасибо!',
                reply_markup=keyboard_start(context.user_data[ID_USER_CHAT_ERROR], context)
            )
            text = ('Ошибка:'
                    '\n\nДолжность: {}'
                    '\n От: {}'
                    '\n Точка: {}'
                    '\n Тип ошибки: {}'
                    '\n Дата ошибки: {}'
                    '\n Комментарий: {}'
                    .format(context.user_data[WHICH_POST],
                            context.user_data[USER_NAME_ERROR],
                            context.user_data[WHAT_LOCATION],
                            context.user_data[DATE_ERROR],
                            context.user_data[WHAT_ERROR],
                            context.user_data[DETAIL_COMMENT],
                            )
                    )
            try:
                if context.user_data[PHOTO_FILE_ID]:
                    context.bot.send_photo(
                        chat_id=context.user_data[CHAT_ID_NOT1],
                        caption=text,
                        photo=context.user_data[PHOTO_FILE_ID]
                    )
                else:
                    context.bot.send_message(
                        chat_id=context.user_data[CHAT_ID_NOT1],
                        text=text,
                        reply_markup=keyboard_accept_read(),
                    )

                    #  -1001225063049 BM - Кассиры




            except Exception as e:
                logging.error('insert data to table {} - ошибка {}'.format(context.user_data[WHICH_POST], str(e)))
                context.bot.sendMessage(
                    chat_id=ERROR_ADMIN_ID,
                    text='ошибка бота ошибок: некорректный ID для отправки сообщений'
                )
        except Exception as e:
            logging.error('insert data to table {} - ошибка {}'.format(context.user_data[WHICH_POST], str(e)))

            update.effective_message.reply_text(
                text='Возникла ошибка! Сообщите о ней',
                reply_markup=keyboard_start(context.user_data[ID_USER_CHAT_ERROR], context)
            )
            context.bot.sendMessage(
                chat_id=ERROR_ADMIN_ID,
                text='Ошибка при внесении замечания {} - {}'.format(context.user_data[WHICH_POST], str(e))
            )
    if data == "No":
        update.effective_message.reply_text(
            text='Сообщение удалено',
            reply_markup=keyboard_start(context.user_data[ID_USER_CHAT_ERROR], context)
        )
    return ConversationHandler.END


def error_cancel(update, context):
    """ Отменить весь процесс диалога. Данные будут утеряны
    """
    context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT_ERROR], message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    update.message.reply_text(
        text='Внесение ошибки прервано, вернулись в стартовое меню:',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT_ERROR], context)
    )
    return ConversationHandler.END


def timeout_callback_error(update, context):
    query = update.callback_query
    # context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT_ERROR], message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    query.edit_message_text(
        text='Прервали внесение 📯 ошибки, не было активностей',
    )
    update.effective_message.reply_text(
        text='Вернулись в стартовое меню',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT_ERROR], context),
    )


def timeout_message_error(update, context):
    # context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT_ERROR], message_id=context.user_data[ID_MESSAGE_TO_DELETE])
    update.message.reply_text(
        text='Прервали внесение 📯 ошибки, не было активностей',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT_ERROR], context),
    )


def error_input(update, context):
    update.message.reply_text(
        text='ввыберите из вариантов в клавиатуре',
    )
    return WHAT_LOCATION


def wrong_input_photo(update, context):
    update.message.reply_text(
        text='😓 это не фото, а надо фото. Ещё разок',
    )
    return GET_PHOTO


def add_observer_error(dispatcher):
    dispatcher.add_handler(ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(BUTTON_ERROR_TITLE), error_start, pass_user_data=True)],

        states={
            WHICH_POST: [CallbackQueryHandler(error_type, pass_user_data=True)],
            WHAT_ERROR: [CallbackQueryHandler(error_location, pass_user_data=True),
                         MessageHandler(Filters.regex(BUTTON_ERROR_CANCEL), error_cancel, pass_user_data=True)],

            WHAT_LOCATION: [CallbackQueryHandler(error_date_time, pass_user_data=True),
                            MessageHandler(Filters.regex(BUTTON_ERROR_CANCEL), error_cancel, pass_user_data=True),
                            MessageHandler(Filters.text, error_input, pass_user_data=True)],

            DATE_ERROR: [MessageHandler(Filters.text, error_comment, pass_user_data=True),
                         MessageHandler(Filters.regex(BUTTON_ERROR_CANCEL), error_cancel, pass_user_data=True)],

            DETAIL_COMMENT: [MessageHandler(Filters.regex(BUTTON_ERROR_CANCEL), error_cancel, pass_user_data=True),
                             MessageHandler(Filters.text, error_check, pass_user_data=True)],

            ADD_PHOTO: [CallbackQueryHandler(error_request_photo, pass_user_data=True),
                        MessageHandler(Filters.text, error_input, pass_user_data=True)],

            GET_PHOTO: [MessageHandler(Filters.regex(BUTTON_ERROR_CANCEL), error_cancel, pass_user_data=True),
                        MessageHandler(~Filters.photo, wrong_input_photo,  pass_user_data=True),
                        MessageHandler(Filters.photo, error_receive_photo,  pass_user_data=True)],

            CHECK_MESSAGE_ERROR: [CallbackQueryHandler(error_finish, pass_user_data=True)],

            ConversationHandler.TIMEOUT:
                [CallbackQueryHandler(timeout_callback_error, pass_job_queue=True, pass_update_queue=True),
                 MessageHandler(Filters.text | Filters.command, timeout_message_error)],
        },
        # fallbacks=[CommandHandler('cancel_error', error_cancel)]
        fallbacks=[MessageHandler(Filters.regex(BUTTON_ERROR_CANCEL), error_cancel, pass_user_data=True)],
        conversation_timeout=CHAT_TIMEOUT
    ))


