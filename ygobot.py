import json
import logging
from pathlib import Path
from uuid import uuid4

import requests
from telegram import InlineQueryResultPhoto
from telegram.ext import InlineQueryHandler, Updater

TOKEN = Path('./TOKEN').read_text().strip()
API_URL = 'https://db.ygoprodeck.com/api/v2/cardinfo.php'


def inlinequery(bot, update):
    query = update.inline_query.query
    query_results = [card for card in json_data[0]
                     if query.lower() in card['name'].lower()][0:20]
    results = list()
    for result in query_results:
        ban_tcg = result['ban_tcg'] if result['ban_tcg'] else "Unlimited"
        caption = '%s\n%s / %s\n\n%s\n\nBan status: %s' % (
            result['name'],
            result['race'],
            result['type'],
            result['desc'],
            ban_tcg
        )
        print(caption)
        results.append(InlineQueryResultPhoto(
            id=uuid4(),
            title=result['name'],
            caption=caption,
            photo_url=result['image_url'],
            thumb_url=result['image_url_small'],
        ))
    update.inline_query.answer(results)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


if __name__ == '__main__':
    json_data = json.loads(Path('./data.json').read_text())
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(InlineQueryHandler(inlinequery))
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()
