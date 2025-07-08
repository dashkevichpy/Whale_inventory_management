import gc
from datetime import datetime
from typing import Union
import pytz
from tabulate import tabulate
from telegram import ParseMode
from telegram.ext import ConversationHandler, CallbackQueryHandler, MessageHandler, Filters, CommandHandler

from Conversations.conversationChooseWhale import reset_store_employee
from Whale_inventory_management.class_WhaleSheet import InventSheet, INVENT_SHEET_NAME, WriteOffSheet, WriteOffType, \
    wr_off_init, ACCEPTANCE_SHEET_NAME, MORNING_INVENT_SHEET_NAME
from Whale_inventory_management.invent_postgres import pg_insert_fake_write_off, pg_get_invent_template, \
    pg_get_acceptance_whale_template
from Whale_inventory_management.report_and_check import check_write_off_done, check_invent_done, check_completed_invent, \
    check_invent_acceptance_done, check_invent_morning_done
from class_StartKeyboard import keyboard_start, Employee
import os
from dotenv import load_dotenv

load_dotenv()
CHAT_TIMEOUT = int(os.getenv('CHAT_TIMEOUT'))
ERROR_ADMIN_ID = os.getenv('ERROR_ADMIN_ID')
TIME_ZONE = os.getenv('TIME_ZONE')
STOCK_CLOSING_START = os.getenv('STOCK_CLOSING_START')
STOCK_CLOSING_END = os.getenv('STOCK_CLOSING_END')


from keyboards import BUTTON_STOCKS, BUTTON_CANCEL_CONVERSATION, keyboard_cancel_conversation, \
    keyboard_from_list
from enum import Enum
from collections import namedtuple

from postgres import pg_get_employee_in_store
import logging


