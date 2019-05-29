import json
import logging
from difflib import SequenceMatcher
from operator import itemgetter
from pathlib import Path
from uuid import uuid4

import requests
from telegram import InlineQueryResultPhoto
from telegram.ext import CommandHandler, InlineQueryHandler, Updater

TOKEN = Path('./TOKEN').read_text().strip()
API_URL = 'https://db.ygoprodeck.com/api/v2/cardinfo.php'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
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
    query_results = [card for card in json_data[0]
                     if query.lower() in card['name'].lower()][0:20]
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


def find_matches(query):
    results = [(card, SequenceMatcher(
        None,
        query.lower(),
        card['name'].lower()).ratio()
    ) for card in json_data[0]]
    results.sort(reverse=True, key=itemgetter(1))
    return results[0]


def card(bot, update):
    try:
        query = update.message.text.split(' ', 1)[1]
    except IndexError:
        return
    print(query)
    result, _ = find_matches(query)
    send_card(bot, update, result)


def send_card(bot, update, card):
    chat_id = update.message.chat_id
    caption = build_caption(card)
    print(caption)
    bot.send_photo(
        chat_id=chat_id,
        photo=card['image_url'],
        caption=caption
    )


def error(bot, update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


if __name__ == '__main__':
    json_data = json.loads(Path('./data.json').read_text())
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(InlineQueryHandler(inlinequery))
    dp.add_handler(CommandHandler('card', card))
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()
