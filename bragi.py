#!/usr/bin/python3

"""
Bragi Printer Bot

This bot receives messages via telegram and prints them with a receipt printer.
"""

import logging
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from escpos.printer import Serial
import re
from PIL import Image
import time
from datetime import datetime, timedelta
import unicodedata
from unidecode import unidecode
import json
import os

# Enable logging
logging.root.setLevel(logging.NOTSET)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

# Url Regex
URL_REGEX = r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'\".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"""

async def error_printing(update: Update, context: CallbackContext, name) -> None:
    logging.error("Failed to print message")
    await update.message.reply_text("Failed to print your message :( There appears to be something wrong...")
    await context.bot.send_message(data['admin_id'], text="Failed to print a text message from {}.".format(name))

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

def user_info(telegram_user):
    """Return username and permission to print"""
    for user in data['users']:
        if user['id'] == telegram_user.id:
            # If username is changed, update the settings
            if "{} {}".format(telegram_user.first_name, telegram_user.last_name) != user['name']:
                user['name'] = "{} {}".format(telegram_user.first_name, telegram_user.last_name)
                store_data()
            # Return username and permission to print
            if user['anonymous']:
                return "Anonymous", user['permission_to_print']
            else:
                return user['name'], user['permission_to_print']
    else:
        return "Unknown", False

def user_exists(telegram_user):
    """Check if user exists"""
    for user in data['users']:
        if user['id'] == telegram_user.id:
            return True
    else:
        return False

def has_permission_to_print(telegram_user):
    """ Returns whether the user has permission to print"""
    for user in data['users']:
        if user['id'] == telegram_user.id:
            return user['permission_to_print']
    else:
        return False

def is_spamming(telegram_user):
    """Returns if user is spamming"""
    for user in data['users']:
        if user['id'] == telegram_user.id:
            if (datetime.now() - datetime.fromisoformat(user['last_message'])) < timedelta(minutes=5):
                if user['recent_messages'] >= 5:
                    return True
                else:
                    user['last_message'] = datetime.now().isoformat()
                    user['recent_messages'] = user['recent_messages'] + 1
                    return False
            else:
                user['last_message'] = datetime.now().isoformat()
                user['recent_messages'] = 0
                return False
    else:
        return True

async def start(update: Update, context: CallbackContext) -> None:
    """Start the bot for a user"""
    await update.message.reply_text("Hi! This is Bragi the receipt printer. The bot is named after the skaldic god of poetry in Norse mythology. Here's some info about the bot:")
    await help_command(update, context)
    # Add user to list of users
    for user in data['users']:
        if user['id'] == update.message.from_user.id:
            await update.message.reply_text("You are already registered")
            break
    else:
        data['users'].append({
            'name': "{} {}".format(update.message.from_user.first_name, update.message.from_user.last_name),
            'id': update.message.from_user.id,
            'permission_to_print': True, # Default permission to print, used to block people if they're annoying
            'anonymous': False,
            'last_message': datetime(1970, 1, 1).isoformat(),
            'recent_messages': 0})
        data['last_user_id'] = update.message.from_user.id
        store_data()
    await context.bot.send_message(data['admin_id'], text="{} {} Started the bot.".format(update.message.from_user.first_name, update.message.from_user.last_name, update.message.from_user.id))

async def listusers_command(update: Update, context: CallbackContext) -> None:
    """List users, their id and if they have permission to print"""
    if not user_is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this command")
        return
    reply_text = "Name | User ID | Permission to print\n"
    for user in data['users']:
        reply_text += "{} | {} | {}\n".format(user['name'], user['id'], user['permission_to_print'])
    await update.message.reply_text(reply_text)

async def givepermission_command(update: Update, context: CallbackContext) -> None:
    """Give a user permission to print"""
    if not user_is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this command")
        return
    # Check amount of arguments
    arguments = update.message.text.split()
    if len(arguments) == 1:
        user_id = data['last_user_id']
    else:
        user_id = arguments[1]
    # Loop through users
    for user in data['users']:
        if user['id'] == int(user_id):
            user['permission_to_print'] = True
            username = user['name']
            await context.bot.send_message(user['id'], "You now have permission to print :D")
            break;
    else:
        await update.message.reply_text("User id not found")
        return
    store_data()
    await update.message.reply_text("Permission to print of {} set to True".format(username))

