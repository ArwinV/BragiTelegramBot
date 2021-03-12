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
from datetime import datetime
import unicodedata
from unidecode import unidecode
import json

# Enable logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Url Regex
URL_REGEX = r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'\".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"""

def store_data() -> None:
    """Store data to json file"""
    with open('saves.json', 'w') as save_file:
        json.dump(data, save_file)

def update_stats(printed_type) -> None:
    """Increment stats"""
    data['total_prints'] = data['total_prints'] + 1
    if printed_type == 'text':
        data['text_prints'] = data['text_prints'] + 1
    elif printed_type == 'image':
        data['image_prints'] = data['image_prints'] + 1
    elif printed_type == 'contact':
        data['contact_prints'] = data['contact_prints'] + 1
    elif printed_type == 'poll':
        data['poll_prints'] = data['poll_prints'] + 1
    elif printed_type == 'location':
        data['location_prints'] = data['location_prints'] + 1
    store_data()

def user_is_admin(user_id) -> bool:
    """Check is user is the admin"""
    if user_id == int(data['admin_id']):
        return True
    else:
        return False

def user_may_print(user_id) -> bool:
    """Check if user may print"""
    for user in data['users']:
        if user['id'] == user_id:
            return user['permission_to_print']
    return False

def user_is_anonymous(user_id) -> bool:
    """Check is user is anonymous"""
    for user in data['users']:
        if user['id'] == user_id:
            return user['anonymous']
    return False

def start(update: Update, context: CallbackContext) -> None:
    """Start the bot for a user"""
    update.message.reply_text("Hi! This is Bragi the receipt printer. The bot is named after the skaldic god of poetry in Norse mythology. Here's some info about the bot:")
    help_command(update, context)
    update.message.reply_text("You'll receive a message when you have gotten permission to print.")
    # Add user to list of users
    for user in data['users']:
        if user['id'] == update.message.from_user.id:
            update.message.reply_text("You are already registered")
            break
    else:
        data['users'].append({
            'name': "{} {}".format(update.message.from_user.first_name, update.message.from_user.last_name),
            'id': update.message.from_user.id,
            'permission_to_print': False,
            'anonymous': False})
        store_data()
    # Send message to admin to inform there is a pending permission request
    context.bot.send_message(data['admin_id'], text="{} {} wants permission to print, grant it with \givepermission {}".format(update.message.from_user.first_name, update.message.from_user.last_name, update.message.from_user.id))

def listusers_command(update: Update, context: CallbackContext) -> None:
    """List users, their id and if they have permission to print"""
    if not user_is_admin(update.message.from_user.id):
        update.message.reply_text("You are not allowed to use this command")
        return
    reply_text = "Name | User ID | Permission to print\n"
    for user in data['users']:
        reply_text += "{} | {} | {}\n".format(user['name'], user['id'], user['permission_to_print'])
    update.message.reply_text(reply_text)

def givepermission_command(update: Update, context: CallbackContext) -> None:
    """Give a user permission to print"""
    if not user_is_admin(update.message.from_user.id):
        update.message.reply_text("You are not allowed to use this command")
        return
    user_id = update.message.text.split()[1]
    for user in data['users']:
        if user['id'] == int(user_id):
            user['permission_to_print'] = True
            username = user['name']
            break;
    else:
        update.message.reply_text("User id not found")
        return
    store_data()
    update.message.reply_text("Permission to print of {} set to True".format(username))

def removepermission_command(update: Update, context: CallbackContext) -> None:
    """Revoke permission to print"""
    if not user_is_admin(update.message.from_user.id):
        update.message.reply_text("You are not allowed to use this command")
        return
    user_id = update.message.text.split()[1]
    for user in data['users']:
        if user['id'] == int(user_id):
            user['permission_to_print'] = False
            username = user['name']
            break;
    else:
        update.message.reply_text("User id not found")
        return
    store_data()
    update.message.reply_text("Permission to print of {} set to False".format(username))

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
        "  /start - Prints hi and then this message\n"
        "  /stats - Prints stats about the printer\n"
        "  /anonymous - Check/Enable/Disable anonymous mode. In anonymous mode your name isn't printed above your message\n"))

