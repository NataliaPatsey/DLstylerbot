import CONFIG
import telebot

bot = telebot.TeleBot(CONFIG.token)


@bot.message_handler(commands=['start'])
def start_message(message):

        send = bot.send_message(message.chat.id, 'i have been back\n send photo')
        bot.register_next_step_handler(send,get_user_content)
        return

@bot.message_handler(content_types=['photo'])
def get_user_content(message):
        file_info = bot.get_file(message.photo[-1].file_id)
        print(message.from_user.id,file_info)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f'tmp/content{message.chat.id}.jpg', 'wb') as new_file:
                new_file.write(downloaded_file)
        send = bot.send_message(message.from_user.id, 'фото принято, шли стиль')
        bot.register_next_step_handler(send, get_user_style)
        return
@bot.message_handler(content_types=['photo'])
def get_user_style(message):
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(f'tmp/style{message.chat.id}.jpg', 'wb') as new_file:
                new_file.write(downloaded_file)
        bot.send_message(message.from_user.id, 'пока все')
        #bot.register_next_step_handler('стиль принят')
        return

bot.infinity_polling()
