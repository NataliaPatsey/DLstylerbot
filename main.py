
import time, os, shutil
import flask
import gc
import pickle
import telebot
from telebot import types
from BOT_CONFIG import TOKEN,HOST,LISTEN,PORT,CERT,CERT_KEY
from img_editor import Img_editor
from styler import Styler



WEBHOOK_URL_BASE = "https://%s:%s" % (HOST, PORT)
WEBHOOK_URL_PATH = "/bot/"

bot = telebot.TeleBot(TOKEN)
app = flask.Flask(__name__)
context = (CERT,CERT_KEY)


bot.remove_webhook()

time.sleep(2)

# устанавливаем webhook
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
                certificate=open(CERT, 'r'))


# принемаем update
@app.route(WEBHOOK_URL_PATH, methods=['POST'])
def webhook():
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)

#----------
@bot.message_handler(commands=['start'])
def start_message(message):
    for f in ['content','style','result']:
        if os.path.exists(f'tmp/{f}{message.chat.id}.jpg'):
            os.remove(f'tmp/{f}{message.chat.id}.jpg')
    if os.path.exists(f'tmp/params{message.chat.id}.pkl'):
        os.remove(f'tmp/params{message.chat.id}.pkl')

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(text='Фото', callback_data='photo'),
               types.InlineKeyboardButton(text='Стиль', callback_data='style'))
    bot.send_message(message.chat.id,
                            'Что будешь слать сначала?',
                            reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ['add_style','add_content','s1','s2','s3'])
def switcher_add(call_obj):
    if call_obj.data == 'add_style':
        bot.edit_message_reply_markup(call_obj.message.chat.id, call_obj.message.message_id)
        bot.send_message(call_obj.from_user.id, 'Ok, добавим стиля!')
        image_corrector(call_obj.from_user.id, add_type='style', msg='Работать буду мин 10')
    elif call_obj.data == 'add_content':
        bot.edit_message_reply_markup(call_obj.message.chat.id, call_obj.message.message_id)
        bot.send_message(call_obj.from_user.id, 'Ок, добавим контента!')
        image_corrector(call_obj.from_user.id,add_type='content',msg='Работать буду мин 10')
    elif call_obj.data == 's3':
        copy_bot_style(call_obj.from_user.id, 3)
        bot.edit_message_reply_markup(call_obj.message.chat.id, call_obj.message.message_id)
        bot.send_message(call_obj.from_user.id, 'Ок, запомнил [Подсолнухи]')
        file_checker(call_obj.from_user.id)
    elif call_obj.data == 's2':
        copy_bot_style(call_obj.from_user.id, 2)
        bot.edit_message_reply_markup(call_obj.message.chat.id, call_obj.message.message_id)
        bot.send_message(call_obj.from_user.id, 'Ок, запомнил [Карандаш]')
        file_checker(call_obj.from_user.id)
    elif call_obj.data == 's1':
        bot.edit_message_reply_markup(call_obj.message.chat.id, call_obj.message.message_id)
        copy_bot_style(call_obj.from_user.id, 1)
        bot.send_message(call_obj.from_user.id, 'Ок, запомнил [Звезды]')
        file_checker(call_obj.from_user.id)


@bot.callback_query_handler(func=lambda call:True)
def switcher(call_obj):
    if call_obj.message:
        if call_obj.data == 'photo':
            send = bot.send_message(call_obj.from_user.id, 'шли фото')
            bot.register_next_step_handler(send, get_user_img, 'content')
        elif call_obj.data == 'style':
            get_style_way(call_obj.from_user.id)
        elif call_obj.data == 'my_style':
            send = bot.send_message(call_obj.from_user.id, 'шли стиль')
            bot.register_next_step_handler(send, get_user_img, 'style')
        elif call_obj.data == 'bot_style':
            bot.send_photo(call_obj.from_user.id, open(f'tmp/s1.jpg', 'rb'), 'Звезды')
            bot.send_photo(call_obj.from_user.id, open(f'tmp/s2.jpg', 'rb'), 'Карандаш')
            bot.send_photo(call_obj.from_user.id, open(f'tmp/s3.jpg', 'rb'), 'Подсолнухи')
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(types.InlineKeyboardButton(text="Звезды", callback_data='s1'),
                       types.InlineKeyboardButton(text="Карандаш", callback_data='s2'),
                       types.InlineKeyboardButton(text="Подсолнухи", callback_data='s3')
                       )
            bot.send_message(call_obj.from_user.id, 'Выбирай:', reply_markup=markup)
        elif call_obj.data == 'start':
            bot.send_message(call_obj.from_user.id, 'Жми /start')
        else:
            send = bot.send_message(call_obj.from_user.id, 'чтото пошло не так :( n/ давай заново /start')
            bot.register_next_step_handler(send, start_message)
        bot.edit_message_reply_markup(call_obj.message.chat.id, call_obj.message.message_id)


