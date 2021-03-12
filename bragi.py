#!/usr/bin/python3

"""
Bragi Printer Bot

This bot receives messages via telegram and prints them with a receipt printer.
"""

import logging
import sys
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from escpos.printer import Serial
import re
from PIL import Image
import time
import unicodedata
from unidecode import unidecode

# Enable logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Printer object
p = Serial(devfile='/dev/ttyUSB2',
           baudrate=115200,
           bytesize=8,
           parity='N',
           stopbits=1,
           timeout=1.00,
           dsrdtr=True,
           )

# Url Regex
URL_REGEX = r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'\".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"""

def start(update: Update, context: CallbackContext) -> None:
    """Start the bot for a user"""
    update.message.reply_text("Hi! This is Bragi the receipt printer. The bot is named after the skaldic god of poetry in Norse mythology. Here's some info about the bot:")
    help_command(update, context)

def help_command(update: Update, context: CallbackContext) -> None:
    """Send instructions"""
    update.message.reply_text(("Everything sent to this bot will be printed on a thermal receipt printer. (Posiflex PP-8000B)\n\n"
    "Currently the following message types are supported:\n"
    "- Text (when sending emojis their discription is printed, like: [FLUSHED FACE] or [SNOWMAN WITHOUT SNOW]. When the text contains a url, a QR code is printed after the text message which points to the url.)\n"
    "- Images (non-animated stickers also work)\n"
    "- Contacts\n"
    "- Polls (although it doesn't print updates when someone votes)\n"
    "- Location (prints the latitude and longitude)\n\n"
    "Things the printer can't print:\n"
    "- Voice messages\n"
    "- Videos (including animated stickers)\n"
    "- Documents (I'm not printing your books or executables)\n\n"
    "The bot supports the following commands:\n"
    "  /help - Prints this message\n"
    "  /start - Prints hi and then this message\n"))

# Function taken from https://stackoverflow.com/questions/43797500/python-replace-unicode-emojis-with-ascii-characters
def replace_emojis(input_string):
    """Replace emojis with descriptions about the emojis"""
    return_string = ""
    for character in input_string:
        try:
            character.encode("ascii")
            return_string += character
        except UnicodeEncodeError:
            replaced = unidecode(str(character))
            if replaced != '':
                return_string += replaced
            else:
                try:
                     return_string += "[" + unicodedata.name(character) + "]"
                except ValueError:
                     return_string += "[x]"
    return return_string

def print_text(update: Update, context: CallbackContext) -> None:
    """Print received text message"""
    logging.info("Message received: {}: {}".format(update.message.from_user.first_name, update.message.text))
    # Print message
    p.text("Message from {} {}:\n{}\n".format(update.message.from_user.first_name, update.message.from_user.last_name, replace_emojis(update.message.text)))
    # Get urls in message and print qr codes for the urls
    urls = re.findall(URL_REGEX, update.message.text)
    for url in urls:
        p.text("\n{}".format(url))
        p.qr(url, size=8, center=True)
    # Cut and reply
    p.cut()
    update.message.reply_text("Printed!")

def print_photo(update: Update, context: CallbackContext) -> None:
    """Print received image"""
    logging.info("Image received from {}".format(update.message.from_user.first_name))
    # Get image from Telegram
    if update.message.document != None:
        imageFile = context.bot.get_file(update.message.document.file_id)
    elif update.message.sticker != None:
        if (update.message.sticker.is_animated):
            update.message.reply_text("Cannot print animated stickers...")
            return
        # Get sticker
        imageFile = context.bot.get_file(update.message.sticker.file_id)
    elif update.message.photo != None:
        imageFile = context.bot.get_file(update.message.photo[-1].file_id)
    image = imageFile.download()
    # Resize image to correct size (maximum width of 512 pixels)
    img = Image.open(image)
    wpercent = (512/float(img.size[0]))
    hsize = int((float(img.size[1])*float(wpercent)))
    img = img.resize((512, hsize))
    img.save(image)
    # Print sender
    p.text("Image from {} {}:\n".format(update.message.from_user.first_name, update.message.from_user.last_name))
    # Print image
    p.image(image)
    # Wait some time before continuing with the rest, the following two lines fixed all my image printing problems
    time.sleep(1)
    p.text("\n")
    # Cut and reply
    p.cut()
    update.message.reply_text("Image printed!")

