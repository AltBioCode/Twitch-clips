from twitch_module import *
from telegram_module import *
     
print('1 - Скачать клипы \n2 - Отправить клипы')
action = input()
if action == '1': dow_clips()
elif action == '2': send_clips()
