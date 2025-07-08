import tracemalloc

import numpy as np

from postgres import query_postgre








def column_breakdown(row_array, col_array, entry_array, col_amount, col_headers, col_to_row):
    '''
    :param colums_array: по каким столбцам разбивать записи
    :param entry_array: записи, которые разбиваем
    :param col_amount: в какой колонке записей entry_array находятся данные
    :param col_headers: в какой колонке записей entry_array находятся колонки результирующей таблицы
    :param col_to_row: в какой колонке записей entry_array находятся строки результирующей таблицы
    :return: результат - без заголовков колонок на шаблоне из 0
    '''

    entry_array = np.array(entry_array)
    col_array = np.array(col_array)
    row_array = np.array(row_array)
    if entry_array.size > 0 and col_array.size > 0 and row_array.size > 0:
        # 1й столбец - уникальные значения из колонки записей
        result = row_array
        # создаем шаблон из 0 - куда будем вставлять данные
        nf = [0 for _ in result]
        for _ in col_array:
            result=np.c_[result, nf]

        for e in entry_array:
            col_in = np.where(e[col_headers] == col_array)[0][0]
            row_in = np.where(e[col_to_row] == result[:, col_to_row])[0][0]
            result[row_in, col_in+1] = e[col_amount]
        return result
    else:
        return None

#
#
# PRODUCT_NAME_WAITING = ['🍕', '🍔', '🚚']
# open_sessions= [
#         ['БК2', '20', '🍕'],
#         ['БК2', '20', '🍔'],
#         ['БК3', '30', '🚚'],
#         ['БК5', '20', '🍔']]
#
# now_waiting_status = column_breakdown(PRODUCT_NAME_WAITING, open_sessions, 1, 2, 0)
# print(now_waiting_status)
# # delivery_burger = np.sum(now_waiting_status[:, 1].astype(int), now_waiting_status[:, 3].astype(int))
# delivery_burger = now_waiting_status[:, 1].astype(int) + now_waiting_status[:, 3].astype(int)
# print(delivery_burger)




# ans =['10 🍕']
# 10 🍕
# 10 🍔
# 15 🍕
# 15 🍔
# 20 🍕
# 20 🍔
# 25 🍕
# 25 🍔
# 30 🍕
# 30 🍔

# print(ans[0].split())

# def validate_amount(text: str):
#     try:
#         amount = int(text)
#     except (TypeError, ValueError):
#         return None
#     if amount < 0:
#         return None
#     else:
#         return amount
#
#
# WAIT_MINUTES = ['10', '15', '20', '25', '30']
# products_postgre = np.array(query_postgre('SELECT product_name FROM product_type')).flatten()
# print(products_postgre)
#
#
# buttons = []
# for i in WAIT_MINUTES:
#     for j in products_postgre:
#         cur = i + " " + j
#         buttons.append(cur)
#
# print(buttons)



# t0 = time.time()
#     buttons_wait = []
#     t1 = time.time()
#     for i in WAIT_MINUTES:
#         for j in PRODUCT_NAME:
#             cur = i + " " + j
#             buttons_wait.append(cur)
#     t2 = time.time()
#     update.effective_message.reply_text(
#         text=text,
#         reply_markup=keyboard_from_list(buttons_wait, 2),
#     )
#     t3 = time.time()
#
#     print('Pgre query ',t1 - t0)
#     print('for ', t2 - t1)
#     print('mess ', t3 - t2)



# def validate_age(text: str) -> Optional[int]:
#     try:
#         age = int(text)
#     except (TypeError, ValueError):
#         return None
#
#     if age < 0 or age > 100:
#         return None
#     return age



# https://bitbucket.org/vkasatkin/tele_bot/src/master/decorators/main.py
# def log_errors(f):
#
#     def inner(*args, **kwargs):
#         try:
#             return f(*args, **kwargs)
#         except Exception as e:
#             error_message = f'[ADMIN] Произошла ошибка: {e}'
#             print(error_message)
#
#             update = args[0]
#             if update and hasattr(update, 'message'):
#                 # Сообщение о любой ошибке всегда отправляется главному админу
#                 update.message.bot.send_message(
#                     chat_id=MAIN_ADMIN_ID,
#                     text=error_message,
#                 )
#
#                 # Отправлять сообщение об ошибке только если она произошла у вас
#                 # chat_id = update.message.chat_id
#                 # if chat_id in ADMIN_IDS:
#                 #     update.message.reply_text(
#                 #         text=error_message,
#                 #     )
#
#             raise e
#
#     return inner

# https://bitbucket.org/vkasatkin/tele_bot/src/master/echo/utils.py
# def logger_factory(logger):
#     """ Импорт функции происходит раньше чем загрузка конфига логирования.
#         Поэтому нужно явно указать в какой логгер мы хотим записывать.
#     """
#     def debug_requests(f):
#
#         @functools.wraps(f)
#         def inner(*args, **kwargs):
#
#             try:
#                 logger.debug('Обращение в функцию `{}`'.format(f.__name__))
#                 return f(*args, **kwargs)
#             except Exception as e:
#                 logger.exception('Ошибка в функции `{}`'.format(f.__name__))
#                 sentry_sdk.capture_exception(error=e)
#                 raise
#
#         return inner
#
#     return debug_requests




# def stop_list_add_write(update, context):
#     query = update.callback_query
#     provision = query.data
#     context.user_data[PROVISION_DATA_STOP] = provision
#     try:
#         result_write = stop_list_add(context.user_data[ID_USER_DATA_STOP], provision,
#                                      context.user_data[WHALE_DATA_STOP], None)
#         if result_write.isdigit():
#             query.edit_message_text(
#                 text=('Поставили на стоп: {}\n'
#                       'Точка: {}\n'
#                       'След.действие:'.format(context.user_data[PROVISION_DATA_STOP],
#                                               context.user_data[WHALE_DATA_STOP])),
#                 # reply_markup=keyboard_stoplist_provision(provisions_available),
#             )
#         else:
#             context.bot.sendMessage(
#                 chat_id=ERROR_ADMIN_ID,
#                 text=str(result_write) + str(' ошибка add_write')
#             )
#             update.effective_message.reply_text(
#                 text='Произошла ошибка, о ней сообщено. Диалог прерван',
#                 reply_markup=keyboard_start())
#             return ConversationHandler.END
#     except:
#         context.bot.sendMessage(
#             chat_id=ERROR_ADMIN_ID,
#             text='STOP: ошибка в stop_list_add_write - записи в stop лист'
#         )
#         update.effective_message.reply_text(
#             text='Произошла ошибка, о ней сообщено. Диалог прерван',
#             reply_markup=keyboard_start())
#         return ConversationHandler.END


# "message":{"message_id":8,
#   "from":{"id":1203303922,"is_bot":false,"first_name":"anton2","last_name":"sukhanov2","username":"sukhanov2","language_code":"ru"},
#   "chat":{"id":-1001367452393,"title":"test_gr","type":"supergroup"},
#   "date":1607170333,
#   "new_chat_participant":{"id":779562442,"is_bot":true,"first_name":"\ud83d\udc0b + \ud83e\udd16","username":"BW_Trouble_bot"},
#   "new_chat_member":{"id":779562442,"is_bot":true,"first_name":"\ud83d\udc0b + \ud83e\udd16","username":"BW_Trouble_bot"},
#   "new_chat_members":[{"id":779562442,"is_bot":true,"first_name":"\ud83d\udc0b + \ud83e\udd16","username":"BW_Trouble_bot"}]}}]}