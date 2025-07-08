import numpy as np
from telegram import ParseMode
from telegram.ext import ConversationHandler, MessageHandler, CallbackQueryHandler, Filters
from tabulate import tabulate

from Conversations.conversationWaiting import PRODUCT_NAME_WAITING
from class_StartKeyboard import keyboard_start
import os
from dotenv import load_dotenv

load_dotenv()
CHAT_TIMEOUT = int(os.getenv('CHAT_TIMEOUT'))
from decorators import check_group
from keyboards import BUTTON_DELIVERY_WAIT, keyboard_delivery_wait, CALLBCK_WRONG_BT_WHALE_DELV_WAIT, CALLBCK_WRONG_BT_MIN_DELV_WAIT, \
    OPEN_SESSION_DELIVERY_WAIT, MARKER_WAIT_DELIVERY_WAIT, BUTTON_DELIVERY_WAIT_CANCEL, keyboard_cancel_delivery_wait
from other_functions import column_breakdown
from postgres import query_postgre

ID_USER_CHAT, WHAT_WHALE, OPEN_SESSIONS, WAIT_SESSION, STORE_LIST, ID_MESSAGE_KEYBOARD, CHOOSE_STORE, CURRENT_TEXT,\
    TG_GR_NOT = range(9)
WRITE_WAIT, INPUT_DELIVERY_TIME = range(2)


INPUT_DELIVERY_MIN = '⏰'
DELIVERY_WAIT_MINUTES = ['30', '60', '90', INPUT_DELIVERY_MIN]
# PRODUCT_NAME_DELIVERY = '🚚'
PACKING_TIME = 10


def delivery_delay_look(update, context):

    # 1. проверить есть ли ожидания
    query_find_open_sessions = '''
                        SELECT store_name, now_wait, product_name
                        FROM wait_session
                        INNER JOIN store USING(id_store)
                        WHERE end_wait is NULL
                        ORDER BY store_name'''
    now_wait = np.array(query_postgre(query_find_open_sessions))
    # 2. создаем клавиатуру
    # 2.1 какие киты осуществляют доставку?
    query_db = '''
            SELECT store_name, basic_delivery_time
            FROM store
            WHERE delivery = TRUE
            ORDER BY store_name
        '''
    delivery_store = np.array(query_postgre(query_db))
    delivery_basic_time = delivery_store[:, 1]

    if now_wait.size > 0:
        now_waiting_status = column_breakdown(delivery_store[:, 0], PRODUCT_NAME_WAITING, now_wait, 1, 2, 0)
        # print(now_waiting_status)
        table_breakdown = tabulate(now_waiting_status, ['кит', '🍕', '🍔', '🚚'], tablefmt='rst')

        # какое время доставки: если нет ожидания - то ставится минимальное, если есть ожидание, то ожидание, без прибавления минимального
        delivery_final_wait = np.where(now_waiting_status[:, 3].astype(int) == 0,
                                       delivery_basic_time.astype(int) + PACKING_TIME,
                                       now_waiting_status[:, 3].astype(int))
        # время доставки пицца
        delivery_pizza = now_waiting_status[:, 1].astype(int) + delivery_final_wait.astype(int)

        # время доставки бургеры
        delivery_burger = now_waiting_status[:, 2].astype(int) + delivery_final_wait.astype(int)
        #сводная по суммарным ожиданиям пиццы и бургеров
        summary_waiting = np.c_[now_waiting_status[:, 0], delivery_pizza, delivery_burger]
        table_leadsheet = tabulate(summary_waiting, ['кит','🍕', '🍔'], tablefmt='rst')

        update.effective_message.reply_text(
            text="<pre>" + 'Выставлены ожидания к стандартым: \n' + table_breakdown + '\n\n'
                 + 'Итоговые ожидания доставки \n' + table_leadsheet + "</pre>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_start(update.message.chat_id, context),
        )
    else:
        basic_time = delivery_basic_time.astype(int) + PACKING_TIME
        summary_waiting = np.c_[delivery_store[:, 0], basic_time, basic_time]
        table_leadsheet = tabulate(summary_waiting, ['кит','🍕', '🍔'], tablefmt='rst')
        update.effective_message.reply_text(
            text="<pre>" + 'Ожиданий нет, базовое время доставки' + '\n\n' + table_leadsheet + "</pre>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_start(update.message.chat_id, context),
        )


