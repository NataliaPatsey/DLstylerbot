import CONFIG
import telebot
from img_editor import Img_editor
from styler import run_style_transfer

import torchvision.models as models

from model_config import device, content_layers_default, style_layers_default, cnn_normalization_std,cnn_normalization_mean
from telebot import types
import os
import gc


bot = telebot.TeleBot(CONFIG.token)



@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    item1 = types.InlineKeyboardButton(text="Фото", callback_data='photo')
    item2 = types.InlineKeyboardButton(text="Стиль", callback_data='style')
    markup.add(item1,item2 )
    send = bot.send_message(message.chat.id,
                            'Что будешь слать сначала?',
                            reply_markup=markup)


@bot.callback_query_handler(func=lambda call:True)
def switcher(call_obj):
    if call_obj.message:
        if call_obj.data == 'photo':
            send = bot.send_message(call_obj.from_user.id, 'шли фото')
            bot.register_next_step_handler(send, get_user_content)
        elif call_obj.data == 'style':
            send = bot.send_message(call_obj.from_user.id, 'шли стиль')
            bot.register_next_step_handler(send, get_user_style)
        else:
            send = bot.send_message(call_obj.from_user.id, 'чтото пошло не так :( n/ давай заново')
            bot.register_next_step_handler(send, start_message)
        bot.answer_callback_query(callback_query_id=call_obj.id)




@bot.message_handler(content_types=['photo'])
def get_user_content(message):
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(f'tmp/content{message.chat.id}.jpg', 'wb') as new_file:
        new_file.write(downloaded_file)
    bot.send_message(message.from_user.id, 'фото принято')
    if os.path.exists(f'tmp/style{message.chat.id}.jpg'):
        bot.send_message(message.from_user.id, 'стиль на месте, мы начали')
        image_corrector(message)
    else:
        send = bot.send_message(message.from_user.id, 'шли стиль')
        bot.register_next_step_handler(send, get_user_style)

@bot.message_handler(content_types=['photo'])
def get_user_style(message):
    file_info = bot.get_file(message.photo[-1].file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    with open(f'tmp/style{message.chat.id}.jpg', 'wb') as new_file:
        new_file.write(downloaded_file)
    bot.send_message(message.from_user.id, 'стиль принят')
    if os.path.exists(f'tmp/content{message.chat.id}.jpg'):
        bot.send_message(message.from_user.id, 'фото на месте, мы начали')
        image_corrector(message)
    else:
        send = bot.send_message(message.from_user.id, 'шли фото')
        bot.register_next_step_handler(send, get_user_content)

def image_corrector(message):
    img_ed = Img_editor()
    content_img = img_ed.image_loader(f'tmp/content{message.chat.id}.jpg')
    img_clear = img_ed.image_unloader(content_img.squeeze(0))
    img_clear.save(f'tmp/content{message.chat.id}.jpg')

    style_img = img_ed.image_loader(f'tmp/style{message.chat.id}.jpg')
    style_clear = img_ed.image_unloader(style_img.squeeze(0))
    style_clear.save(f'tmp/style{message.chat.id}.jpg')

    bot.send_message(message.from_user.id, 'коррекция пройдена')


    print('начали обучение')
    cnn = models.vgg19(pretrained=True).features.to(device).eval()

    input_img = content_img.clone()

    output = run_style_transfer(cnn, cnn_normalization_mean, cnn_normalization_std,
                                content_img, style_img, input_img)
    print('закончили обучение обучение')
    result = img_ed.image_unloader(output.squeeze(0))
    result.save(f'tmp/result{message.chat.id}.jpg')
    print('закончили и сохранили')
    gc.collect()
    bot.send_photo(message.chat.id, open(f'tmp/result{message.chat.id}.jpg', 'rb'), 'результат')
    send = bot.send_message(message.from_user.id, 'повторим?')
    start_message(message)


bot.infinity_polling()