logging.basicConfig(level=logging.INFO, filename='appStock.log', filemode='w',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

DISPATCH_HANDLER = range(1)
ID_MESSAGE_TO_DELETE, SERVICE_MESSAGE, ID_USER_CHAT = range(3)
ADMIN_STOCK_TEL_ID = []
# 189198380

BUTTON_INVENT = "🧮 отправить Инвентаризацию"
BUTTON_WRITE_OFF = "🗑 отправить Списание"
BUTTON_TMRR_WRITE_OFF = "📅 отравить Завтра списание"
BUTTON_MORNING_INVENT = "☀️отправить Утро инвент"
BUTTON_WRITE_OFF_REJECTION = "Нет списаний"
BUTTON_SHIPMENT_ACCEPTANCE = "📦 Принять транспортировку"
BUTTON_ADD_STOP_LIST = "⛔ Стоп"


START_STOCK_EVENING_TIME = datetime.strptime(STOCK_CLOSING_START, "%H:%M:%S")
END_STOCK_EVENING_TIME = datetime.strptime(STOCK_CLOSING_END, "%H:%M:%S")

START_SHIPMENT_ACCEPTANCE_TIME = datetime.strptime("08:00:00", "%H:%M:%S")
END_SHIPMENT_ACCEPTANCE_TIME = datetime.strptime("15:00:00", "%H:%M:%S")

START_STOCK_MORNING_TIME = datetime.strptime("08:00:00", "%H:%M:%S")
END_STOCK_MORNING_TIME = datetime.strptime("11:00:00", "%H:%M:%S")  # поменть время

StockEvent = namedtuple('StockEvent', ('button', 'time_start', 'time_end', 'check_func'))
StockKeyboardText = namedtuple('StockKeyboardText', {'text', 'keyboard'})

class StockEventList(Enum):
    INVENT = StockEvent(BUTTON_INVENT, START_STOCK_EVENING_TIME, END_STOCK_EVENING_TIME, check_invent_done)
    WRITE_OFF = StockEvent(BUTTON_WRITE_OFF, START_STOCK_EVENING_TIME, END_STOCK_EVENING_TIME, check_write_off_done)
    TMRR_WRITE_OFF = StockEvent(BUTTON_TMRR_WRITE_OFF, START_STOCK_EVENING_TIME, END_STOCK_EVENING_TIME, None)
    WRITE_OFF_REJECTION = StockEvent(BUTTON_WRITE_OFF_REJECTION, START_STOCK_EVENING_TIME, END_STOCK_EVENING_TIME, None)
    SHIPMENT_ACCEPTANCE = StockEvent(BUTTON_SHIPMENT_ACCEPTANCE, START_SHIPMENT_ACCEPTANCE_TIME,
                                     END_SHIPMENT_ACCEPTANCE_TIME, check_invent_acceptance_done)

    MORNING_INVENT = StockEvent(BUTTON_MORNING_INVENT, START_STOCK_MORNING_TIME,
                                     END_STOCK_MORNING_TIME, check_invent_morning_done)


def event_now(empl: Employee) -> dict:
    '''
        какие события происходяn сейчас
    :return:
    '''
    now = datetime.now(tz=pytz.timezone(TIME_ZONE))
    list_button = {}
    for e in StockEventList:
        fl_add_button = False  # чтобы не повторять участок кода

        if e.value.time_start.time() > e.value.time_end.time():  # значит это до и после полуночи
            if now.time() >= e.value.time_start.time() or now.time() <= e.value.time_end.time():
                fl_add_button = True
        else:
            if e.value.time_start.time() <= now.time() <= e.value.time_end.time():
                fl_add_button = True

        if fl_add_button:
            if e.value.check_func:
                list_button[e.value.button] = e.value.check_func(empl)
            else:
                list_button[e.value.button] = True
    return list_button


def keyboard_stock(context) -> Union[StockKeyboardText, None]:
    empl = context.user_data['employee']
    buttons = event_now(empl)
    if not buttons:
        return None
    text_header = f'Запасы для {empl.store_name}\n\n'
    text = ''
    # если уже внесено списание - удаляем конпку "инвентаризация"
    if BUTTON_INVENT in buttons.keys():
        if buttons[BUTTON_INVENT]:  # инвент выполнена
            del buttons[BUTTON_INVENT]
            text = 'инвентаризация уже отправлена, доступны только списания'

    # если нет не списания ни инвента - удаляем кнопку "инвентаризация"
    if BUTTON_WRITE_OFF in buttons.keys() and BUTTON_INVENT in buttons.keys():  # списание и инвент есть одновременно
        if not buttons[BUTTON_WRITE_OFF] and not buttons[BUTTON_INVENT]:  # инвент и списание не выполнены
            del buttons[BUTTON_INVENT]
            text = 'отправьте списание'

    #  если уже вносили списание - удаляем кнопку "списаний не было"
    if BUTTON_WRITE_OFF in buttons.keys() and BUTTON_WRITE_OFF_REJECTION in buttons.keys():
        if buttons[BUTTON_WRITE_OFF]:  # есть списание
            del buttons[BUTTON_WRITE_OFF_REJECTION]

    #  если уже вносили прием накладной - удаляем кнопку "Премка поставки"
    if BUTTON_SHIPMENT_ACCEPTANCE in buttons.keys():
        if buttons[BUTTON_SHIPMENT_ACCEPTANCE]:
            del buttons[BUTTON_SHIPMENT_ACCEPTANCE]

    #  если уже вносили утреннюю инвентаризацию
    if BUTTON_MORNING_INVENT in buttons.keys():
        if buttons[BUTTON_MORNING_INVENT]:
            del buttons[BUTTON_MORNING_INVENT]

    if not buttons:
        return None
    text = f'{text_header}' + text
    return StockKeyboardText(text=text, keyboard=keyboard_from_list(list(buttons.keys()), 1))


# @check_group
def start_stock_conversation(update, context):
    context.user_data[ID_USER_CHAT] = update.message.chat_id
    logging.info(f'start_stock_conversation {update.message.chat_id} \n')
    store_name = pg_get_employee_in_store(update.message.chat_id)  # отметил ли сотрудник точку, где сейчас
    if not store_name:
        update.message.reply_text(
            text='Сначала выбери точку, где работаешь',
            reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
        )
        return ConversationHandler.END

    update.message.reply_text(
        text=f"Ты работаешь сегодня в\n<b>{context.user_data['employee'].store_name}</b>?\n"
             f"Если нет, то поменяй точку /reset_store",
        reply_markup=keyboard_cancel_conversation(),
        parse_mode=ParseMode.HTML,
    )

    stock_keyb_text = keyboard_stock(context)

    if not stock_keyb_text:
        update.message.reply_text(
            text='Нет доступных интервалов',
            reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
        )
        return ConversationHandler.END

    update.message.reply_text(
        text=stock_keyb_text.text,
        reply_markup=stock_keyb_text.keyboard
    )
    context.user_data[ID_MESSAGE_TO_DELETE] = [update.message.message_id + 1,  update.message.message_id + 2]
    context.user_data[SERVICE_MESSAGE] = None
    return DISPATCH_HANDLER


def stock_dispatch_handler(update, context):

    query = update.callback_query
    query.edit_message_text(
        text="⏳ обработка...",
    )
    emp = context.user_data['employee']
    logging.info(f'press {query.data} {context.user_data[ID_USER_CHAT]}, store -{emp.store_name}, '
                 f'dept - {emp.department_code}  \n')

    # инвентаризация
    if query.data == BUTTON_INVENT:
        if check_invent_done(context.user_data['employee']):
            query.answer(text='❌ Инвентаризация уже внесена', show_alert=True)
            text = '\n❌ инвент внесена'
        else:
            invent_whale_sheet = InventSheet(em=emp, sheet=INVENT_SHEET_NAME,
                                             func_get_nomenclature=pg_get_invent_template, invent_type=None)
            if invent_whale_sheet.get_result():
                query.answer(text='🙌 Отлично, инвентаризация внесена', show_alert=True)
                text = '\n✔️инвент отправлен'
                incompleted_invent = check_completed_invent()
                if incompleted_invent:  # если есть инвентаризации, которые надо отправить
                    table_inc = tabulate(incompleted_invent, tablefmt="rst")
                    context.bot.sendMessage(chat_id=ERROR_ADMIN_ID,
                                            text='📨 Заполнили инвент {store_name} - {dept} осталось ещё \n {inc}'.
                                            format(store_name=emp.store_name, dept=emp.department_code, inc=table_inc))
                else:  # если отправлены все инвенты
                    context.bot.sendMessage(chat_id=ERROR_ADMIN_ID, text='🎉 Все инвент заполнены')
            else:
                query.answer(text='❌ Что-то внесли не так🤨, смотри в колонке Ошибка заполнения', show_alert=True)
                text = '\n❌ ошибка инвент'
            del invent_whale_sheet
            gc.collect()

    # списание сегодня
    elif query.data == BUTTON_WRITE_OFF:
        write_off = wr_off_init(em=emp, write_off_type=WriteOffType.WRITE_OFF_TODAY, wb=None)
        w_result = write_off.get_result()
        if w_result is None:
            query.answer(text='🙄 Нечего вносить в списание', show_alert=True)
            text = '\n - в списание нечего вносить'
        elif w_result:
            query.answer(text='👍 Списание внесено', show_alert=True)
            text = '\n✔️списание за сегодня отправлено'
        else:
            query.answer(text='❌ Ошибка в листе Списание, колонка Ошибка заполнения',show_alert=True)
            text = '\n❌ ошибка списания'
        del write_off
        gc.collect()

    # сегодня списаний не было
    elif query.data == BUTTON_WRITE_OFF_REJECTION:  # если списаний сегодня нет, вносим мнимое списание
        pg_insert_fake_write_off(emp.id_store, emp.department_code)
        text = '\n⚠ списаний не было'

    # списание завтра
    elif query.data == BUTTON_TMRR_WRITE_OFF:
        text = f'\n\n {BUTTON_TMRR_WRITE_OFF} пока неактивно, запустим позже'

        # write_off_tmrr = wr_off_init(em=emp, write_off_type=WriteOffType.WRITE_OFF_TMRR, wb=None)
        # w_result = write_off_tmrr.get_result()
        # if w_result is None:
        #     query.answer(text='🙄 Нечего вносить в списание', show_alert=True)
        #     text = '\n - в списание нечего вносить'
        # elif w_result:
        #     query.answer(text='👍 Списание внесено', show_alert=True)
        #     text = '\n✔️списание за сегодня отправлено'
        # else:
        #     query.answer(text='❌ Ошибка в листе Списание, колонка Ошибка заполнения', show_alert=True)
        #     text = '\n❌ ошибка списания'
        # del write_off_tmrr
        # gc.collect()

    # принятие транспортировки
    elif query.data == BUTTON_SHIPMENT_ACCEPTANCE:
        invent_whale_sheet = InventSheet(em=emp, sheet=ACCEPTANCE_SHEET_NAME,
                                         func_get_nomenclature=pg_get_acceptance_whale_template, invent_type='acceptance')
        if invent_whale_sheet.get_result():
            query.answer(text='🙌 Приемка транспортировки внесена', show_alert=True)
            text = '\n✔️приемка отправлена'
            context.bot.sendMessage(chat_id=ERROR_ADMIN_ID, text='📦 Приемка внесена {dept} - {store_name}'.
                                    format(store_name=emp.store_name, dept=emp.department_code))
        else:
            query.answer(text='❌ Что-то внесли не так🤨, смотри в колонке Ошибка заполнения', show_alert=True)
            text = '\n❌ ошибка приемка'
        del invent_whale_sheet
        gc.collect()

    # инвентаризация утро
    elif query.data == BUTTON_MORNING_INVENT:
        invent_whale_sheet = InventSheet(em=emp, sheet=MORNING_INVENT_SHEET_NAME,
                                         func_get_nomenclature=pg_get_acceptance_whale_template,
                                         invent_type='morning')
        if invent_whale_sheet.get_result():
            query.answer(text='☀️Утро инвентаризация внесена', show_alert=True)
            text = '\n✔️утро инвентаризация внесена'
            context.bot.sendMessage(chat_id=ERROR_ADMIN_ID, text='☀️Утро инвент внесена {dept} - {store_name}'.
                                    format(store_name=emp.store_name, dept=emp.department_code))
        else:
            query.answer(text='❌ Что-то внесли не так🤨, смотри в колонке Ошибка заполнения', show_alert=True)
            text = '\n❌ ошибка утро инвентаризация'
        del invent_whale_sheet
        gc.collect()

    else:
        return ConversationHandler.END

    # проверяем какие кнопки доступны
    stock_keyb_text = keyboard_stock(context)
    # если во время работы диалога время вышло и нет доступных интервалов, то клавиатура веернёт None
    if not stock_keyb_text:
        update.message.reply_text(
            text='Нет доступных интервалов',
            reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
        )
        return ConversationHandler.END

    context.user_data[SERVICE_MESSAGE] = update.callback_query.message.text + text

    query.edit_message_text(
        text=context.user_data[SERVICE_MESSAGE],
        reply_markup=stock_keyb_text.keyboard,
    )
    return DISPATCH_HANDLER


def stock_cancel(update, context):

    logging.info(f'press stock_cancel сообщения на удаление {context.user_data[ID_MESSAGE_TO_DELETE]} \n')

    for mes_id in context.user_data[ID_MESSAGE_TO_DELETE]:
        try:
            context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT], message_id=mes_id)
        except:
            logging.error(f'ошибка stock - удаление {context.user_data[ID_USER_CHAT]}    -   \n')
            return ConversationHandler.END


    if not context.user_data[SERVICE_MESSAGE]:
        context.user_data[SERVICE_MESSAGE] = f'Прервали ,\n{BUTTON_STOCKS}'
    update.message.reply_text(
        text=f' {context.user_data[SERVICE_MESSAGE]}\n\nВернулись в cтартовое меню',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context)
    )
    return ConversationHandler.END


