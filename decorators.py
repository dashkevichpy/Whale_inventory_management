import tracemalloc

from telegram.ext import ConversationHandler
from time import time

def check_group(func):
    def wrapper(update, context):
        if update.message.chat.type == 'group' or update.message.chat.type == 'supergroup':
            update.effective_message.reply_text(
                text='Команды в группе не принимаются',
                reply_markup=None
            )
            return ConversationHandler.END
        else:
            return func(update, context)
    return wrapper


def timing(f):
    def wrap(*args, **kw):
        ts = time()
        result = f(*args, **kw)
        te = time()
        print('-- func:%r args:[%r, %r] took: %2.4f sec' % (f.__name__, args, kw, te-ts))
        return result
    return wrap


def leak_find(f):
    # @wraps(f)
    def wrap(*args, **kw):
        tracemalloc.start()

        result = f(*args, **kw)

        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        print('LEAKS -- func:%r args:[%r, %r]' % (f.__name__, args, kw))
        for stat in top_stats[:5]:
            print(stat)
        return result
    return wrap