@check_group
def delivery_wait_start(update, context):

    query_tg_group_notif = '''
        SELECT group_telegram_id
        FROM errors_departments
        WHERE department_name = 'Операторы'
        '''
    # context.user_data[TG_GR_NOT] = query_postgre(query_tg_group_notif)[0][0]
    context.user_data[TG_GR_NOT] = 189198380

    # delivery_delay_look(update, context)
    context.user_data[ID_USER_CHAT] = update.message.chat_id
    # 1. проверить есть ли ожидания
    query_find_open_sessions = '''
                    SELECT store_name, now_wait, product_name
                    FROM wait_session
                    INNER JOIN store USING(id_store)
                    WHERE end_wait is NULL
                    ORDER BY store_name'''
    now_wait = np.array(query_postgre(query_find_open_sessions))
    print(now_wait)

    # 2. создаем клавиатуру
    # 2.1 какие киты осуществляют доставку?
    query_db = '''
        SELECT store_name, basic_delivery_time
        FROM store
        WHERE delivery = TRUE
        ORDER BY store_name
    '''
    delivery_store = np.array(query_postgre(query_db))
    delivery_now_wait = []
    if now_wait.size > 0:
        delivery_now_wait = now_wait[np.where(now_wait[:, 2] == PRODUCT_NAME_WAITING[2])][:, [0, 1]]

    context.user_data[STORE_LIST] = delivery_store

    update.effective_message.reply_text(
                text="<pre>" + 'Выбрали ' + BUTTON_DELIVERY_WAIT + "</pre>",
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard_cancel_delivery_wait(),
            )

    update.effective_message.reply_text(
        text="<pre>" + "поменять ожидание (в мин.):\n чтобы убрать ожидание с точки - нажмите на нее \n" + "</pre>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard_delivery_wait(delivery_now_wait, delivery_store[:, 0], DELIVERY_WAIT_MINUTES),
    )
    return WRITE_WAIT