def print_audio(update: Update, context: CallbackContext) -> None:
    """Cannot print received audio"""
    logging.info("Audio received from {}".format(update.message.from_user.first_name))
    update.message.reply_text("Although the printer makes sound, my printer cannot make your sound...")

def print_contact(update: Update, context: CallbackContext) -> None:
    """Print received contact"""
    logging.info("Contact received from {}".format(update.message.from_user.first_name))
    # Print contact (I'm not sure why I implemented this)
    p.text("Contact from {} {}\nName: {} {}\nTel: {}\n".format(update.message.from_user.first_name, update.message.from_user.last_name, update.message.contact.first_name, update.message.contact.last_name, update.message.contact.phone_number))
    # Cut and reply
    p.cut()
    update.message.reply_text("Contact printed")

def print_document(update: Update, context: CallbackContext) -> None:
    """Don't print received document"""
    logging.info("Document received from {}".format(update.message.from_user.first_name))
    update.message.reply_text("How about no. Print your own documents!")

def print_location(update: Update, context: CallbackContext) -> None:
    """Print received location"""
    logging.info("Location received from {}".format(update.message.from_user.first_name))
    # Print latitude and longitude
    p.text("Location from {} {}\nLatitude: {}\nLongitude: {}\n".format(update.message.from_user.first_name, update.message.from_user.last_name, update.message.location.latitude, update.message.location.longitude))
    # Cut and reply
    p.cut()
    update.message.reply_text("Location printed")

def print_poll(update: Update, context: CallbackContext) -> None:
    """Print received poll"""
    logging.info("Poll received from {}".format(update.message.from_user.first_name))
    # Print question and answers
    p.text("Poll from {} {}\nQuestion: {}\n".format(update.message.from_user.first_name, update.message.from_user.last_name, update.message.poll.question))
    p.set(align='left')
    for option in update.message.poll.options:
        p.text("    [] {}\n".format(option.text))
    p.set(align='center')
    # Cut and reply
    p.cut()
    update.message.reply_text("Poll printed")

def print_video(update: Update, context: CallbackContext) -> None:
    """Don't print received video"""
    logging.info("Video received from {}".format(update.message.from_user.first_name))
    update.message.reply_text("Video's cannot be printed smartass.")

def main():
    """Starting point"""
    # Printer settings
    p.set(align='center')
    # Start the bot
    TOKEN = None
    with open("token.txt") as f:
        TOKEN = f.read().strip()
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher
    # Handle commands
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    # Handle all the message types! I might be able to OR some lines, but this also works
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, print_text))
    dispatcher.add_handler(MessageHandler(Filters.photo, print_photo))
    dispatcher.add_handler(MessageHandler(Filters.document.image, print_photo))
    dispatcher.add_handler(MessageHandler(Filters.audio, print_audio))
    dispatcher.add_handler(MessageHandler(Filters.voice, print_audio))
    dispatcher.add_handler(MessageHandler(Filters.contact, print_contact))
    dispatcher.add_handler(MessageHandler(Filters.document & ~Filters.document.image & ~Filters.document.video, print_document))
    dispatcher.add_handler(MessageHandler(Filters.location, print_location))
    dispatcher.add_handler(MessageHandler(Filters.poll, print_poll))
    dispatcher.add_handler(MessageHandler(Filters.sticker, print_photo))
    dispatcher.add_handler(MessageHandler(Filters.video, print_video))
    dispatcher.add_handler(MessageHandler(Filters.document.video, print_video))

    # Start polling
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