def stats_command(update: Update, context: CallbackContext) -> None:
    """Send stats"""
    update.message.reply_text(("Total amount of messages printed: {}\n"
        "Text messages printed: {}\n"
        "Images printed: {}\n"
        "Contacts printed: {}\n"
        "Polls printed: {}\n"
        "Locations printed: {}\n").format(data['total_prints'], data['text_prints'], data['image_prints'], data['contact_prints'], data['poll_prints'], data['location_prints']))

def anonymous_command(update: Update, context: CallbackContext) -> None:
    """Set anonymous status"""
    command_words = update.message.text.split()
    if len(command_words) == 1:
        for user in data['users']:
            if user['id'] == update.message.from_user.id:
                update.message.reply_text("Anonymous: {}\nYou can enable or disable anonymous messages with /anonymous true/false".format(user['anonymous']))
                break;
    else:
        for user in data['users']:
            if user['id'] == update.message.from_user.id:
                user['anonymous'] = command_words[1].lower() == 'true'
                update.message.reply_text("Anonymous setting set to: {}".format(user['anonymous']))
                break;

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
    if not user_may_print(update.message.from_user.id):
        update.message.reply_text("You are not allowed to print, request permission with /start")
        return
    # Print message
    if not user_is_anonymous(update.message.from_user.id):
        name = "{} {}".format(update.message.from_user.first_name, update.message.from_user.last_name)
    else:
        name = "Anonymous"
    logging.info("Message received: {}: {}".format(name, update.message.text))
    p.text("{} - {}:\n{}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name, replace_emojis(update.message.text)))
    # Get urls in message and print qr codes for the urls
    urls = re.findall(URL_REGEX, update.message.text)
    for url in urls:
        p.text("\n{}".format(url))
        p.qr(url, size=8, center=True)
    # Cut, reply and update stats
    p.cut()
    update.message.reply_text("Printed!")
    update_stats('text')

def print_photo(update: Update, context: CallbackContext) -> None:
    """Print received image"""
    if not user_may_print(update.message.from_user.id):
        update.message.reply_text("You are not allowed to print, request permission with /start")
        return
    # Get name (or anonymous)
    if not user_is_anonymous(update.message.from_user.id):
        name = "{} {}".format(update.message.from_user.first_name, update.message.from_user.last_name)
    else:
        name = "Anonymous"
    logging.info("Image received from {}".format(name))
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
    p.text("{} - {}:\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name))
    # Print image
    p.image(image)
    # Wait some time before continuing with the rest, the following two lines fixed all my image printing problems
    time.sleep(1)
    p.text("\n")
    # Cut and reply
    p.cut()
    update.message.reply_text("Image printed!")
    update_stats('image')

def print_audio(update: Update, context: CallbackContext) -> None:
    """Cannot print received audio"""
    # Get name (or anonymous)
    if not user_is_anonymous(update.message.from_user.id):
        name = "{} {}".format(update.message.from_user.first_name, update.message.from_user.last_name)
    else:
        name = "Anonymous"
    logging.info("Audio received from {}".format(name))
    update.message.reply_text("Although the printer makes sound, my printer cannot make your sound...")

def print_contact(update: Update, context: CallbackContext) -> None:
    """Print received contact"""
    if not user_may_print(update.message.from_user.id):
        update.message.reply_text("You are not allowed to print, request permission with /start")
        return
    # Get name (or anonymous)
    if not user_is_anonymous(update.message.from_user.id):
        name = "{} {}".format(update.message.from_user.first_name, update.message.from_user.last_name)
    else:
        name = "Anonymous"
    logging.info("Contact received from {}".format(name))
    # Print contact (I'm not sure why I implemented this)
    p.text("{} - {}\nName: {} {}\nTel: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name, update.message.contact.first_name, update.message.contact.last_name, update.message.contact.phone_number))
    # Cut and reply
    p.cut()
    update.message.reply_text("Contact printed")
    update_stats('contact')

def print_document(update: Update, context: CallbackContext) -> None:
    """Don't print received document"""
    # Get name (or anonymous)
    if not user_is_anonymous(update.message.from_user.id):
        name = "{} {}".format(update.message.from_user.first_name, update.message.from_user.last_name)
    else:
        name = "Anonymous"
    logging.info("Document received from {}".format(name))
    update.message.reply_text("How about no. Print your own documents!")

def print_location(update: Update, context: CallbackContext) -> None:
    """Print received location"""
    if not user_may_print(update.message.from_user.id):
        update.message.reply_text("You are not allowed to print, request permission with /start")
        return
    # Get name (or anonymous)
    if not user_is_anonymous(update.message.from_user.id):
        name = "{} {}".format(update.message.from_user.first_name, update.message.from_user.last_name)
    else:
        name = "Anonymous"
    logging.info("Location received from {}".format(name))
    # Print latitude and longitude
    p.text("{} - {}\nLatitude: {}\nLongitude: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name, update.message.location.latitude, update.message.location.longitude))
    # Cut and reply
    p.cut()
    update.message.reply_text("Location printed")
    update_stats('location')

def print_poll(update: Update, context: CallbackContext) -> None:
    """Print received poll"""
    if not user_may_print(update.message.from_user.id):
        update.message.reply_text("You are not allowed to print, request permission with /start")
        return
    # Get name (or anonymous)
    if not user_is_anonymous(update.message.from_user.id):
        name = "{} {}".format(update.message.from_user.first_name, update.message.from_user.last_name)
    else:
        name = "Anonymous"
    logging.info("Poll received from {}".format(name))
    # Print question and answers
    p.text("{} - {}:\nQuestion: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name, update.message.poll.question))
    p.set(align='left')
    for option in update.message.poll.options:
        p.text("    [] {}\n".format(option.text))
    p.set(align='center')
    # Cut and reply
    p.cut()
    update.message.reply_text("Poll printed")
    update_stats('poll')

def print_video(update: Update, context: CallbackContext) -> None:
    """Don't print received video"""
    # Get name (or anonymous)
    if not user_is_anonymous(update.message.from_user.id):
        name = "{} {}".format(update.message.from_user.first_name, update.message.from_user.last_name)
    else:
        name = "Anonymous"
    logging.info("Video received from {}".format(name))
    # Reply
    update.message.reply_text("Video's cannot be printed smartass.")

def main():
    """Starting point"""
    # Printer object
    global p
    p = Serial(devfile='/dev/ttyUSB2',
               baudrate=115200,
               bytesize=8,
               parity='N',
               stopbits=1,
               timeout=1.00,
               dsrdtr=True)

    # Printer settings
    p.set(align='center')
    # Load saves dict
    global data
    try:
        with open("saves.json") as save_file:
            data = json.load(save_file)
    except FileNotFoundError:
        logging.info("saves.json file not found. Creating the file.")
        data = {}
        data['total_prints'] = 0
        data['text_prints'] = 0
        data['image_prints'] = 0
        data['contact_prints'] = 0
        data['poll_prints'] = 0
        data['location_prints'] = 0
        data['users'] = []
        try:
            with open("admin_id.txt") as admin_file:
                admin_id = admin_file.read().strip()
        except FileNotFoundError:
            logging.error("No admin_id file found. Add your user id in a file called admin_id.txt in the same directory as the bot.")
            return
        data['admin_id'] = int(admin_id)
        with open('saves.json', 'w') as save_file:
            json.dump(data, save_file)
    # Start the bot
    TOKEN = None
    try:
        with open("token.txt") as f:
            TOKEN = f.read().strip()
    except FileNotFoundError:
        logging.error("No token file found. Add your token in a file called token.txt in the same directory as the bot.")
        return
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher
    # Handle commands
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("stats", stats_command))
    dispatcher.add_handler(CommandHandler("listusers", listusers_command))
    dispatcher.add_handler(CommandHandler("givepermission", givepermission_command))
    dispatcher.add_handler(CommandHandler("removepermission", removepermission_command))
    dispatcher.add_handler(CommandHandler("anonymous", anonymous_command))
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
