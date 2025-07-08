from telegram import KeyboardButton
from telegram import ReplyKeyboardMarkup
from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
import numpy as np


from gSheet import get_column_values, get_error_postions_from_gs


BUTTON_BREAK_TITLE = "🛠Поломка"
BUTTON_ERROR_TITLE = "📯Ошибка"
# BUTTON_STOP_TITLE = "🛑STOP"
BUTTON_WAIT_TITLE = "⏳Ожидание"
BUTTON_AVERAGE_CHECK = '💸 Средний чек'
BUTTON_STOCKS = '🖋 Запасы'
BUTTON_TRANSFER = '📦 Перемещение'
BUTTON_REGISTER = '📑 Зарегистрироваться'
BUTTON_WHAT_WHALE = "📍 Выбрать точку"
BUTTON_BM_SHIPMENT_CHECK = "Принять поставку"
BUTTON_DELIVERY_WAIT = '🚚 Поставить ожидание'
BUTTON_DELIVERY_TIME_WATCH = '👀 Посмотреть ожидания'

BUTTON_ERROR_CANCEL = '🙅️ Прервать внесение ошибки'
BUTTON_BREAK_CANCEL = "🙅️ Прервать внесение поломки"
BUTTON_STOP_CANCEL = "🙅️ Прервать и выйти"
BUTTON_CHOOSE_WHALE_CANCEL = "🔙 вернуться"
BUTTON_TRANSFER_CANCEL = "🙅️ Прервать внесение перемещения"
BUTTON_STOCKS_CANCEL = '🙅️ Прервать запасы'

BUTTON_WAIT_CANCEL = "🙅️ Прервать и выйти"
BUTTON_REMOVE_WAIT = "убрать_ожидание"

BUTTON_DELIVERY_WAIT_CANCEL = "Ожидания 🚚 выставлены"
BUTTON_DELIVERY_STOP = "🆘 поставить доставку на стоп"
BUTTON_STOP_RETURN_INLINE = "⬅"
BUTTON_CANCEL_CONVERSATION = 'Прервать'

# NOTIFICATION
BUTTON_NOTIFICATION_REMIND_CALLBACK = 'notification_remind_callback'
NOTIFICATION_SEPARATOR_SYMBOL = '%'


KEYBOARD_STOP_ACTIONS_CALLBACK = ["add_to_stop", "view_stop_list", "remove_from_stop_list"]
KEYBOARD_STOP_ACTIONS_TITLES = {
    KEYBOARD_STOP_ACTIONS_CALLBACK[0]: "на стоп",
    KEYBOARD_STOP_ACTIONS_CALLBACK[1]: "посмотреть стопы",
    KEYBOARD_STOP_ACTIONS_CALLBACK[2]: "снять со стопа",
}

KEYBOARD_STOP_AMOUNT_CALLBACK = [3, 5, 20, 50, 200, 500, 1000, 3000]
KEYBOARD_STOP_AMOUNT_TITLES = {
    KEYBOARD_STOP_AMOUNT_CALLBACK[0]: "меньше 3",
    KEYBOARD_STOP_AMOUNT_CALLBACK[1]: "меньше 5",
    KEYBOARD_STOP_AMOUNT_CALLBACK[2]: "меньше 20",
    KEYBOARD_STOP_AMOUNT_CALLBACK[3]: "меньше 50",
    KEYBOARD_STOP_AMOUNT_CALLBACK[4]: "меньше 200",
    KEYBOARD_STOP_AMOUNT_CALLBACK[5]: "меньше 500",
    KEYBOARD_STOP_AMOUNT_CALLBACK[6]: "меньше 1000",
    KEYBOARD_STOP_AMOUNT_CALLBACK[7]: "меньше 3000",
}

KEYBOARD_STOP_ADD_CONT_CALLBACK = ["another_stop", "exit"]
KEYBOARD_STOP_ADD_CONT_TITLES = {
    KEYBOARD_STOP_ADD_CONT_CALLBACK[0]: "ещё поставить на стоп в этой же точке",
    KEYBOARD_STOP_ADD_CONT_CALLBACK[1]: "выйти в меню",
}