async def removepermission_command(update: Update, context: CallbackContext) -> None:
    """Revoke permission to print"""
    if not user_is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this command")
        return
    # Check amount of arguments
    arguments = update.message.text.split()
    if len(arguments) == 1:
        user_id = data['last_user_id']
    else:
        user_id = arguments[1]
    for user in data['users']:
        if user['id'] == int(user_id):
            user['permission_to_print'] = False
            username = user['name']
            await context.bot.send_message(user['id'], "You no longer have permission to print...")
            break;
    else:
        await update.message.reply_text("User id not found")
        return
    store_data()
    await update.message.reply_text("Permission to print of {} set to False".format(username))

async def help_command(update: Update, context: CallbackContext) -> None:
    """Send instructions"""
    await update.message.reply_text(("Everything sent to this bot will be printed on a thermal receipt printer. (Posiflex PP-8000B)\n\n"
        "Currently the following message types are supported:\n"
        "- Text (when sending emojis their discription is printed, like: [FLUSHED FACE] or [SNOWMAN WITHOUT SNOW]. When the text contains a url, a QR code is printed after the text message which points to the url.)\n"
        "- Images (non-animated stickers also work)\n"
        "- Contacts\n"
        "- Polls (although it doesn't print updates when someone votes)\n"
        "- Location (prints the latitude and longitude and a qr code to google maps)\n\n"
        "Things the printer can't print:\n"
        "- Voice messages\n"
        "- Videos (including animated stickers)\n"
        "- Documents (I'm not printing your books or executables)\n\n"
        "The bot supports the following commands:\n"
        "  /help - Prints this message\n"
        "  /start - Prints hi and then this message\n"
        "  /stats - Prints stats about the printer\n"
        "  /anonymous - Check/Enable/Disable anonymous mode. In anonymous mode your name isn't printed above your message\n"))
    if user_is_admin(update.message.from_user.id):
        await update.message.reply_text(("You are the admin, so you can also use:\n"
        "  /listusers - Lists all users with their names, id and permission to print\n"
        "  /givepermission [id] - Gives a user permission to print. When no id is given the last registered user gets permission to print\n"
        "  /removepermission [id] - Revoke permission to print for a user. When no id is given the last registered user loses its permission to print.\n"))

async def stats_command(update: Update, context: CallbackContext) -> None:
    """Send stats"""
    await update.message.reply_text(("Total amount of messages printed: {}\n"
        "Text messages printed: {}\n"
        "Images printed: {}\n"
        "Contacts printed: {}\n"
        "Polls printed: {}\n"
        "Locations printed: {}\n").format(data['total_prints'], data['text_prints'], data['image_prints'], data['contact_prints'], data['poll_prints'], data['location_prints']))

async def anonymous_command(update: Update, context: CallbackContext) -> None:
    """Set anonymous status"""
    command_words = update.message.text.split()
    if len(command_words) == 1:
        for user in data['users']:
            if user['id'] == update.message.from_user.id:
                await update.message.reply_text("Anonymous: {}\nYou can enable or disable anonymous messages with /anonymous true/false".format(user['anonymous']))
                break;
    else:
        for user in data['users']:
            if user['id'] == update.message.from_user.id:
                user['anonymous'] = command_words[1].lower() == 'true'
                await update.message.reply_text("Anonymous setting set to: {}".format(user['anonymous']))
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

