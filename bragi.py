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
import RPi.GPIO as GPIO
import threading

# Enable logging
logging.root.setLevel(logging.NOTSET)
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

# Url Regex
URL_REGEX = r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'\".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"""

def printqueue_button_callback(channel):
    print_unprinted_messages()

def start_blinking():
    if not e.isSet():
        t = threading.Thread(name='non-block', target=blink_led, args=(e,))
        t.start()
        t.join()
        e.clear()

def stop_blinking():
    e.set()

def blink_led(e):
    """Blink led of button"""
    while True:
        GPIO.output(18, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(18, GPIO.LOW)
        time.sleep(1)
        if e.is_set():
            break

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
    await update.message.reply_text("Hi! This is Bragi the receipt printer. The printer will print all text messages or photos that are sent to it. The bot is named after the skaldic god of poetry in Norse mythology. Type /help for more info.")
    #await help_command(update, context)
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
        "\n"
        "The bot supports the following commands:\n"
        "  /help - Prints this message\n"
        "  /start - Prints hi and then this message\n"
        "  /stats - Prints stats about the printer\n"
        "  /anonymous - Check/Enable/Disable anonymous mode. In anonymous mode your name isn't printed above your message\n"))
    if user_is_admin(update.message.from_user.id):
        await update.message.reply_text(("You are the admin, so you can also use:\n"
        "  /listusers - Lists all users with their names, id and permission to print\n"
        "  /givepermission [id] - Gives a user permission to print. When no id is given the last registered user gets permission to print\n"
        "  /removepermission [id] - Revoke permission to print for a user. When no id is given the last registered user loses its permission to print.\n"
        "  /printqueue - Prints all messages in the queue\n"
        "  /emptyqueue - Sets all received messages to printed\n"))

async def stats_command(update: Update, context: CallbackContext) -> None:
    """Send stats"""
    await update.message.reply_text(("Total amount of messages printed: {}\n"
        "Text messages printed: {}\n"
        "Images printed: {}\n").format(data['total_prints'], data['text_prints'], data['image_prints']))

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

async def get_text_message(update: Update, context: CallbackContext) -> None:
    """Get and store received text message"""
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
    # Store message
    message = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'sender': name,
        'text': replace_emojis(update.message.text),
        'image_path': None,
        'printed': False,
        }
    # Print message
    if print_text_message(message):
        # Reply
        await update.message.reply_text("Printed!")
    else:
        await error_printing(update, context, name)

    # Add message to list
    messages.append(message)
    # Save messages to disk
    with open('messages.json', 'w') as save_file:
        json.dump(messages, save_file)
    # Start led
    start_blinking()

def print_text_message(message):
    """Prints a text message"""
    try:
        # Open serial interface
        p.open()
        # Print text
        p.text("{} - {}:\n{}\n".format(message['timestamp'], message['sender'], message['text']))
        # Get urls in message and print qr codes for the urls
        urls = re.findall(URL_REGEX, message['text'])
        for url in urls:
            p.text("\n{}".format(url))
            p.qr(url, size=8, center=True)
        # Cut, reply and update stats
        p.cut()
        # Close interface
        p.close();
        # Update stats
        update_stats('text')
        return True
    except:
        return False

async def get_photo_message(update: Update, context: CallbackContext) -> None:
    """Get and store received image"""
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
    print(image)
    # Resize image to correct size (maximum width of 512 pixels)
    img = Image.open(image)
    wpercent = (512/float(img.size[0]))
    hsize = int((float(img.size[1])*float(wpercent)))
    img = img.resize((512, hsize))
    img.save(image)
    # Get caption
    caption = update.message.caption
    # Replace emojis
    if caption != None:
        caption = replace_emojis(caption),
    # Store message
    message = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'sender': name,
        'text': caption,
        'image_path': str(image),
        'printed': False,
        }
    # Print message
    if print_photo_message(message):
        # Reply
        await update.message.reply_text("Printed!")
    else:
        await error_printing(update, context, name)
    # Add message to list
    messages.append(message)
    # Save messages to disk
    with open('messages.json', 'w') as save_file:
        json.dump(messages, save_file)
    # Start led
    start_blinking()