KEYBOARD_STOP_DEL_CONT_CALLBACK = ["another_remove", "exit"]
KEYBOARD_STOP_DEL_CONT_TITLES = {
    KEYBOARD_STOP_DEL_CONT_CALLBACK[0]: "снять ещё",
    KEYBOARD_STOP_DEL_CONT_CALLBACK[1]: "выйти в меню",
}


def keyboard_cancel_wait():
    """
    cancel choose whale
    :return:
    """
    keyboard = [[KeyboardButton(BUTTON_WAIT_CANCEL)]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    # return ForceReply(keyboard=keyboard, resize_keyboard=True)

# ------------------------choose whale--------------------------------

def keyboard_cancel_choose_whale():
    """
    cancel choose whale
    :return:
    """
    keyboard = [[KeyboardButton(BUTTON_CHOOSE_WHALE_CANCEL)]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    # return ForceReply(keyboard=keyboard, resize_keyboard=True)

# ------------------------STOP LIST--------------------------------
# ------------------------STOP LIST--------------------------------
# def keyboard_add_cont():
#     keyboard = [
#         [
#             InlineKeyboardButton(KEYBOARD_STOP_ADD_CONT_TITLES[KEYBOARD_STOP_ADD_CONT_CALLBACK[0]],
#                                  callback_data=KEYBOARD_STOP_ADD_CONT_CALLBACK[0])
#             # InlineKeyboardButton(KEYBOARD_STOP_ADD_CONT_TITLES[KEYBOARD_STOP_ADD_CONT_CALLBACK[1]],
#             #                      callback_data=KEYBOARD_STOP_ADD_CONT_CALLBACK[1])
#         ],
#         [
#             InlineKeyboardButton(KEYBOARD_STOP_ADD_CONT_TITLES[KEYBOARD_STOP_ADD_CONT_CALLBACK[1]],
#                                  callback_data=KEYBOARD_STOP_ADD_CONT_CALLBACK[1])
#         ],
#     ]
#     return InlineKeyboardMarkup(keyboard)
#
#
# def keyboard_del_cont():
#     keyboard = [
#         [
#             InlineKeyboardButton(KEYBOARD_STOP_DEL_CONT_TITLES[KEYBOARD_STOP_DEL_CONT_CALLBACK[0]],
#                                  callback_data=KEYBOARD_STOP_DEL_CONT_CALLBACK[0]),
#             InlineKeyboardButton(KEYBOARD_STOP_DEL_CONT_TITLES[KEYBOARD_STOP_DEL_CONT_CALLBACK[1]],
#                                  callback_data=KEYBOARD_STOP_DEL_CONT_CALLBACK[1])
#         ],
#     ]
#     return InlineKeyboardMarkup(keyboard)
#
#
# def keyboard_stoplist_actions():
#     keyboard = [
#         [
#             InlineKeyboardButton(KEYBOARD_STOP_ACTIONS_TITLES[KEYBOARD_STOP_ACTIONS_CALLBACK[0]],
#                                  callback_data=KEYBOARD_STOP_ACTIONS_CALLBACK[0])
#         ],
#         [
#             InlineKeyboardButton(KEYBOARD_STOP_ACTIONS_TITLES[KEYBOARD_STOP_ACTIONS_CALLBACK[1]],
#                                  callback_data=KEYBOARD_STOP_ACTIONS_CALLBACK[1])
#         ],
#         [
#             InlineKeyboardButton(KEYBOARD_STOP_ACTIONS_TITLES[KEYBOARD_STOP_ACTIONS_CALLBACK[2]],
#                                  callback_data=KEYBOARD_STOP_ACTIONS_CALLBACK[2])
#         ],
#         # [
#         #     InlineKeyboardButton(KEYBOARD_STOP_ACTIONS_TITLES[KEYBOARD_STOP_ACTIONS_CALLBACK[3]],
#         #                          callback_data=KEYBOARD_STOP_ACTIONS_CALLBACK[3])
#         # ],
#     ]
#     return InlineKeyboardMarkup(keyboard)
#
#
# def keyboard_stoplist_amount():
#     keyboard = [
#         [
#             InlineKeyboardButton(KEYBOARD_STOP_AMOUNT_TITLES[KEYBOARD_STOP_AMOUNT_CALLBACK[0]],
#                                  callback_data=KEYBOARD_STOP_AMOUNT_CALLBACK[0]),
#             InlineKeyboardButton(KEYBOARD_STOP_AMOUNT_TITLES[KEYBOARD_STOP_AMOUNT_CALLBACK[1]],
#                                  callback_data=KEYBOARD_STOP_AMOUNT_CALLBACK[1]),
#         ],
#         [
#             InlineKeyboardButton(KEYBOARD_STOP_AMOUNT_TITLES[KEYBOARD_STOP_AMOUNT_CALLBACK[2]],
#                                  callback_data=KEYBOARD_STOP_AMOUNT_CALLBACK[2]),
#             InlineKeyboardButton(KEYBOARD_STOP_AMOUNT_TITLES[KEYBOARD_STOP_AMOUNT_CALLBACK[3]],
#                                  callback_data=KEYBOARD_STOP_AMOUNT_CALLBACK[3]),
#         ],
#         [
#             InlineKeyboardButton(KEYBOARD_STOP_AMOUNT_TITLES[KEYBOARD_STOP_AMOUNT_CALLBACK[4]],
#                                  callback_data=KEYBOARD_STOP_AMOUNT_CALLBACK[4]),
#             InlineKeyboardButton(KEYBOARD_STOP_AMOUNT_TITLES[KEYBOARD_STOP_AMOUNT_CALLBACK[5]],
#                                  callback_data=KEYBOARD_STOP_AMOUNT_CALLBACK[5]),
#         ],
#         [
#             InlineKeyboardButton(KEYBOARD_STOP_AMOUNT_TITLES[KEYBOARD_STOP_AMOUNT_CALLBACK[6]],
#                                  callback_data=KEYBOARD_STOP_AMOUNT_CALLBACK[6]),
#             InlineKeyboardButton(KEYBOARD_STOP_AMOUNT_TITLES[KEYBOARD_STOP_AMOUNT_CALLBACK[7]],
#                                  callback_data=KEYBOARD_STOP_AMOUNT_CALLBACK[7]),
#         ],
#     ]
#     return InlineKeyboardMarkup(keyboard)
#
#
# def keyboard_stoplist_now():
#     pass
#
#
# def keyboard_stoplist_provision(provisions_avaliable):
#     provision_for_keyboard = np.array(provisions_avaliable[:, 1])
#     keyboard = [[] for _ in range(len(provision_for_keyboard))]
#     count = 0
#     col_amount = 2
#     for i in provision_for_keyboard:
#         rt = int(count / col_amount)
#         keyboard[int(rt)].append(InlineKeyboardButton(i, callback_data=i))
#         count += 1
#
#     return InlineKeyboardMarkup(keyboard)
#
#
# def keyboard_cancel_stoplist():
#     """
#     старотвая стационарная клавиатура
#     :return:
#     """
#     keyboard = [[KeyboardButton(BUTTON_STOP_CANCEL)]]
#     return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
#     # return ForceReply(keyboard=keyboard, resize_keyboard=True)
#
# # KeyboardButton(BUTTON_STOP_TITLE)



# ---------------------OVERALL-----------------------------------

# да/нет клавиатура
def keyboard_yes_no():
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data="Yes"),
            InlineKeyboardButton("Нет", callback_data="No")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def keyboard_from_column(sheet_name, col_number: int, start: int, finish: int, col_amount: int):
    """
    столбце в googlesheet в inline keyboard
    :param sheet_name: c какого листа берем значения
    :param col_number: с какой колонки в листе берем
    :param col_amount: сколько столбцов в клавиатуре
    :return: inline клавиатуру
    """
    values_from_cell = get_column_values(sheet_name, col_number, start, finish)
    keyboard = [[] for _ in range(len(values_from_cell))]
    count = 0

    for cell_value in values_from_cell:
        rt = int(count / col_amount)
        keyboard[int(rt)].append(InlineKeyboardButton(cell_value, callback_data=cell_value))
        count += 1

    return InlineKeyboardMarkup(keyboard)


# подтверждение получения клавиатура
def keyboard_accept_read():
    keyboard = [
        [
            InlineKeyboardButton("Confirm", callback_data="accept"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

# dict_test = [{'id_department': 2, 'department_name': 'Бургермейкер'}, {'id_department': 1, 'department_name': 'Фабрика'}]

def keyboard_from_dict(list_of_dict: list, button_title: str, callback_title: str, col_amount: int):
    '''

    :param list_of_dict:  [{'id_department': 2, 'department_name': 'Бургермейкер'}, {'id_department': 1, 'department_name': 'Фабрика'}]
    :param button_title:  'department_name'
    :param callback:   'id_department'
    :param col_amount:
    :return:
    '''

    keyboard = [[] for _ in range(len(list_of_dict))]
    [keyboard[int(counter / col_amount)].append(InlineKeyboardButton(x[button_title], callback_data=x[callback_title])) for counter, x in
     enumerate(list_of_dict)]
    return InlineKeyboardMarkup(keyboard)


def keyboard_from_list(list_values, col_amount: int):
    """
    клавиатура из массива
    :param list_values: массив для клавиатуры
    :param col_amount: сколко колонок лавиатура
    :return: Inlinekeybaord
    """

    keyboard = [[] for _ in range(len(list_values))]
    count = 0

    for cell_value in list_values:
        rt = int(count / col_amount)
        keyboard[int(rt)].append(InlineKeyboardButton(cell_value, callback_data=cell_value))
        count += 1

    return InlineKeyboardMarkup(keyboard)



def keyboard_from_enum(enum_obj, col_amount: int):
    """
    клавиатура из массива
    :param list_values: массив для клавиатуры
    :param col_amount: сколко колонок лавиатура
    :return: Inlinekeybaord
    """

    keyboard = [[] for _ in enum_obj]
    [keyboard[int(counter / col_amount)].append(InlineKeyboardButton(e.value, callback_data=e.name)) for counter, e in enumerate(enum_obj)]
    return InlineKeyboardMarkup(keyboard)


# ---------------------ERROR-----------------------------------


def keyboard_cancel_error():
    """
    старотвая стационарная клавиатура
    :return:
    """
    keyboard = [[KeyboardButton(BUTTON_ERROR_CANCEL)]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# должности
def keyboard_position():
    keyboard = [[], [], [], []]
    counterKeyboard = 0

    for post in get_error_postions_from_gs():
        keyboard[int(counterKeyboard / 2)].append(InlineKeyboardButton(post, callback_data=post))
        counterKeyboard += 1

    return InlineKeyboardMarkup(keyboard)


# ---------------------BREAKAGE-----------------------------------


def keyboard_cancel_breakage():
    """
    старотвая стационарная клавиатура
    :return:
    """
    keyboard = [[KeyboardButton(BUTTON_BREAK_CANCEL)]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def keyboard_critical():
    keyboard = [
        [
            InlineKeyboardButton("Критична", callback_data="Критична"),
        ],
        [
            InlineKeyboardButton("⏳ Поломка некритична", callback_data="Некритическая"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


CALLBCK_WRONG_BT_WHALE_DELV_WAIT = 'Nope'
CALLBCK_WRONG_BT_MIN_DELV_WAIT = 'already exposed'
OPEN_SESSION_DELIVERY_WAIT = 'OPEN_SESSION_DELIVERY_WAIT'
MARKER_WAIT_DELIVERY_WAIT = '🔴'


def keyboard_delivery_wait(now_wait, delivery_store, WAIT_MINUTES):
    sym_dev_st = '🟢 '
    now_wait = np.array(now_wait)
    # print(now_wait.size)
    # print(type(now_wait), '',now_wait)
    # print(type(delivery_store), '',delivery_store )
    keyboard = [[] for i in delivery_store]
    if now_wait.size > 0:
        for s in range(delivery_store.size):
            ind_store = np.where(now_wait[:, 0] == delivery_store[s])[0]  # если в этой точке ожидание доставки
            if ind_store.size > 0:
                keyboard[s].append(InlineKeyboardButton(MARKER_WAIT_DELIVERY_WAIT + delivery_store[s], callback_data=MARKER_WAIT_DELIVERY_WAIT + " " + delivery_store[s]))
                for t in range(len(WAIT_MINUTES)):
                    ind_min = np.where(now_wait[ind_store, 1] == WAIT_MINUTES[t])[0]
                    if ind_min.size > 0:
                        keyboard[s].append(
                            InlineKeyboardButton('❗' + WAIT_MINUTES[t], callback_data=CALLBCK_WRONG_BT_MIN_DELV_WAIT))
                    else:
                        keyboard[s].append(
                            InlineKeyboardButton(WAIT_MINUTES[t], callback_data=OPEN_SESSION_DELIVERY_WAIT + " " + delivery_store[s] + " " + WAIT_MINUTES[t]))
            else:
                keyboard[s].append(InlineKeyboardButton(sym_dev_st + delivery_store[s], callback_data=CALLBCK_WRONG_BT_WHALE_DELV_WAIT))
                for t in range(len(WAIT_MINUTES)):
                    keyboard[s].append(
                        InlineKeyboardButton(WAIT_MINUTES[t], callback_data=delivery_store[s] + " " + WAIT_MINUTES[t]))
    else:
        for s in range(delivery_store.size):
            keyboard[s].append(InlineKeyboardButton(sym_dev_st + delivery_store[s], callback_data=CALLBCK_WRONG_BT_WHALE_DELV_WAIT))
            for t in range(len(WAIT_MINUTES)):
                keyboard[s].append(
                    InlineKeyboardButton(WAIT_MINUTES[t], callback_data=delivery_store[s] + " " + WAIT_MINUTES[t]))

    # keyboard[-1].append(InlineKeyboardButton('всё внесено', callback_data='22'))
    return InlineKeyboardMarkup(keyboard)


def keyboard_cancel_delivery_wait():
    """старотвая стационарная клавиатура
        :return:
    """
    keyboard = [[KeyboardButton(BUTTON_DELIVERY_WAIT_CANCEL)]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def keyboard_stop_or_cancel_delivery_wait():
    # [[KeyboardButton(BUTTON_BREAK_TITLE), KeyboardButton(BUTTON_ERROR_TITLE)],
    #  [KeyboardButton(BUTTON_STOP_TITLE), KeyboardButton(BUTTON_WAIT_TITLE)]]


    keyboard = [
        [KeyboardButton(BUTTON_DELIVERY_WAIT_CANCEL)],
                [KeyboardButton(BUTTON_DELIVERY_STOP)]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# ---------------------TRANSFER-----------------------------------

def keyboard_cancel_transfer():
    """
    старотвая стационарная клавиатура
    :return:
    """
    keyboard = [[KeyboardButton(BUTTON_TRANSFER_CANCEL)]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    # return ForceReply(keyboard=keyboard, resize_keyboard=True)


# ---------------------STOCKS-----------------------------------

def keyboard_cancel_conversation() -> ReplyKeyboardMarkup:
    """
    старотвая стационарная клавиатура
    :return:
    """
    keyboard = [[KeyboardButton(BUTTON_CANCEL_CONVERSATION)]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    # return ForceReply(keyboard=keyboard, resize_keyboard=True)


# ---------------------NOTIFICATION-----------------------------------

def keyboard_remind(id_notification: int) -> InlineKeyboardMarkup:
    callback = str(id_notification) + NOTIFICATION_SEPARATOR_SYMBOL + BUTTON_NOTIFICATION_REMIND_CALLBACK
    keyboard = [
        [
            InlineKeyboardButton('Сделано|прочтено', callback_data=callback),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