async def print_text(update: Update, context: CallbackContext) -> None:
    """Print received text message"""
    # Check if user exists
    if not user_exists(update.message.from_user):
        await update.message.reply_text("Please use the /start command before sending anything.")
        return
    # Check if user is spamming
    if is_spamming(update.message.from_user):
        await update.message.reply_text("Please wait a few minutes before sending another message.")
        return
    # Get name and permission to print
    name, permission_to_print = user_info(update.message.from_user)
    if not permission_to_print:
        await update.message.reply_text("You do not have permission to print anymore.")
        return
    # Print message
    logging.info("Message received: {}: {}".format(name, update.message.text))
    try:
        # Open serial interface
        p.open()
        # Print text
        p.text("{} - {}:\n{}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name, replace_emojis(update.message.text)))
        # Get urls in message and print qr codes for the urls
        urls = re.findall(URL_REGEX, update.message.text)
        for url in urls:
            p.text("\n{}".format(url))
            p.qr(url, size=8, center=True)
        # Cut, reply and update stats
        p.cut()
        # Close interface
        p.close();
        # Reply
        await update.message.reply_text("Printed!")
        update_stats('text')
    except:
        await error_printing(update, context, name)

async def print_photo(update: Update, context: CallbackContext) -> None:
    """Print received image"""
    # Check if user exists
    if not user_exists(update.message.from_user):
        await update.message.reply_text("Please use the /start command before sending anything.")
        return
    # Check if user is spamming
    if is_spamming(update.message.from_user):
        await update.message.reply_text("Please wait a few minutes before sending another message.")
        return
    # Get name and permission to print
    name, permission_to_print = user_info(update.message.from_user)
    if not permission_to_print:
        await update.message.reply_text("You do not have permission to print anymore.")
        return
    logging.info("Image received from {}".format(name))
    # Get image from Telegram
    if update.message.document != None:
        imageFile = await context.bot.get_file(update.message.document.file_id)
    elif update.message.sticker != None:
        if (update.message.sticker.is_animated):
            await update.message.reply_text("Cannot print animated stickers...")
            return
        # Get sticker
        imageFile = await context.bot.get_file(update.message.sticker.file_id)
    elif update.message.photo != None:
        imageFile = await context.bot.get_file(update.message.photo[-1].file_id)
    image = await imageFile.download_to_drive()
    # Resize image to correct size (maximum width of 512 pixels)
    img = Image.open(image)
    wpercent = (512/float(img.size[0]))
    hsize = int((float(img.size[1])*float(wpercent)))
    img = img.resize((512, hsize))
    img.save(image)
    # Print sender
    try:
        # Open serial interface
        p.open()
        # Print text
        p.text("{} - {}:\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name))
        # Print image
        p.image(image)
        # Wait some time before continuing with the rest, the following two lines fixed all my image printing problems
        time.sleep(1)
        p.text("\n")
        # Print caption
        if update.message.caption != None:
            p.text(update.message.caption)
        # Cut and reply
        p.cut()
        # Close interface
        p.close()
        # Reply
        await update.message.reply_text("Image printed!")
        update_stats('image')
    except:
        await error_printing(update, context, name)

async def print_audio(update: Update, context: CallbackContext) -> None:
    """Cannot print received audio"""
    # Check if user exists
    if not user_exists(update.message.from_user):
        await update.message.reply_text("Please use the /start command before sending anything.")
        return
    # Check if user is spamming
    if is_spamming(update.message.from_user):
        await update.message.reply_text("Please wait a few minutes before sending another message.")
        return
    # Get name and permission to print
    name, permission_to_print = user_info(update.message.from_user)
    if not permission_to_print:
        await update.message.reply_text("You do not have permission to print anymore.")
        return
    logging.info("Audio received from {}".format(name))
    await update.message.reply_text("Although the printer makes sound, my printer cannot make your sound...")

async def print_contact(update: Update, context: CallbackContext) -> None:
    """Print received contact"""
    # Check if user exists
    if not user_exists(update.message.from_user):
        await update.message.reply_text("Please use the /start command before sending anything.")
        return
    # Check if user is spamming
    if is_spamming(update.message.from_user):
        await update.message.reply_text("Please wait a few minutes before sending another message.")
        return
    # Get name and permission to print
    name, permission_to_print = user_info(update.message.from_user)
    if not permission_to_print:
        await update.message.reply_text("You do not have permission to print anymore.")
        return
    logging.info("Contact received from {}".format(name))
    # Print contact (I'm not sure why I implemented this)
    try:
        # Open serial interface
        p.open()
        # Print contact
        p.text("{} - {}\nName: {} {}\nTel: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name, update.message.contact.first_name, update.message.contact.last_name, update.message.contact.phone_number))
        # Cut and reply
        p.cut()
        # Close interface
        p.close()
        # Reply
        await update.message.reply_text("Contact printed")
        update_stats('contact')
    except:
        await error_printing(update, context, name)

async def print_document(update: Update, context: CallbackContext) -> None:
    """Don't print received document"""
    # Check if user exists
    if not user_exists(update.message.from_user):
        await update.message.reply_text("Please use the /start command before sending anything.")
        return
    # Check if user is spamming
    if is_spamming(update.message.from_user):
        await update.message.reply_text("Please wait a few minutes before sending another message.")
        return
    # Get name and permission to print
    name, permission_to_print = user_info(update.message.from_user)
    if not permission_to_print:
        await update.message.reply_text("You do not have permission to print anymore.")
        return
    logging.info("Document received from {}".format(name))
    await update.message.reply_text("How about no. Print your own documents!")

async def print_location(update: Update, context: CallbackContext) -> None:
    """Print received location"""
    # Check if user exists
    if not user_exists(update.message.from_user):
        await update.message.reply_text("Please use the /start command before sending anything.")
        return
    # Check if user is spamming
    if is_spamming(update.message.from_user):
        await update.message.reply_text("Please wait a few minutes before sending another message.")
        return
    # Get name and permission to print
    name, permission_to_print = user_info(update.message.from_user)
    if not permission_to_print:
        await update.message.reply_text("You do not have permission to print anymore.")
        return
    logging.info("Location received from {}".format(name))
    # Print latitude and longitude
    try:
        # Open serial interface
        p.open()
        # Print location
        p.text("{} - {}\nLatitude: {}\nLongitude: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name, update.message.location.latitude, update.message.location.longitude))
        p.qr("https://maps.google.com/?q={0:.14f},{1:.14f}".format(update.message.location.latitude, update.message.location.longitude), size=8)
        # Cut and reply
        p.cut()
        # Close interface
        p.close()
        # Reply
        await update.message.reply_text("Location printed")
        update_stats('location')
    except:
        await error_printing(update, context, name)

async def print_poll(update: Update, context: CallbackContext) -> None:
    """Print received poll"""
    # Check if user exists
    if not user_exists(update.message.from_user):
        await update.message.reply_text("Please use the /start command before sending anything.")
        return
    # Check if user is spamming
    if is_spamming(update.message.from_user):
        await update.message.reply_text("Please wait a few minutes before sending another message.")
        return
    # Get name and permission to print
    name, permission_to_print = user_info(update.message.from_user)
    if not permission_to_print:
        await update.message.reply_text("You do not have permission to print anymore.")
        return
    logging.info("Poll received from {}".format(name))
    # Print question and answers
    try:
        # Open serial interface
        p.open()
        # Print poll
        p.text("{} - {}:\nQuestion: {}\n".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), name, update.message.poll.question))
        p.set(align='left')
        for option in update.message.poll.options:
            p.text("    [] {}\n".format(option.text))
        p.set(align='center')
        # Cut and reply
        p.cut()
        # Close interface
        p.close()
        # Reply
        await update.message.reply_text("Poll printed")
        update_stats('poll')
    except:
        await error_printing(update, context, name)

async def print_video(update: Update, context: CallbackContext) -> None:
    """Don't print received video"""
    # Check if user exists
    if not user_exists(update.message.from_user):
        await update.message.reply_text("Please use the /start command before sending anything.")
        return
    # Check if user is spamming
    if is_spamming(update.message.from_user):
        await update.message.reply_text("Please wait a few minutes before sending another message.")
        return
    # Get name and permission to print
    name, permission_to_print = user_info(update.message.from_user)
    if not permission_to_print:
        await update.message.reply_text("You do not have permission to print anymore.")
        return
    logging.info("Video received from {}".format(name))
    # Reply
    await update.message.reply_text("Video's cannot be printed smartass.")

def main():
    """Starting point"""
    # Printer object
    global p
    p = Serial(devfile='/dev/ttyUSB1',
               baudrate=115200,
               bytesize=8,
               parity='N',
               stopbits=1,
               timeout=1.00,
               dsrdtr=True)

    # Printer settings
    p.set(align='center')
    # Print started message
    p.text("Bragi started!")
    p.cut()
    # Close connection
    p.close()
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
        data['last_user_id'] = 0
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
    
    # Create application
    application = Application.builder().token(TOKEN).build()

    # Handle commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("listusers", listusers_command))
    application.add_handler(CommandHandler("givepermission", givepermission_command))
    application.add_handler(CommandHandler("removepermission", removepermission_command))
    application.add_handler(CommandHandler("anonymous", anonymous_command))
    # Handle all the message types! I might be able to OR some lines, but this also works
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, print_text))
    application.add_handler(MessageHandler(filters.PHOTO, print_photo))
    application.add_handler(MessageHandler(filters.Document.IMAGE, print_photo))
    application.add_handler(MessageHandler(filters.AUDIO, print_audio))
    application.add_handler(MessageHandler(filters.VOICE, print_audio))
    application.add_handler(MessageHandler(filters.CONTACT, print_contact))
    application.add_handler(MessageHandler(filters.Document.ALL & ~filters.Document.IMAGE & ~filters.Document.VIDEO, print_document))
    application.add_handler(MessageHandler(filters.LOCATION, print_location))
    application.add_handler(MessageHandler(filters.POLL, print_poll))
    application.add_handler(MessageHandler(filters.Sticker.ALL, print_photo))
    application.add_handler(MessageHandler(filters.VIDEO, print_video))
    application.add_handler(MessageHandler(filters.Document.VIDEO, print_video))

    # Start polling
    application.run_polling()

if __name__ == '__main__':
    main()
