# BragiTelegramBot
Telegram bot which sends received messages to a receipt printer.

You need the following packages:
- python-telegram-bot
- escpos
- unidecode

In order to use the bot you have to put your token in a file called 'token.txt' and your user id in a file called admin_id.txt in the same directory as the bragi.py file.

In order to autostart the bot:
- Copy bragi.service to /etc/systemd/system/
- Run systemctl daemon-reload
- Enable the service with systemctl enable bragi

The bot can also automatically be started with:
systemctl start bragi
