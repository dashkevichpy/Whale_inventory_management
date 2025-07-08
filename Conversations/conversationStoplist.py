from collections import namedtuple
from enum import Enum
from uuid import uuid4

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
import os
from dotenv import load_dotenv

load_dotenv()
TG_GROUP_NAMES = os.getenv('TG_GROUP_NAMES')
CASHIER_TG = os.getenv('CASHIER_TG')
STOPS_TG = os.getenv('STOPS_TG')
from keyboards import keyboard_yes_no
from postgres import pg_get_nomenclature_to_stop_list, pg_add_stop_list, pg_get_stop_list, pg_remove_stop_list

BUTTON_STOP_START = "🛑 STOP"
# BUTTON_REMOVE_STOP_TITLE = "снять со STOP"

StopButton = namedtuple('StopButton', ('button_text', 'code_inline', 'code_split'))

class StopButtonList(Enum):
    BUTTON_ADD_STOP = StopButton("добавить STOP", "write#off", '➕⛔')
    BUTTON_REMOVE_STOP = StopButton("снять со STOP", "removewrite#off", '➖⛔')

def keyboard_switch_incline(list_values: list, col_amount: int) -> InlineKeyboardMarkup:
    '''
        список в inline mode клавиатуру
    :param list_values:
    :param col_amount:
    :return:
    '''
    keyboard = [[] for _ in range(len(list_values))]
    count = 0

    for cell_value in list_values:
        rt = int(count / col_amount)
        keyboard[int(rt)].append(InlineKeyboardButton(text=cell_value, switch_inline_query_current_chat="write#off"))
        count += 1

    return InlineKeyboardMarkup(keyboard)


