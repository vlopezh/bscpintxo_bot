# BSC Pintxo BOT

This is the BSC Pintxo Bot for Telegram

## Requirements

Python modules:

* python-telegram-bot
* python-google-api-python-client
* python-google-auth-oauthlib
* python-tabulate
* python-unidecode

## Files

These files are needed to run the bot:

* `google_credentials.json`: Google Token to access the Google Spreadsheet.
([Google documentation](https://developers.google.com/sheets/api/quickstart/python)).
* `bscpintxo_bot.json`: Bot options
    * `bot_admins`: List of Telegram user IDs that can execute admin commands
    * `chat_whitelist`: List of Telegram chat IDs that can execute private commands
    * `telegram_token`: Token provided by Telegram's Botfather to access the bot
    * `spreadsheet_id`: Google Spreadsheet id
