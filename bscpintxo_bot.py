#!/usr/bin/env python

import sheetdata

# Telegram
from telegram import ParseMode
from telegram.ext import Updater
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters

import json
import random
import functools
import logging
import os.path

# Enable logging for telegram module and this file
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.ERROR)
telegram_logger = logging.getLogger('telegram')
telegram_logger.setLevel(logging.INFO)
logger = logging.getLogger(os.path.basename(__file__))
logger.setLevel(logging.INFO)

# Load JSON config file
with open('bscpintxo_bot.json') as json_file:
    config = json.load(json_file)

def admin_command(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = args[1].message.from_user
        chat = args[1].message.chat
        if user.id in config['bot_admins']:
            logger.info('GET /{command} (admin) from channel \'{channel_title}\'({channel_id}): '
                    '{first_name} {last_name} ({user_id})'.format(
                        command=func.__name__,
                        channel_title=chat.title,
                        channel_id=chat.id,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        user_id=user.id))
            func(*args, **kwargs)
            logger.info('Successful reply to {0}'.format(user.id))
        else:
            logger.warning('GET /{command} (admin) from channel \'{channel_title}\'({channel_id}): '
                    '{first_name} {last_name} ({user_id}) DENIED'.format(
                        command=func.__name__,
                        channel_title=chat.title,
                        channel_id=chat.id,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        user_id=user.id))
    return wrapper

def private_command(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = args[1].message.from_user
        chat = args[1].message.chat
        if chat.id in config['chat_whitelist']:
            logger.info('GET /{command} from channel \'{channel_title}\'({channel_id}): '
                    '{first_name} {last_name} ({user_id})'.format(
                        command=func.__name__,
                        channel_title=chat.title,
                        channel_id=chat.id,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        user_id=user.id))
            func(*args, **kwargs)
            logger.info('Successful reply to {0}'.format(user.id))
        else:
            logger.warning('GET /{command} from channel \'{channel_title}\'({channel_id}): '
                    '{first_name} {last_name} ({user_id}) DENIED'.format(
                        command=func.__name__,
                        channel_title=chat.title,
                        channel_id=chat.id,
                        first_name=user.first_name,
                        last_name=user.last_name,
                        user_id=user.id))
    return wrapper

@private_command
def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="I'm a bot, please talk to me!")

@private_command
def help(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text='Available commands... (tbd).'
            ' Ok, only a little: /start /choices /roll')

@private_command
def choices(bot, update, args):
    sheet = sheetdata.SheetData(config['spreadsheet_id'])
    try:
        sheet.compute_choices(args)
    except sheetdata.SheetDataException:
        text_error = 'Sorry, I couldn\'t find any vote'
        bot.send_message(chat_id=update.message.chat_id, text=text_error)
    else:
        text = 'Choice options for ' + ', '.join(sheet.choices_participants) + '\n\n'
        text += '<pre>'+sheet.get_choices_table(hide_zeroes=True)+'</pre>'
        bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode=ParseMode.HTML)

@private_command
def people(bot, update):
    sheet = sheetdata.SheetData(config['spreadsheet_id'])
    text = 'People: ' + ', '.join(sheet.people)
    bot.send_message(chat_id=update.message.chat_id, text=text, parse_mode=ParseMode.HTML)

@private_command
def roll(bot, update, args):
    sheet = sheetdata.SheetData(config['spreadsheet_id'])
    try:
        sheet.compute_choices(args)
    except sheetdata.SheetDataException:
        text_error = 'Sorry, I couldn\'t find any vote'
        bot.send_message(chat_id=update.message.chat_id, text=text_error)
    else:
        text = ''
        # Add participants, if filtered
        if args:
            text += 'Computing roll for ' + ', '.join(sheet.choices_participants) + ':\n'
            text += '(' + sheet.choices_summary + ')\n'
        # Add drums
        text += '\U0001f941 \U0001f941 \U0001f941\n'
        # Result
        text += random.choices(sheet.choices_places, weights=sheet.choices_weights)[0]
        bot.send_message(chat_id=update.message.chat_id, text=text)

@private_command
def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
            text='Sorry, I didn\'t understand that command.'
            ' Type /help for a description of available commands.')

def main():
    updater = Updater(token=config['telegram_token'])
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    help_handler = CommandHandler('help', help)
    dispatcher.add_handler(help_handler)

    choices_handler = CommandHandler('choices', choices, pass_args=True)
    dispatcher.add_handler(choices_handler)

    people_handler = CommandHandler('people', people)
    dispatcher.add_handler(people_handler)

    roll_handler = CommandHandler('roll', roll, pass_args=True)
    dispatcher.add_handler(roll_handler)

    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