def stock_timeout_callback(update, context):
    query = update.callback_query
    query.edit_message_text(
        text=f'Прервали ,\n{BUTTON_STOCKS} - не было активностей',
    )
    update.effective_message.reply_text(
        text='Вернулись в стартовое меню',
        reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context),
    )


def stock_timeout_message(update, context):
    for mes_id in context.user_data[ID_MESSAGE_TO_DELETE]:
        context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT], message_id=mes_id)
    update.message.reply_text(
            text=f'Прервали ,\n{BUTTON_STOCKS} - не было активностей',
            reply_markup=keyboard_start(context.user_data[ID_USER_CHAT], context),
    )


def stock_reset_store(update, context):
    for mes_id in context.user_data[ID_MESSAGE_TO_DELETE]:
        context.bot.delete_message(chat_id=context.user_data[ID_USER_CHAT], message_id=mes_id)
    reset_store_employee(update, context)  # выкидывает из БД запись о том где работает сотрудник
    return ConversationHandler.END


def conversation_stocks(dispatcher):
    dispatcher.add_handler(ConversationHandler(
        entry_points=[MessageHandler(Filters.regex(BUTTON_STOCKS), start_stock_conversation, pass_user_data=True)],

        states={
            DISPATCH_HANDLER: [CallbackQueryHandler(stock_dispatch_handler, pass_user_data=True)],
            # WRITE: [CallbackQueryHandler(register_write, pass_user_data=True)],
            ConversationHandler.TIMEOUT: [CallbackQueryHandler(stock_timeout_callback, pass_job_queue=True, pass_update_queue=True),
                                          MessageHandler(Filters.text | Filters.command, stock_timeout_message)],
        },
        fallbacks=[MessageHandler(Filters.regex(BUTTON_CANCEL_CONVERSATION), stock_cancel, pass_user_data=True),
                   CommandHandler('reset_store', stock_reset_store, pass_user_data=True),
                   MessageHandler(Filters.text | Filters.command(False), stock_cancel)],
        conversation_timeout=CHAT_TIMEOUT
    ))