def stoplist_dispatch(update, context):
    keyboard = []
    stop_list = pg_get_stop_list(context.user_data['employee'].id_store)
    keyboard.append([InlineKeyboardButton(text=StopButtonList.BUTTON_ADD_STOP.value.button_text,
                                          switch_inline_query_current_chat=StopButtonList.BUTTON_ADD_STOP.value.code_inline)])

    if stop_list:
        keyboard.append([InlineKeyboardButton(text=StopButtonList.BUTTON_REMOVE_STOP.value.button_text,
                                              switch_inline_query_current_chat=StopButtonList.BUTTON_REMOVE_STOP.value.code_inline)])
    update.message.reply_text(
        text='Выберите дествие:',
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


def add_stop_list(update, context):
    try:
        prov_list = pg_get_nomenclature_to_stop_list(context.user_data['employee'].id_store)
    except KeyError:
        prov_list = ['😤Точка не выбрана!']

    res = [InlineQueryResultArticle(
        id=str(uuid4()),
        title=p,
        input_message_content=InputTextMessageContent(StopButtonList.BUTTON_ADD_STOP.value.code_split+p),
        hide_url=True,
        thumb_height = 5
    ) for p in prov_list]
    update.inline_query.answer(res, cache_time=1)


def remove_stop_list(update, context):
    try:
        prov_list = pg_get_stop_list(context.user_data['employee'].id_store)
    except KeyError:
        prov_list = ['😤Точка не выбрана!']

    res = [InlineQueryResultArticle(
        id=str(uuid4()),
        title=p,
        input_message_content=InputTextMessageContent(StopButtonList.BUTTON_REMOVE_STOP.value.code_split + p),
        hide_url=True,
        thumb_height=5
    ) for p in prov_list]
    update.inline_query.answer(res, cache_time=1)


def add_stop_handler(update, context):
    nomenclature_name = update.effective_message.text.split(StopButtonList.BUTTON_ADD_STOP.value.code_split)[1]
    pg_add_stop_list(context.user_data['employee'].id_store, nomenclature_name)
    context.bot.sendMessage(chat_id=TG_GROUP_NAMES[STOPS_TG], text=f'➕⛔ {nomenclature_name} '
                                                                   f'в {context.user_data["employee"].store_name}')


def remove_stop_handler(update, context):
    nomenclature_name = update.effective_message.text.split(StopButtonList.BUTTON_REMOVE_STOP.value.code_split)[1]
    pg_remove_stop_list(context.user_data['employee'].id_store, nomenclature_name)
    context.bot.sendMessage(chat_id=TG_GROUP_NAMES[STOPS_TG], text=f'➖⛔ {nomenclature_name} '
                                                                   f'в {context.user_data["employee"].store_name}')


# inline_buttons.append(
#     telebot.types.InlineQueryResultArticle(
#         id=query_new.pk,
#         title=prod.product.name,
#         description=f"{prod.product.description} описание",
#         input_message_content=telebot.types.InputTextMessageContent(
#                                         message_text=get_text(key='product_card').format(
#                                             prod.product.name,
#                                             prod.product.price,
#                                             prod.product.description
#                                         ),
#                                         parse_mode='HTML'
#                                     ),
#                                     thumb_url=prod.product.photo if prod.product.photo else None,
#                                     reply_markup=keyboard
#                                 )
#                             )



# ADD_STOP_LIST = StockEvent(BUTTON_ADD_STOP_LIST, START_STOP_TIME,  END_STOP_TIME, None)

# from telegram import ParseMode
# from telegram.ext import MessageHandler, CallbackContext, CommandHandler
# from telegram.ext import ConversationHandler
# from telegram.ext import CallbackQueryHandler
# from telegram.ext import Filters
#
# from decorators import check_group
# from keyboards import BUTTON_STOP_TITLE, BUTTON_STOP_CANCEL, BUTTON_STOP_RETURN_INLINE, KEYBOARD_STOP_ACTIONS_TITLES
# import numpy as np
#
# from keyboards import keyboard_start, \
#     keyboard_from_list, keyboard_stoplist_actions, \
#     KEYBOARD_STOP_ACTIONS_CALLBACK, KEYBOARD_STOP_ADD_CONT_CALLBACK, \
#     keyboard_cancel_stoplist, keyboard_add_cont, keyboard_del_cont, \
#     KEYBOARD_STOP_DEL_CONT_CALLBACK
#
# from postgres import query_postgre, view_all_stoplist, add_stop_postgre, del_stop_postgre
#
# from configs import ERROR_ADMIN_ID, STOPLIST_NOTIF_RANK, TG_GROUP_NAMES, OPERATION_BM, STOPS_TG, CHAT_TIMEOUT
# import logging
#
# logging.basicConfig(level=logging.INFO, filename='app.log', filemode='w',
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#
# # индексы для хранения информации по стопам в памяти бота
# # ID_USER_CHAT_STOP, USER_NAME_STOP, WHICH_WHALE_STOP, PROVISION_STOP, AMOUNT_STOP, CHAT_ID_N1_STOP, CHAT_ID_N2_STOP = \
# #     range(7)
#
# #  STOPLIST_DATA_STOP - записываем все стопы, а потом сохраняем все разом, весь массив
# ID_USER_DATA_STOP, WHALE_DATA_STOP, ACTION_DATA_STOP, \
# CATEGORY_DATA_STOP, PROVISION_DATA_STOP, AMOUNT_DATA_STOP, \
# STOPLIST_DATA_STOP, \
# REMOVE_PROVISION_DATA_STOP = range(8)
#
# # индексы для навигации меду диалогами
# # ACTION, ADD_TO_STOP, ADD_TO_STOP_CATEGORY, ADD_TO_STOP_PROVISION = range(4)
#
# ACTIONS, DISPATCH, \
# ADD_CATEGORY, ADD_PROVISION, ADD_WRITE, ADD_AMOUNT, ADD_WRITE_AMOUNT, ADD_CONTINUE, \
# REMOVE_VIEW_PROVISION, REMOVE_PROVISION, REMOVE_CONTINUE = range(11)
#
# @check_group
# def stop_list_actions(update, context):
#     context.user_data[ID_USER_DATA_STOP] = update.message.chat_id
#     # print('user -', update.message.chat_id)
#     # find in which whale he is
#     query_db = """SELECT store_name
#                             FROM employee_in_store
#                             INNER JOIN store USING(id_store)
#                             WHERE chat_id_telegram = '{}'
#                     """.format(context.user_data[ID_USER_DATA_STOP])
#     # always not empty
#     whale_store = np.array(query_postgre(query_db))
#     if whale_store.size > 0:
#         context.user_data[WHALE_DATA_STOP] = whale_store[0, 0]
#         # print(context.user_data[WHALE_DATA_STOP])
#         log_text = 'STOP user - {}, точка - {}'.format(update.effective_user, context.user_data[WHALE_DATA_STOP])
#         print(log_text)
#         update.message.reply_text(
#             text='Выбрали 🛑STOP',
#             reply_markup=keyboard_cancel_stoplist()
#         )
#         update.effective_message.reply_text(
#             text='Выберите действие:',
#             reply_markup=keyboard_stoplist_actions(),
#         )
#         return DISPATCH
#     else:
#         log_text = 'STOP user - {}, точка не выбрана'.format(update.effective_user)
#         print(log_text)
#         update.message.reply_text(
#             text='Пожалуйста, выбери где сегодня работаешь',
#             reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP])
#         )
#         return ConversationHandler.END
#         # print('bye')
#
#
# def stop_list_dispatch(update, context):  # save action
#     query = update.callback_query
#     # --------------------------------------add_stop_list--------------------------------------
#     if query.data == KEYBOARD_STOP_ACTIONS_CALLBACK[0] or query.data == BUTTON_STOP_RETURN_INLINE or query.data == \
#             KEYBOARD_STOP_ADD_CONT_CALLBACK[0]:
#         context.user_data[ACTION_DATA_STOP] = KEYBOARD_STOP_ACTIONS_TITLES[KEYBOARD_STOP_ACTIONS_CALLBACK[0]]
#         # find category which has 1 minimum provision
#         query_db = """
#                        WITH dsdf AS (
#                                SELECT category_name, COUNT (id_provision)
#                                FROM category_provision
#                                INNER JOIN provision USING(id_category_provision)
#                                INNER JOIN stoplist USING(id_provision)
#                                INNER JOIN store USING(id_store)
#                                WHERE store_name = '{}'
#                                GROUP BY category_name
#                                INTERSECT
#                                SELECT category_name, COUNT (id_provision)
#                                FROM category_provision
#                                INNER JOIN provision USING(id_category_provision)
#                                GROUP BY category_name
#                        )
#                        SELECT DISTINCT category_name
#                        FROM provision
#                        INNER JOIN category_provision USING(id_category_provision)
#                        WHERE category_name NOT IN (SELECT category_name FROM dsdf)
#                        ORDER BY category_name
#                        """.format(context.user_data[WHALE_DATA_STOP])
#         categories_postgre = np.array(query_postgre(query_db)).flatten()
#
#         # log_text = 'add_stop_list user - {}, точка - {} - {}'.format(update.effective_user,
#         #                                                              context.user_data[WHALE_DATA_STOP],
#         #                                                              context.user_data[ACTION_DATA_STOP])
#         # print(log_text)
#
#         query.edit_message_text(
#             text=('Точка: {}\n'
#                   'Действие: {}\n'
#                   'Выберите категорию'.format(context.user_data[WHALE_DATA_STOP],
#                                               context.user_data[ACTION_DATA_STOP])),
#             reply_markup=keyboard_from_list(categories_postgre, 2),
#         )
#         return ADD_PROVISION
#     # --------------------------------------view_stop_list--------------------------------------
#     if query.data == KEYBOARD_STOP_ACTIONS_CALLBACK[1]:
#         logging.info('start query - view/n')
#         output = view_all_stoplist()
#         query.edit_message_text(
#             text='Стоп - лист:'
#         )
#         if not output:
#             update.effective_message.reply_text(
#                 text='<b> На стопе ничего нет </b>\n '
#                      'Вышли из 🛑STOP, вернулись в стартовое меню',
#                 parse_mode=ParseMode.HTML,
#                 reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP]),
#             )
#         else:
#             update.effective_message.reply_text(
#                 text="<pre> \n" + output + "</pre>",
#                 parse_mode=ParseMode.HTML,
#                 reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP])
#             )
#         return ConversationHandler.END
#     # --------------------------------------delete--------------------------------------
#     if query.data == KEYBOARD_STOP_ACTIONS_CALLBACK[2] or query.data == KEYBOARD_STOP_DEL_CONT_CALLBACK[0]:
#         # provision which on stop
#         query_db = """SELECT provision_name
#                             FROM provision
#                             INNER JOIN stoplist USING(id_provision)
#                             INNER JOIN store USING(id_store)
#                             WHERE store_name = '{}'
#                     """.format(context.user_data[WHALE_DATA_STOP])
#         stoplist_now = np.array(query_postgre(query_db)).flatten()
#         if not stoplist_now.size:
#             update.effective_message.reply_text(
#                 text='В этом ките стопов нет 👽',
#                 parse_mode=ParseMode.HTML,
#                 reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP]),
#             )
#             return ConversationHandler.END
#         else:
#             # if continue stop
#             if query.data == KEYBOARD_STOP_DEL_CONT_CALLBACK[0]:
#                 update.effective_message.reply_text(
#                     text=('Точка: {}\n'
#                           'Что снимаем со стопа?'.format(context.user_data[WHALE_DATA_STOP])),
#                     reply_markup=keyboard_from_list(stoplist_now, 2),
#                 )
#             else:
#                 query.edit_message_text(
#                     text=('Точка: {}\n'
#                           'Что снимаем со стопа?'.format(context.user_data[WHALE_DATA_STOP])),
#                     reply_markup=keyboard_from_list(stoplist_now, 2),
#                 )
#             return REMOVE_PROVISION
#
#
# def stop_list_add_provision(update, context):  # keyb - provisions (categories)
#     query = update.callback_query
#     context.user_data[CATEGORY_DATA_STOP] = query.data
#     try:
#         query_db = """SELECT provision_name
#                       FROM provision
#                       INNER JOIN category_provision USING(id_category_provision)
#                       WHERE category_name = '{}'
#                       EXCEPT
#                       SELECT provision_name
#                       FROM provision
#                       INNER JOIN stoplist USING(id_provision)
#                       INNER JOIN store USING(id_store)
#                       WHERE store_name = '{}'
#                       ORDER BY provision_name""".format(context.user_data[CATEGORY_DATA_STOP],
#                                                         context.user_data[WHALE_DATA_STOP])
#         provisions_available = np.array(query_postgre(query_db)).flatten()
#         provisions_available = np.insert(provisions_available, 0, BUTTON_STOP_RETURN_INLINE)
#         query.edit_message_text(
#             text=('Точка: {}\n'
#                   'Действие: {}\n'
#                   'Категория: {}\n'
#                   'Выберите заготовку/упаковку'.format(context.user_data[WHALE_DATA_STOP],
#                                                        context.user_data[ACTION_DATA_STOP],
#                                                        context.user_data[CATEGORY_DATA_STOP])),
#             reply_markup=keyboard_from_list(provisions_available, 2),
#         )
#         return ADD_WRITE
#     except:
#         context.bot.sendMessage(
#             chat_id=ERROR_ADMIN_ID,
#             text='STOP: ошибка в stop_list_add_provision'
#         )
#         update.effective_message.reply_text(
#             text='Произошла ошибка, о ней уже сообщили кому надо. Диалог прерван',
#             reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP]))
#         return ConversationHandler.END
#
#
# def stop_list_add_write(update, context):
#     query = update.callback_query
#     # если нажали кнопку "обратно"
#     if query.data == BUTTON_STOP_RETURN_INLINE:
#         stop_list_dispatch(update, context)
#         return ADD_PROVISION
#     else:
#         provision = query.data
#         context.user_data[PROVISION_DATA_STOP] = provision
#         print(context.user_data[PROVISION_DATA_STOP], "поставили на стоп в Кит - ", context.user_data[WHALE_DATA_STOP])
#         add_stop_postgre(context.user_data[WHALE_DATA_STOP], context.user_data[PROVISION_DATA_STOP])
#         query.edit_message_text(
#             text='Поставили <b>{}</b> на стоп -  <b>{}</b>'.format(context.user_data[PROVISION_DATA_STOP],
#                                                                    context.user_data[WHALE_DATA_STOP]),
#             # reply_markup=keyboard_stoplist_add_continue()
#             reply_markup=keyboard_add_cont(),
#             parse_mode=ParseMode.HTML,
#         )
#         # notification_rank
#         notification_rank = query_postgre("""SELECT notification_rank
#                             FROM provision
#                             WHERE provision_name = '{}'""".format(context.user_data[PROVISION_DATA_STOP]))
#         context.bot.sendMessage(
#             chat_id=TG_GROUP_NAMES[OPERATION_BM],
#             text='Новый стоп <b>{}</b> в <b>{}</b>'.format(context.user_data[PROVISION_DATA_STOP],
#                                                            context.user_data[WHALE_DATA_STOP]),
#             parse_mode=ParseMode.HTML,
#         )
#         context.bot.sendMessage(
#             chat_id=TG_GROUP_NAMES[STOPS_TG],
#             text='Новый стоп <b>{}</b> в <b>{}</b>'.format(context.user_data[PROVISION_DATA_STOP],
#                                                            context.user_data[WHALE_DATA_STOP]),
#             parse_mode=ParseMode.HTML,
#         )
#         # if STOPLIST_NOTIF_RANK[0] == notification_rank[0][0]:
#         #     context.bot.sendMessage(
#         #         chat_id=TG_GROUP_NAMES[OPERATION_BM],
#         #         text='Новый стоп <b>{}</b> в <b>{}</b>'.format(context.user_data[PROVISION_DATA_STOP],
#         #                                                        context.user_data[WHALE_DATA_STOP]),
#         #         parse_mode=ParseMode.HTML,
#         #     )
#         #     context.bot.sendMessage(
#         #         chat_id=TG_GROUP_NAMES[STOPS_TG],
#         #         text='Новый стоп <b>{}</b> в <b>{}</b>'.format(context.user_data[PROVISION_DATA_STOP],
#         #                                                        context.user_data[WHALE_DATA_STOP]),
#         #         parse_mode=ParseMode.HTML,
#         #     )
#         # elif STOPLIST_NOTIF_RANK[1] == notification_rank[0][0]:
#         #     context.bot.sendMessage(
#         #         chat_id=TG_GROUP_NAMES[STOPS_TG],
#         #         text='Новый стоп <b>{}</b> в <b>{}</b>'.format(context.user_data[PROVISION_DATA_STOP],
#         #                                                        context.user_data[WHALE_DATA_STOP]),
#         #         parse_mode=ParseMode.HTML,
#         #     )
#         # elif STOPLIST_NOTIF_RANK[2] == notification_rank[0][0]:
#         #     context.bot.sendMessage(
#         #         chat_id=TG_GROUP_NAMES[STOPS_TG],
#         #         text='Новый стоп <b>{}</b> в <b>{}</b>'.format(context.user_data[PROVISION_DATA_STOP],
#         #                                                        context.user_data[WHALE_DATA_STOP]),
#         #         parse_mode=ParseMode.HTML,
#         #     )
#         return ADD_CONTINUE
#
#
# def stop_list_add_continue(update, context):
#     query = update.callback_query
#     next_action = query.data
#     current_text = update.effective_message.text
#     query.edit_message_text(  # убираем клавиатуру
#         parse_mode=ParseMode.HTML,
#         text=current_text,
#     )
#     # ----- if add another stop --------------------------
#     if next_action == KEYBOARD_STOP_ADD_CONT_CALLBACK[0]:
#         stop_list_dispatch(update, context)
#         return ADD_PROVISION
#     # ----- if exit --------------------------
#     if next_action == KEYBOARD_STOP_ADD_CONT_CALLBACK[1]:
#         update.effective_message.reply_text(
#             text='👋 пока',
#             reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP]),
#         )
#         return ConversationHandler.END
#
#
# def stop_list_remove_provision(update, context):
#     query = update.callback_query
#     context.user_data[PROVISION_DATA_STOP] = query.data
#     del_stop_postgre(context.user_data[WHALE_DATA_STOP], context.user_data[PROVISION_DATA_STOP])
#     # print("удалили ", context.user_data[PROVISION_DATA_STOP])
#     query.edit_message_text(
#         text=('Сняли <b>{}</b> со стопа -  <b>{}</b>'.format(context.user_data[PROVISION_DATA_STOP],
#                                                              context.user_data[WHALE_DATA_STOP])),
#         reply_markup=keyboard_del_cont(),
#         parse_mode=ParseMode.HTML,
#     )
#     context.bot.sendMessage(
#         chat_id=TG_GROUP_NAMES[STOPS_TG],
#         text='Сняли со стопа <b>{}</b> в <b>{}</b>'.format(context.user_data[PROVISION_DATA_STOP],
#                                                            context.user_data[WHALE_DATA_STOP]),
#         parse_mode=ParseMode.HTML,
#     )
#     context.bot.sendMessage(
#         chat_id=TG_GROUP_NAMES[OPERATION_BM],
#         text='Сняли со стопа <b>{}</b> в <b>{}</b>'.format(context.user_data[PROVISION_DATA_STOP],
#                                                            context.user_data[WHALE_DATA_STOP]),
#         parse_mode=ParseMode.HTML,
#     )
#     return REMOVE_CONTINUE
#
#
# def stop_list_remove_continue(update, context):
#     query = update.callback_query
#     next_action = query.data
#     current_text = update.effective_message.text
#     query.edit_message_text(  # убираем клавиатуру
#         parse_mode=ParseMode.HTML,
#         text=current_text,
#     )
#     # ----- if another stop --------------------------
#     if next_action == KEYBOARD_STOP_DEL_CONT_CALLBACK[0]:
#         stop_list_dispatch(update, context)
#         return REMOVE_PROVISION
#     # ----- if exit --------------------------
#     if next_action == KEYBOARD_STOP_DEL_CONT_CALLBACK[1]:
#         update.effective_message.reply_text(
#             text='👋 пока',
#             reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP]),
#         )
#         return ConversationHandler.END
#
#
# def stop_list_cancel(update, context):
#     """ Отменить весь процесс диалога. Данные будут утеряны
#     """
#     update.message.reply_text(
#         text='Вышли из 🛑STOP, вернулись в стартовое меню',
#         reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP])
#     )
#     return ConversationHandler.END
#
#
# def timeout_callback_stop(update, context):
#     query = update.callback_query
#     query.edit_message_text(
#         text='Прервали 🛑STOP, не было активностей',
#         # reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP])
#     )
#     update.effective_message.reply_text(
#         text='Вернулись в стартовое меню',
#         reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP]),
#     )
#
#
# def timeout_message_stop(update, context):
#     update.message.reply_text(
#         text='Прервали 🛑STOP, не было активностей',
#         reply_markup=keyboard_start(context.user_data[ID_USER_DATA_STOP])
#     )
#
#
# def stop_list(dispatcher):
#     dispatcher.add_handler(
#         ConversationHandler(
#         entry_points=[MessageHandler(Filters.regex(BUTTON_STOP_TITLE), stop_list_actions, pass_user_data=True)],
#         states={
#             DISPATCH: [CallbackQueryHandler(stop_list_dispatch, pass_user_data=True)],
#             ADD_PROVISION: [CallbackQueryHandler(stop_list_add_provision, pass_user_data=True)],
#             # ADD_AMOUNT: [CallbackQueryHandler(add_amount, pass_user_data=True)],
#             # ADD_WRITE_AMOUNT: [CallbackQueryHandler(add_write_amount, pass_user_data=True)],
#             ADD_WRITE: [CallbackQueryHandler(stop_list_add_write, pass_user_data=True)],
#             ADD_CONTINUE: [CallbackQueryHandler(stop_list_add_continue, pass_user_data=True)],
#             # REMOVE_VIEW_PROVISION: [CallbackQueryHandler(sl_remove_view_provision, pass_user_data=True)],
#             REMOVE_PROVISION: [CallbackQueryHandler(stop_list_remove_provision, pass_user_data=True)],
#             REMOVE_CONTINUE: [CallbackQueryHandler(stop_list_remove_continue, pass_user_data=True)],
#             # REMOVE_PROVISION: [CallbackQueryHandler(stop_list_remove_provision, pass_user_data=True)]
#             # DETAIL_COMMENT: [MessageHandler(Filters.text, error_check, pass_user_data=True)],
#             # CHECK_MESSAGE_ERROR: [CallbackQueryHandler(error_finish, pass_user_data=True)],
#             # ConversationHandler.TIMEOUT: [MessageHandler(Filters.text | Filters.command, timeout)],
#             ConversationHandler.TIMEOUT:
#                 [CallbackQueryHandler(timeout_callback_stop, pass_job_queue=True, pass_update_queue=True),
#                  MessageHandler(Filters.text | Filters.command, timeout_message_stop)],
#
#             # ConversationHandler.TIMEOUT: [
#             #     CallbackQueryHandler(timeout_callback_wait, pass_job_queue=True, pass_update_queue=True),
#             #     MessageHandler(Filters.text | Filters.command, timeout_message_wait)]
#
#
#         },
#         # ConversationHandler.conversation_timeout (stop_list_actions, pass_user_data=True),
#             fallbacks=[
#
#             MessageHandler(Filters.regex(BUTTON_STOP_CANCEL), stop_list_cancel, pass_user_data=True),
#         ],
#         conversation_timeout = CHAT_TIMEOUT
#         )
#     )