def callback_keyboard_processing(update, context):
    query = update.callback_query
    context.user_data[CURRENT_TEXT] = update.effective_message.text
    callback_data = query.data
    context.user_data[ID_MESSAGE_KEYBOARD] = query.message.message_id
    text = ''
    # now_situation = column_breakdown(PRODUCT_NAME_WAITING)
    #  тыкнули на название КИТа
    if callback_data == CALLBCK_WRONG_BT_WHALE_DELV_WAIT:
        context.bot.answer_callback_query(
            callback_query_id=query.id,
            text='Выбрать ожидание, а не точку',
            show_alert=True)
    #  тыкнули где уже есть ожидание
    elif callback_data == CALLBCK_WRONG_BT_MIN_DELV_WAIT:
        context.bot.answer_callback_query(
            callback_query_id=query.id,
            text='Ожидание уже выставлено',
            show_alert=True)
    #  остальные события уже обрабатываем
    else:
        #  если сессия ожидания уже есть на этой точке и меняем время ожидания
        if callback_data.split()[0] == OPEN_SESSION_DELIVERY_WAIT:
            store_name = callback_data.split()[1]
            context.user_data[CHOOSE_STORE] = store_name

            #  если выбрали выставить время вручную:

            if callback_data.split()[2] == INPUT_DELIVERY_MIN:
                #  убираем клавиатуру:
                query.edit_message_text(
                    text=context.user_data[CHOOSE_STORE] + " - выставите время в мин от 90 до 240",
                    parse_mode=ParseMode.HTML
                )

                # #  добавляем кнопку поставить на стоп точку:
                # update.effective_message.reply_text(
                #     text=store_name + " - выставите время в минутах от 90 до 240",
                #     reply_markup=keyboard_stop_or_cancel_delivery_wait(),
                # )
                return INPUT_DELIVERY_TIME
            else:
                now_wait = int(callback_data.split()[2])
                # находим открытые сессии на ожидание для конкретного кита
                query_wait_session_delivery_store = '''
                                                SELECT max_wait, id_wait_session
                                                FROM wait_session
                                                INNER JOIN store USING(id_store)
                                                WHERE end_wait is NULL and product_name = '{}' and store_name = '{}'
                                    '''.format(PRODUCT_NAME_WAITING[2], store_name)
                session = np.array(query_postgre(query_wait_session_delivery_store))[0]

                # callback_data.split() = {list: 3}['OPEN_SESSION_DELIVERY_WAIT', 'БК3', '⏰']
                # ['OPEN_SESSION_DELIVERY_WAIT', 'БК3', '90']
                id_wait_session = session[1]
                session_wait_max = session[0]
                max_wait = session_wait_max if session_wait_max > now_wait else now_wait
                q_update_session = '''
                    UPDATE wait_session
                    SET max_wait = {}, now_wait = {}
                    WHERE id_wait_session = {}'''.format(max_wait, now_wait, id_wait_session)
                query_postgre(q_update_session)
                q_wait_entry = '''
                    SET TIMEZONE='posix/Asia/Krasnoyarsk';
                    INSERT INTO wait_entry (date_time, wait_min, id_wait_session)
                    VALUES (date_trunc('minute', now()) ,{},{});'''.format(now_wait, id_wait_session)
                query_postgre(q_wait_entry)
                text = '\n⭕ изменили ожидание доставки в <b>' + store_name + '</b> ➔ ' + str(now_wait) + '\n'


        # если убираем сессию ожидания
        elif callback_data.split()[0] == MARKER_WAIT_DELIVERY_WAIT:
            store = callback_data.split()[1]  # узнаем в каком ките открыта сессия
            q_close_wait_session = '''
                SET TIMEZONE='posix/Asia/Krasnoyarsk';
                UPDATE wait_session
                SET end_wait = date_trunc('minute', now()), duration_wait = date_trunc('minute', (NOW() - begin_wait)), now_wait = 0
                WHERE(
                    SELECT id_store
                    FROM store
                    WHERE store_name = '{}'
                ) = id_store and end_wait is NULL and product_name = '{}' 
                RETURNING id_wait_session'''.format(store, PRODUCT_NAME_WAITING[2])
            id_wait_session = np.array(query_postgre(q_close_wait_session))[0][0]
            print('id_wait_session -', id_wait_session)
            # при закрытии добавляем entry
            q_wait_entry = '''
                                  SET TIMEZONE='posix/Asia/Krasnoyarsk';
                                  INSERT INTO wait_entry (date_time, wait_min, id_wait_session) VALUES
                                  (date_trunc('minute', now()) ,{},{});
                              '''.format(0, id_wait_session)
            query_postgre(q_wait_entry)
            text = '\n🔆 в ' + store + ' нет ожиданий \n'

        # если открываем новую сессию ожидания
        else:
            store_name = callback_data.split()[0]
            wait_min = callback_data.split()[1]

            # если выбрали выставить ожиадания самостоятельно
            if callback_data.split()[1] == INPUT_DELIVERY_MIN:
                context.user_data[CHOOSE_STORE] = store_name
                # убираем клавиатуру
                query.edit_message_text(
                    text=context.user_data[CHOOSE_STORE] + " - выставите время в мин от 90 до 240",
                    parse_mode=ParseMode.HTML
                )
                # добавляем клавиатуру со СТОПам всей заготовки
                # update.effective_message.reply_text(
                #     text=context.user_data[CHOOSE_STORE] + " - выставите время в мин от 90 до 240",
                #     reply_markup=keyboard_stop_or_cancel_delivery_wait(),
                # )

                return INPUT_DELIVERY_TIME
            else:
                # сессий открытых нет, т.к. клавиатура вернула бы иное как первый символ
                q_new_wait_session = '''
                    SET TIMEZONE='posix/Asia/Krasnoyarsk';
                    INSERT INTO wait_session (begin_wait, id_store, max_wait, product_name, now_wait)
                    SELECT date_trunc('minute', now()), store.id_store, {}, '{}',{}
                    FROM store
                    WHERE store.store_name = '{}'
                    RETURNING id_wait_session
                '''.format(wait_min, PRODUCT_NAME_WAITING[2], wait_min, store_name)
                id_wait_session = np.array(query_postgre(q_new_wait_session))[0, 0]
                q_new_wait_entry = '''
                            SET TIMEZONE='posix/Asia/Krasnoyarsk';
                            INSERT INTO wait_entry (date_time, wait_min, id_wait_session) VALUES
                            (date_trunc('minute', now()) ,{},{});'''.format(wait_min, id_wait_session)
                query_postgre(q_new_wait_entry)
                text = '\n❗️Поставили ожидание ' + PRODUCT_NAME_WAITING[2] + wait_min + " мин в " + store_name +'\n'

        # запрос к БД  - есть ли ожидание
        query_wait_session_delivery = '''
                    SELECT store_name, now_wait, product_name
                    FROM wait_session
                    INNER JOIN store USING(id_store)
                    WHERE end_wait is NULL and product_name = '{}'
                    ORDER BY store_name
        '''.format(PRODUCT_NAME_WAITING[2])
        delivery_now_wait = np.array(query_postgre(query_wait_session_delivery))
        delivery_store = np.array(context.user_data[STORE_LIST])

        context.bot.sendMessage(
            chat_id=context.user_data[TG_GR_NOT],
            text=text,
            parse_mode=ParseMode.HTML,
        )

        context.user_data[CURRENT_TEXT] = context.user_data[CURRENT_TEXT] + text
        query.edit_message_text(
            text=context.user_data[CURRENT_TEXT],
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_delivery_wait(delivery_now_wait, delivery_store[:, 0], DELIVERY_WAIT_MINUTES),
        )
    return WRITE_WAIT


