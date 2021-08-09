import telebot
import os, time
from settings import config
from tinydb import TinyDB, Query

bot = telebot.TeleBot(config["TelegramBot"]["token"]) # объект телеграм бота

def send_clips():
    db_clips = TinyDB('clips_info.json')
    fileList = os.listdir('clips')
    #fileList.sort(key=os.path.getctime)
    for i in fileList:
        try:
            video_id = i.split('.mp4')[0]
            # Находим данные клипа
            clip_info = db_clips.search(Query().video_id == video_id)[0]
            # Формируем описание
            caption = '{0}\nКанал: {1}\nПросмотров: {2}'.format(clip_info['title'], clip_info['broadcaster_name'], clip_info['view_count'])
            # Отправляем
            file = open(os.path.join('clips/' + i), 'rb')
            bot.send_video(config['TelegramBot']['chat_id'], file, width=640, height=480, caption=caption, thumb=clip_info['thumbnail_url'])
            file.close()
            time.sleep(1);
            print(f'{i} успешно')
        except:
            print(f'{i} неудачно')

    db_clips.close()
