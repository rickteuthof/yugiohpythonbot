import logging
import re
from difflib import SequenceMatcher
from json import dumps, loads
from operator import itemgetter
from pathlib import Path
from uuid import uuid4

import requests
from numpy import array, reshape
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      InlineQueryResultPhoto)
from telegram.ext import (CallbackQueryHandler, CommandHandler,
                          InlineQueryHandler, Updater)

TOKEN = Path('./TOKEN').read_text().strip()
API_URL = 'https://db.ygoprodeck.com/api/v2/cardinfo.php'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
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
    query_results = [card[0] for card in find_matches(query)[:20]]
    results = list()
    for result in query_results:
        caption = build_caption(result)
        print(caption)
        results.append(InlineQueryResultPhoto(
            id=uuid4(),
            title=result['name'],
            caption=caption,
            photo_url=result['image_url'],
            thumb_url=result['image_url_small'],
        ))
    update.inline_query.answer(results)


def match_ratio(query, card):
    regex = r'[^\s!,./?":;0-9]+'
    cardname = card['name'].lower()
    query = query.lower()
    ratio = 0
    ratio += SequenceMatcher(None, query, cardname).ratio()
    splitquery = re.findall(regex, query)
    splitcard = re.findall(regex, cardname)
    test = sum([word in splitquery for word in splitcard])
    ratio += test
    return ratio


def find_matches(query):
    results = [(card, match_ratio(query, card)) for card in json_data[0]]
    results.sort(reverse=True, key=itemgetter(1))
    return results


def card(bot, update):
    try:
        query = update.message.text.split(' ', 1)[1]
    except IndexError:
        return
    message_id = update.message.message_id
    chat_id = update.message.chat.id
    bot.delete_message(
        chat_id=chat_id,
        message_id=message_id
    )
    results = [result[0] for result in find_matches(query)[:10]]
    names = [card['name'] for card in results]
    kbd = [InlineKeyboardButton(name, callback_data=name) for name in names]
    newshape = (len(kbd) // 2, 2)
    keyboard = list(reshape(array(kbd), newshape))
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        text='Results for query:',
        reply_markup=reply_markup
    )


def button(bot, update):
    query = update.callback_query.data
    message_id = update.callback_query.message.message_id
    chat_id = update.callback_query.message.chat.id
    bot.delete_message(
        chat_id=chat_id,
        message_id=message_id
    )
    card = find_matches(query)[0][0]
    caption = build_caption(card)
    print(caption)
    bot.send_photo(
        chat_id=chat_id,
        photo=card['image_url'],
        caption=caption
    )


def help(bot, update):
    update.message.reply_text(
        "Use /card to find any Yu-Gi-Oh card.\n"
        "You can also use the inline feature to search for specific cards."
    )


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


if __name__ == '__main__':
    json_data = loads(Path('./data.json').read_text())
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(InlineQueryHandler(inlinequery))
    dp.add_handler(CommandHandler('card', card))
    dp.add_handler(CommandHandler('help', help))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()