def input_delivery_time(update, context):
    input_data = update.message.text
    if input_data.isnumeric():
        now_wait = int(input_data)
        # какие сейчас ожидания в точках
        query_wait_session_delivery_store = '''
            SELECT max_wait, id_wait_session
            FROM wait_session
            INNER JOIN store USING(id_store)
            WHERE end_wait is NULL and product_name = '{}' and store_name = '{}'
            '''.format(PRODUCT_NAME_WAITING[2], context.user_data[CHOOSE_STORE])
        # session = np.array(query_postgre(query_wait_session_delivery_store))[0]
        session = np.array(query_postgre(query_wait_session_delivery_store))
        # если нашли открытую сессию
        if session.size > 0:
                # callback_data.split() = {list: 3}['OPEN_SESSION_DELIVERY_WAIT', 'БК3', '⏰']
            # ['OPEN_SESSION_DELIVERY_WAIT', 'БК3', '90']
            session = session[0]
            id_wait_session = session[1]
            session_wait_max = session[0]
            max_wait = session_wait_max if session_wait_max > now_wait else now_wait
            q_update_session = '''
                                UPDATE wait_session
                                SET max_wait = {}, now_wait = {}
                                WHERE id_wait_session = {}'''.format(max_wait, now_wait, id_wait_session)
            query_postgre(q_update_session)
            q_wait_entry = '''
                                SET TIMEZONE='posix/Asia/Krasnoyarsk';
                                INSERT INTO wait_entry (date_time, wait_min, id_wait_session)
                                VALUES (date_trunc('minute', now()) ,{},{});'''.format(now_wait, id_wait_session)
            query_postgre(q_wait_entry)
        # если нет открытых сессий
        else:
            q_new_wait_session = '''
                                SET TIMEZONE='posix/Asia/Krasnoyarsk';
                                INSERT INTO wait_session (begin_wait, id_store, max_wait, product_name, now_wait)
                                SELECT date_trunc('minute', now()), store.id_store, {}, '{}',{}
                                FROM store
                                WHERE store.store_name = '{}'
                                RETURNING id_wait_session
                            '''.format(now_wait, PRODUCT_NAME_WAITING[2], now_wait, context.user_data[CHOOSE_STORE])
            id_wait_session = np.array(query_postgre(q_new_wait_session))[0, 0]
            q_new_wait_entry = '''
                                        SET TIMEZONE='posix/Asia/Krasnoyarsk';
                                        INSERT INTO wait_entry (date_time, wait_min, id_wait_session) VALUES
                                        (date_trunc('minute', now()) ,{},{});'''.format(now_wait, id_wait_session)
            query_postgre(q_new_wait_entry)

        # создаем новую клавиатуру
        query_find_open_sessions = '''
                                    SELECT store_name, now_wait, product_name
                                    FROM wait_session
                                    INNER JOIN store USING(id_store)
                                    WHERE end_wait is NULL
                                    ORDER BY store_name'''
        wait_sessions= np.array(query_postgre(query_find_open_sessions))
        delivery_now_wait = []
        if wait_sessions.size > 0:
            delivery_now_wait = wait_sessions[np.where(wait_sessions[:, 2] == PRODUCT_NAME_WAITING[2])][:, [0, 1]]
        delivery_store = np.array(context.user_data[STORE_LIST])
        text = '\n⭕ изменили ожидание доставки в <b>' + context.user_data[CHOOSE_STORE] + '</b> ➔ ' + str(now_wait) + '\n'
        context.user_data[CURRENT_TEXT] = context.user_data[CURRENT_TEXT] + text

        context.bot.sendMessage(
            chat_id=context.user_data[TG_GR_NOT],
            text=text,
            parse_mode=ParseMode.HTML,
        )

        update.effective_message.reply_text(
            text=context.user_data[CURRENT_TEXT],
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard_delivery_wait(delivery_now_wait, delivery_store[:, 0], DELIVERY_WAIT_MINUTES),
        )
        return WRITE_WAIT
    else:
        update.effective_message.reply_text(text="это не число")
    return INPUT_DELIVERY_TIME


