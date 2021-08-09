import requests, os, json, time, datetime, sys
import urllib.request
import argparse
from tinydb import TinyDB, Query
from settings import config

# База данных клипов
db_clips = TinyDB('clips_info.json')
# База данных фильтров для клипов
db_filter = TinyDB('filter.json')

def dow_clips():  
    """ Функция качает отфильтрованные клипы топ категорий Twitch """

    # Параметры для запросов
    cliend_id = config["Twitch"]["client_id"]
    client_secret = config["Twitch"]["client_secret"]
    top_count = int(config["Twitch"]["top_count"])
    # Получаем токен
    token = get_oa_token(cliend_id, client_secret)
    # Получаем топ категорий
    games, cursor = get_top_games(token, cliend_id, top_count)
    for i in range(top_count//100):
        temp_games, cursor = get_top_games(token, cliend_id, 100, cursor)
        games += temp_games
    # Получаем клипы категорий
    clips = []
    for i in range(top_count):
        temp_clips = get_game_clips(token, games[i]['id'])   
        clips += temp_clips    
    # Сортируем по дате создания клипов
    clips = sorted(clips, key=lambda k: k['created_at']) 
    # Сохраняем клипы
    for clip_info in clips:
        download_clip(clip_info)

def send_request(url, params = {}, headers = {}, get_method = False):
    """ Функция отправляет запрос 
    url - адрес запроса
    params - параметры запроса
    headers - заголовки запроса
    get_method - post или get метод """

    try:
        if get_method: response = requests.get(url, params = params, headers=headers)     
        else: response = requests.post(url, params = params, headers=headers) 
    except:
        print(sys.exc_info())
        return None
    else:
        if response.status_code == 200:
            return response.json()
        else:
            print(response.text)
            return None

def get_oa_token(client_id: str, client_secret: str):
    """ Функция получает токен авторизации 
    client_id - id Twitch приложения
    client_secret - секретный токен приложения """

    url = 'https://id.twitch.tv/oauth2/token'
    params = {'client_id': client_id, 'client_secret': client_secret, 'grant_type': 'client_credentials'}
    result = send_request(url, params=params)
    if result is None: return None
    else: return result['access_token']

def get_top_games(token: str, cliend_id: str, limit: int = 10, cursor = None):
    """ Функция получает данные о топ 20 категорий на Twitch 
    token - токен авторизации на Twitch 
    client_id - id Twtich приложения """

    limit = 10 if limit < 10 else limit
    limit = 100 if limit > 100 else limit
    url = 'https://api.twitch.tv/helix/games/top'
    headers = {'Authorization': f'Bearer {token}', 'Client-Id': cliend_id}
    params = {'limit': limit}
    if cursor is not None: params['offset'] = cursor
    result = send_request(url, params=params, headers=headers, get_method=True)
    if result is None: return [], None
    else: return result['data'], result['pagination']['cursor']

def get_clips(token: str, game_id: str, cursor: str = None):
    """ Функция получает Twitch клипы по категории 
    token - токен авторизации на Twitch 
    game_id - id категории на Twitch
    cursor - токен для получения следующего списка клипов """

    url = 'https://api.twitch.tv/helix/clips'
    headers = {'Authorization': f'Bearer {token}', 'Client-Id': 'iwyangrju70mippqv0ek3yzmn5ln20'}
    # Дата начала
    started_at = datetime.datetime.today() - datetime.timedelta(days=1)
    started_at = started_at.replace(hour=0, minute=0, second=0, microsecond=0)
    started_at = started_at.isoformat('T') + 'Z'
    # Дата окончания
    ended_at = datetime.datetime.today() - datetime.timedelta(days=0)
    ended_at = ended_at.replace(hour=0, minute=0, second=0, microsecond=0)
    ended_at = ended_at.isoformat('T') + 'Z'
    # Параметры
    params = {'game_id': game_id, 'started_at': started_at, 'ended_at': ended_at, 'first': 100}
    if cursor is not None: params['after'] = cursor
    # Получаем
    result = send_request(url, params, headers, get_method=True)
    if result is None: return [], None
    else: return result['data'], result['pagination']['cursor'] if 'cursor' in result['pagination'] else None

def download_clip(clip_info):
    """ Функция сохраняет клип 
    clip_info - данные клипа """

    video_id = clip_info['video_id']
    out_filename = f'clips/{video_id}.mp4'
    mp4_url = clip_info['thumbnail_url'].split("-preview",1)[0] + ".mp4"   
    try:
        # Скачиваем клип         
        urllib.request.urlretrieve(mp4_url, out_filename)  
        # Заносим в бд
        db_clips.insert(clip_info)
        time.sleep(1);
        print(f'{out_filename} успешно')
        return True
    except:
        return False

def get_game_clips(token, game_id):
    """ Функция получает клипы Twitch категории
    token - токен авторизации
    game_id - id категории Twitch
    clips - массив клипов
    """

    # Получаем клипы
    valided_clips = []
    game_clips, cursor = get_clips(token, game_id)
    while len(game_clips) > 0 and cursor is not None:
        for clip_info in game_clips:
            if check_filter_validation(clip_info):
                valided_clips.append(clip_info)
        game_clips,cursor = get_clips(token,game_id, cursor)
    return valided_clips

def check_filter_validation(clip_info):
    """ Функция проверяет проходит ли клип фильтр
    clip_info - структура данных клипа """

    # Находим строку параметров фильтра для клипа
    clip_filters = db_filter.search(Query().id == clip_info['game_id'])
    if len(clip_filters) == 0: clip_filters = db_filter.search(Query().id == '0')
    game_filter = clip_filters[0]
    # Проверка
    view_count = clip_info['view_count']
    duration = clip_info['duration']
    lang_check = (
                 (clip_info['language'] == 'en' and view_count >= int(game_filter['en_view_count'])) or
                 (clip_info['language'] == 'ru' and view_count >= int(game_filter['ru_view_count']))
                 )

    duration_check = duration <= int(game_filter['duration'])
    
    return lang_check and duration_check