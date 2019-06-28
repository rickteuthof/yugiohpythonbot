import logging
import re
from difflib import SequenceMatcher
from json import dumps, loads
from operator import itemgetter
from pathlib import Path
from uuid import uuid4

import requests
from numpy import array, reshape
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultPhoto,
    InputMediaPhoto
)
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    InlineQueryHandler,
    Updater
)

TOKEN = Path('./TOKEN').read_text().strip()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    # filename='log.log'
)
logger = logging.getLogger(__name__)


def build_caption(card):
    ban_tcg = card['ban_tcg'] if card['ban_tcg'] else "Unlimited"
    caption = '%s\n%s / %s\n\n%s\n\nBan status: %s' % (
        card['name'],
        card['race'],
        card['type'],
        card['desc'],
        ban_tcg
    )
    return caption


def inlinequery(bot, update):
    query = update.inline_query.query
    logger.info('Bot "%s" got inlinequery "%s"' % (bot, query))
    query_results = [card for card in json_data[0]
                     if query.lower() in card['name'].lower()][:20]
    results = list()
    for result in query_results:
        caption = build_caption(result)
        results.append(InlineQueryResultPhoto(
            id=uuid4(),
            title=result['name'],
            caption=caption,
            photo_url=result['image_url'],
            thumb_url=result['image_url_small'],
        ))
    update.inline_query.answer(results)


def match_ratio(query, card):
    regex = r'[^\s!,.?":;0-9]+'
    cardname = card['name'].lower()
    query = query.lower()
    ratio = 0
    ratio += SequenceMatcher(None, query, cardname).quick_ratio()
    splitquery = re.findall(regex, query)
    splitcard = re.findall(regex, cardname)
    test = sum([word in splitquery for word in splitcard])
    ratio += test
    return ratio


def find_matches(query):
    """
    Returns a triple (card json, query match value, json data index)
    """
    results = [(card, match_ratio(query, card), i)
               for i, card in enumerate(json_data[0])]
    results.sort(reverse=True, key=itemgetter(1))
    return results


def card(bot, update):
    chat_id = update.message.chat.id
    message_id = update.message.message_id
    try:
        query = update.message.text.split(' ', 1)[1]
    except IndexError:
        return
    logger.info('Bot "%s" got query "%s"' % (bot, query))
    results = [(card['name'], i) for card, _, i in find_matches(query)[:10]]
    kbd = [InlineKeyboardButton(name, callback_data=i) for name, i in results]
    newshape = (len(kbd) // 2, 2)
    keyboard = list(reshape(array(kbd), newshape))
    reply_markup = InlineKeyboardMarkup(keyboard)
    bot.send_message(
        chat_id=chat_id,
        text='Results for query:',
        reply_markup=reply_markup
    )
    bot.delete_message(
        chat_id=chat_id,
        message_id=message_id
    )


def send_card(bot, update, index):
    message_id = update.callback_query.message.message_id
    chat_id = update.callback_query.message.chat.id
    bot.delete_message(
        chat_id=chat_id,
        message_id=message_id
    )
    card = json_data[0][index]
    caption = build_caption(card)
    logger.info('Bot "%s" sent msg "%s"' % (bot, caption))
    keyboard = [[InlineKeyboardButton("Collapse", callback_data="collapse")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = bot.send_photo(
        chat_id=chat_id,
        photo=card['image_url'],
        caption=caption,
        reply_markup=reply_markup
    )
    active_msgs[msg.message_id] = {
        "card_name": card['name'],
        "image_url": card['image_url'],
        "caption": caption,
    }


def collapse(bot, update):
    message_id = update.callback_query.message.message_id
    chat_id = update.callback_query.message.chat.id
    keyboard = [[InlineKeyboardButton("Expand", callback_data="expand")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    active_message = active_msgs[message_id]
    media = InputMediaPhoto(
        media='https://upload.wikimedia.org/wikipedia/commons/2/20/16x16.png',
        caption=active_message['card_name']
    )
    bot.edit_message_media(
        chat_id=chat_id,
        message_id=message_id,
        media=media,
        reply_markup=reply_markup
    )


def expand(bot, update):
    message_id = update.callback_query.message.message_id
    chat_id = update.callback_query.message.chat.id
    # keyboard = [[InlineKeyboardButton("Collapse", callback_data="collapse")]]
    # reply_markup = InlineKeyboardMarkup(keyboard)
    active_message = active_msgs[message_id]
    media = InputMediaPhoto(
        media=active_message['image_url'],
        caption=active_message['caption']
    )
    bot.edit_message_media(
        chat_id=chat_id,
        message_id=message_id,
        media=media,
        # reply_markup=reply_markup
    )


def button(bot, update):
    data = update.callback_query.data
    if data == "collapse":
        collapse(bot, update)
    elif data == "expand":
        expand(bot, update)
    else:
        index = int(data)
        send_card(bot, update, index)


def help(bot, update):
    update.message.reply_text(
        "Use /card to find any Yu-Gi-Oh card.\n"
        "You can also use the inline feature to search for specific cards."
    )


def error(bot, update, error):
    """Log Errors caused by Updates."""
    logger.error('Bot "%s" caused error "%s"' % (bot, error))


if __name__ == '__main__':
    json_data = loads(Path('./data.json').read_text())
    active_msgs = dict()
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(InlineQueryHandler(inlinequery))
    dp.add_handler(CommandHandler('card', card))
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()