def deivery_wait_cancel(update, context):

    update.message.reply_text(
        text='Ожидания выставлены',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
    )
    return ConversationHandler.END


def timeout_callback_deivery_wait(update, context):
    query = update.callback_query
    query.edit_message_text(
        text='Прервали ⏳Ожидание, не было активностей',
    )
    update.effective_message.reply_text(
        text='Вернулись в стартовое меню',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context),
    )


def conversation_delivery_waiting(dispatcher):
    dispatcher.add_handler(ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(BUTTON_DELIVERY_WAIT), delivery_wait_start, pass_user_data=True)],

        states={
            WRITE_WAIT: [CallbackQueryHandler(callback_keyboard_processing, pass_user_data=True)],
            INPUT_DELIVERY_TIME: [MessageHandler(Filters.regex(BUTTON_DELIVERY_WAIT_CANCEL), deivery_wait_cancel, pass_user_data=True),
                                  MessageHandler(Filters.text, input_delivery_time, pass_user_data=True)],
            # DETAIL_COMMENT: [MessageHandler(Filters.text, error_check, pass_user_data=True)],
            ConversationHandler.TIMEOUT: [
                CallbackQueryHandler(timeout_callback_deivery_wait, pass_job_queue=True, pass_update_queue=True),
                # MessageHandler(Filters.text | Filters.command, timeout_message_wait)
            ],
        },
        fallbacks=[MessageHandler(Filters.regex(BUTTON_DELIVERY_WAIT_CANCEL), deivery_wait_cancel, pass_user_data=True)],
        conversation_timeout=CHAT_TIMEOUT
    ))