def print_photo_message(message):
    """Prints message with photo"""
    try:
        # Open serial interface
        p.open()
        # Print text
        p.text("{} - {}:\n".format(message['timestamp'], message['sender']))
        # Print image
        p.image(message['image_path'])
        # Wait some time before continuing with the rest, the following two lines fixed all my image printing problems
        time.sleep(1)
        p.text("\n")
        # Print caption
        if message['text'] != None:
            p.text(message['text'])
        # Cut and reply
        p.cut()
        # Close interface
        p.close()
        # Update stats
        update_stats('image')
        return True
    except:
        return False

async def get_unsupported_message(update: Update, context: CallbackContext) -> None:
    """ Reply that type is unsupported"""
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
    # Log
    logging.info("Unsupported message received from {}".format(name))
    # Reply
    await update.message.reply_text("This type of message is unsupported. Try a text message or an image.")

async def print_unprinted_messages_command(update: Update, context: CallbackContext):
    # Check is user is admin
    if not user_is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this command")
        return
    print_unprinted_messages()
    await update.message.reply_text("All unprinted messages printed.")

def print_unprinted_messages():
    # Loop over messages
    for message in messages:
        if message['printed'] == False:
            if message['image_path'] == None:
                print_text_message(message)
            else:
                print_photo_message(message)
                time.sleep(1)

async def set_all_printed_command(update: Update, context: CallbackContext):
    """Set all messages to printed"""
    # Check is user is admin
    if not user_is_admin(update.message.from_user.id):
        await update.message.reply_text("You are not allowed to use this command")
        return
    set_all_printed()
    await update.message.reply_text("Queue emptied")

def set_all_printed():
    # Loop over messages
    for message in messages:
        message['printed'] = True
    # Save messages to disk
    with open('messages.json', 'w') as save_file:
        json.dump(messages, save_file)
    # Stop blinking
    stop_blinking()

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
    # Load message list
    global messages
    try:
        with open("messages.json") as save_file:
            messages = json.load(save_file)
    except FileNotFoundError:
        logging.info("messages.json file not found. Creating empty list.")
        messages = []

    # Start the bot
    TOKEN = None
    try:
        with open("token.txt") as f:
            TOKEN = f.read().strip()
    except FileNotFoundError:
        logging.error("No token file found. Add your token in a file called token.txt in the same directory as the bot.")
        return
    
    # Initialize GPIO
    # Print messages button
    GPIO.setwarnings(False) # Ignore warning for now
    GPIO.setmode(GPIO.BCM) # Use physical pin numbering
    GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_UP) 
    GPIO.add_event_detect(4,GPIO.FALLING,callback=printqueue_button_callback) # Setup event on pin 10 rising edge
    # LED in button
    GPIO.setup(18, GPIO.OUT)

    # Create event for thread
    global e 
    e = threading.Event()

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
    application.add_handler(CommandHandler("printqueue", print_unprinted_messages_command))
    application.add_handler(CommandHandler("emptyqueue", set_all_printed_command))
    # Handle text messages and photos
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, get_photo_message))
    application.add_handler(MessageHandler(filters.Document.IMAGE, get_photo_message))
    application.add_handler(MessageHandler(filters.Sticker.ALL, get_photo_message))
    # Send reply when sending unupported message
    application.add_handler(MessageHandler(filters.ALL & ~filters.TEXT & ~filters.COMMAND & ~filters.PHOTO & ~filters.Document.IMAGE & ~filters.Sticker.ALL, get_unsupported_message))

    # Start polling
    application.run_polling()

    # Cleanup gpio
    GPIO.cleanup()

if __name__ == '__main__':
    main()