@bot.message_handler(content_types=['photo'])
def get_user_img(message, type=None):
    if type is None:
        bot.send_message(message.from_user.id, 'просто так файл слать не надо,  давай по порядку')
    file_info = bot.get_file(message.photo[-1].file_id)
    filename, file_ext = os.path.splitext(file_info.file_path)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(f'tmp/{type}{message.chat.id}{file_ext}', 'wb') as new_file:
        new_file.write(downloaded_file)
    del (downloaded_file)
    del (file_info)
    file_checker(message.from_user.id)


#Функция переноса стиля
def image_corrector(user_id, add_type=None, msg=None):
    if msg is not None:
        bot.send_message(user_id, msg)

    if add_type is None:
        style_img = img_size_corrector(user_id, 'style')
        content_img = img_size_corrector(user_id, 'content')
        bot.send_message(user_id, 'Немного подкорректировал картинки. Работать буду мин 10')
    else:
        style_img = Img_editor.image_loader(f'tmp/style{user_id}.jpg')
        content_img = Img_editor.image_loader(f'tmp/content{user_id}.jpg')

    styler = Styler(content_img, style_img)

    if add_type == 'style':
        params = load_patams(user_id)
        style_weight = params['style_weight'] + 50000
        content_weight = params['content_weight']
        styler.weight_setter(style_weight,content_weight)
    if add_type == 'content':
        params = load_patams(user_id)
        style_weight = params['style_weight']
        content_weight = params['content_weight'] + 5
        styler.weight_setter(style_weight, content_weight)

    output, params = styler.run_style_transfer()
    result = Img_editor.image_unloader(output.squeeze(0))
    result.save(f'tmp/result{user_id}.jpg')
    save_params(params, user_id)
    gc.collect()
    bot.send_photo(user_id, open(f'tmp/result{user_id}.jpg', 'rb'), 'результат')
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(text="усилить Фото", callback_data='add_content'),
               types.InlineKeyboardButton(text="усилить Стиль", callback_data='add_style'),
               types.InlineKeyboardButton(text="хочу все новое", callback_data='start')
               )
    bot.send_message(user_id, 'что дальше?',reply_markup=markup)


# Фун-я отображения меню для выбора способа загрузки стиля
def get_style_way(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2,)
    markup.add(types.InlineKeyboardButton(text="Мой стиль", callback_data='my_style'),
               types.InlineKeyboardButton(text="Выбрать", callback_data='bot_style')
               )
    bot.send_message(user_id, 'Свой пришлешь или выберешь?', reply_markup=markup)

# Фун-я копирует предустановленный стиль к пользовательский style
def copy_bot_style(user_id,style_id):
    shutil.copy2(f'tmp/s{style_id}.jpg',f'tmp/style{user_id}.jpg')


# Фун-я проверки наличия файлов content и style до начала работы image_corrector
def file_checker(user_id):
    if not os.path.exists(f'tmp/style{user_id}.jpg'):
        get_style_way(user_id)
    elif not os.path.exists(f'tmp/content{user_id}.jpg'):
        send = bot.send_message(user_id, 'шли фото')
        bot.register_next_step_handler(send, get_user_img,'content')
    else:
        bot.send_message(user_id, 'все на месте, творИм!')
        image_corrector(user_id)


# Фун-я сохранения значений весов, используемых на предыдущем шаге
def save_params(obj, id ):
    with open(f'tmp/params{id}.pkl', 'wb+') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


# Фун-я загрузки значений весов, используемых на предыдущем шаге
def load_patams(id):
    with open(f'tmp/params{id}.pkl', 'rb') as f:
        return pickle.load(f)

# Фун-я корректировки картинки, масштабирует размер, обрезает лишнее, приводит к размеру imsize, заданному в model_config
def img_size_corrector(id,type_file):
    right_tensor = Img_editor.image_loader(f'tmp/{type_file}{id}.jpg')
    right_file = Img_editor.image_unloader(right_tensor.squeeze(0))
    right_file.save(f'tmp/{type_file}{id}.jpg')
    return right_tensor


# Handle справки
@bot.message_handler(commands=['help'])
def send_welcome(message):
    bot.reply_to(message,
                 ("Этот бот переносит стиль с картинки-стиля на картинку-фото.\n"
                  "Фото надо прислать самому.\n"
                  "Стиль можно выбрать из предустановленных или прислать свой.\n"
                  "После обработки можно повторно запустить процесс на тех же Фото и Стиле, поменяв немного веса значимости.\n"
                  "Сложной логики в работе нет, в любой непонятой ситуации жми /start.\n"))


# Handle на введенный пользователем текст
@bot.message_handler(func=lambda message: True, content_types=['text'])
def echo_message(message):
    bot.send_message(message.from_user.id , 'Не надо ничего писать, жми(набери) /help или /start , а потом жми кнопки')


#
app.run(host=LISTEN,
        port=PORT,
        ssl_context=(CERT, CERT_KEY),
        debug=True)