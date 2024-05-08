import math
import time

import telebot
import schedule
from threading import Thread
import datetime
import logging
from telebot.types import Message, ReplyKeyboardMarkup
from speech import text_to_speech, speech_to_text, count_gpt_tokens, ask_gpt
from data_bases import (selection_stt_blocks,  insert_info, check_quantity, create_table, check_summ_tokens,
                        check_summ_tts_symbol)
from config import (TABLE_NAME, MAX_STT_BLOCKS, MAX_GPT_TOKENS_FOR_QUERE, MAX_USERS_IN_DIALOG, TOKEN_TELEGRAMM,
                    MAX_TTS_STT_TOKENS, MAX_GPT_TOKENS_USER, SYSTEM_CONTENT, MAX_FOR_USER_TTS_STT_SYMBOL)





bot = telebot.TeleBot(TOKEN_TELEGRAMM)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",encoding='utf-8',
    filename="log_file.txt",
    filemode="w",
)
user_history = {}
def block_duraction_limit(message, duraction):
    user_id = message.from_user.id
    audio_blocks = math.ceil(duraction/15)
    logging.info('Получено количество блоков (/stt).')
    all_blocks = selection_stt_blocks(user_id, TABLE_NAME)[0] + audio_blocks
    logging.info('Получено значение максимума для блоков (/stt).')
    if all_blocks > MAX_STT_BLOCKS:
        bot.send_message(user_id, 'Перебор с блоками(/stt)'
                                  'Попробуйте иначе изложить свои мысли : ')
        bot.register_next_step_handler(message, get_voice)
        logging.info(f'Слишком много блоков : {all_blocks}/{MAX_STT_BLOCKS}')
        return
    if duraction > 60:
        bot.send_message(user_id, 'Длинное гс!\n'
                                  'Перезапишите!')
        bot.register_next_step_handler(message, get_voice)
        logging.info('Слишком больша длина аудио-запроса.')
        return
    return audio_blocks

def gpt_tokens_text_limit(message, text):
    user_id = message.from_user.id
    tokens = count_gpt_tokens(text)
    logging.info('Получено число токенов в запросе')
    if not tokens < MAX_GPT_TOKENS_FOR_QUERE:
        bot.send_message(user_id, 'Слишком большой запрос!\n'
                                  'Попробуйте снова.')
        logging.info('Слишком большой запрос. Отмена генерации ответа.\n'
                     f'{tokens}/{MAX_GPT_TOKENS_USER}')
        return
    return tokens

def all_gpt_tokens_limit(message):
    user_id = message.from_user.id
    tokens = check_summ_tokens(user_id)
    tokens = tokens[0]
    logging.info('Получено значение всех токенов, использованных пользователем.')
    if tokens > MAX_GPT_TOKENS_USER:
        bot.send_message(user_id, 'Вы израсходовали все токены.')
        logging.info('Все токены израсходованы.\n'
                     )
        return 0
    return tokens


def create_keyboard(buttons):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, one_time_keyboard=True)
    keyboard.add(*buttons)
    logging.info('Создана клавиатура.')
    return keyboard

@bot.message_handler(commands=['start'])
def start_message(message: Message):
    user_id = message.from_user.id
    user_one_name = message.from_user.first_name
    user_last_name = message.from_user.last_name
    logging.info('Получен id пользователя.')
    create_table(TABLE_NAME)
    logging.info('Создана таблица SQL.')
    users_in_dialog = check_quantity(TABLE_NAME)
    users_in_dialog = users_in_dialog[0]

    logging.info('Получено количетсво пользоватлей, пользующихся этой нейросетью в данный момент.')
    tokens = all_gpt_tokens_limit(message)
    if not tokens:
        bot.send_message(user_id, 'У вас закончились токены.')
        logging.info(f'У пользователя {user_one_name} {user_last_name}с id {user_id} закончились токены.')
        return
    if users_in_dialog > MAX_USERS_IN_DIALOG:
        bot.send_message(user_id, 'Превышено количество пользователей.\n'
                                  'Мест нет!')
        logging.info('Слишком много пользователей, использующих эту нейросеть.')
        return
    user_history['user_id'] = user_id
    user_history[user_id] = {}
    session = 1
    user_history[user_id]['session'] = session
    bot.send_message(user_id, f'Приветсвую вас, {user_one_name} {user_last_name}с id {user_id}!\n'
                              f'Я бот-GPT.')
    logging.info('Приветственное сообщения от бота.')
    time.sleep(2)
    bot.send_message(user_id, 'Моя функциональность. \n'
                                 'Играю роль переводчика :\n'
                              '1. Перевожу аудио в текст;\n'
                              '2. Перевожу текст в аудио;\n'
                              '3. Даю ответы на поставленные задачи таким же форматом,'
                              ' каким клиент ввёл вопрос - а именно :\n'
                              'Голос - голос; текст - текст.')
    time.sleep(2)
    bot.send_message(user_id, 'Выбери мою функцию : \n'
                              '1. Перевод текста в голос - /tts;\n'
                              '2. перевод голоса пользователя  в текст - /stt; \n'
                              '3. задать вопрос текстом - /quest_text;\n'
                              '4. задать вопрос голосом - /quest_voice',reply_markup = create_keyboard(['/stt', '/tts',
                                                                                                        '/quest_text',
                                                                                                         '/quest_voice']))



    time.sleep(1)
    logging.info('Все приветственные сообщения выведены.')

def quest_day():
    try:
        user_id = user_history['user_id']
        system_cont = 'Ты бот-всезнайка, который знает все  интересные факты. Отвечай кратко и по делу.Если нет фактов, то расскажи смешную шутку'
        str_date = datetime.datetime.now()
        data = datetime.datetime.strftime(str_date, '%d.%m.%Y')
        status, question = ask_gpt(system_cont, f'Интересный факт на {data} в мире на абсолютно любые темы.')
        if status:
            bot.send_message(user_id, f'Интересный факт на {data}: {question}')
            logging.info('Бот прислал интересный факт.')
    except Exception as e:
        print(e)
        return

def shedule_runner():
    while True:
        schedule.run_pending()
        time.sleep(1)


@bot.message_handler(commands=['quest_voice'])
def quest_vo(message: Message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Хорошо.\n'
                              'Запиши мне гс :')
    logging.info('Пользователь использует запрос методом stt')
    logging.info('Бот запросил ГС.')
    bot.register_next_step_handler(message, get_voice)

def get_voice(message: Message):
    user_id = message.from_user.id
    try:
        if not message.voice:
            bot.send_message(user_id, 'Ваш запрос не аудио!\n'
                                      'До свидания!', reply_markup=create_keyboard(['/debug', '/restart',
                                                                           '/count_all_tokens_gpt',
                                                                                    '/count_all_tts_symbol']))
            logging.info('Пользователь ошибся с вводом.')
            return
        blocks = block_duraction_limit(message, message.voice.duration)
        if blocks:
            user_history[user_id]['blocks'] = blocks
            logging.info(f'Количество блоков получено.{blocks} блок(-a;-ов).')
            file_id = message.voice.file_id
            file_info = bot.get_file(file_id)
            file = bot.download_file(file_info.file_path)
            logging.info('Аудио файл успешно сохранен.')
            status, result, len_text = speech_to_text(file)
            user_history[user_id]['len_result'] = len_text
            logging.info('Запрос пользователя (из речи в текст).')
            if not status:
                bot.send_message(user_id, 'Ошибка')
                logging.info('Ошибка!')
                return
            if len_text > MAX_TTS_STT_TOKENS:
                bot.send_message(user_id, 'Слишком большой ответ от GPT,\n Попробуйте перефразировать ваш запрос.')
                logging.info('Пользователь запросил слишком длинный запрос.')
                return
            bot.send_message(user_id, result)
            user_history[user_id]['result_voice'] = result
            logging.info('Результат поучен.')
            time.sleep(2)

            bot.send_message(user_id, 'Выберите голос для ответа GPT :', reply_markup=create_keyboard(['jane', 'ermil']))
            bot.register_next_step_handler(message, get_voice_for_answer)
            return
    except Exception as e:
        bot.send_message(user_id, f'Ошибка {e}', reply_markup=create_keyboard(['/debug', '/restart',
                                                                                     '/count_all_tokens_gpt',
                                                                               'count_all_tts_symbol']))

def get_voice_for_answer(message: Message):
    user_id = message.from_user.id
    try:
        voice_answer = message.text
        logging.info('Голос для ответа получен.')
        user_history[user_id]['voice_answer'] = voice_answer
        if user_history[user_id]['voice_answer'] == 'jane':
            logging.info('Голос (Jain).')
            bot.send_message(user_id, 'Good. Выбери тип голоса для синтеза речи', reply_markup=create_keyboard(['evil',
                                                                                                                'neutral',
                                                                                                                'good']))
            logging.info('Бот запросил тип голоса для синтеза речи.')
            bot.register_next_step_handler(message, emotion_for_answer)
            return
        elif user_history[user_id]['voice_answer'] == 'ermil':
            logging.info('Голос Ermil.')
            bot.send_message(user_id, 'Good. Выбери тип голоса для синтеза речи',
                             reply_markup=create_keyboard(['good', 'neutral']))
            logging.info('Бот запросил тип голоса для синтеза речи.')
            bot.register_next_step_handler(message, emotion_for_answer)
            return
        else:
            logging.info('Ошибка выбора голоса..')
            bot.send_message(user_id, 'Вы неверно выбрали голос для синтеза.\n\nВыберите голос для синтеза.',
                             reply_markup=create_keyboard(['jane', 'ermil']))
            bot.register_next_step_handler(message, get_voice_for_answer)
            return
    except Exception as e:
        bot.send_message(user_id, f'Ошибка! {e}\n'
                                  'Попробуйте снова!', reply_markup=create_keyboard(['/debug', '/restart',
                                                                                     '/count_all_tokens_gpt',
                                                                                     '/count_all_tts_symbol']))
        logging.info('Ошибка')
        return

def emotion_for_answer(message):
    user_id = message.from_user.id
    try:
        type_voice_answer = message.text
        logging.info('Тип голоса получен.')
        if type_voice_answer == 'good' or type_voice_answer == 'strict' or type_voice_answer == 'neutral' or type_voice_answer == 'evil':
            logging.info('Проверка на правильность ввода.')
            user_history[user_id]['type_voice_answer'] = type_voice_answer
            logging.info('Эмоция получена')
            bot.send_message(user_id, 'Параметры сохранены.', parse_mode='Markdown')

            status, result = ask_gpt(SYSTEM_CONTENT, user_history[user_id]['result_voice'])
            user_history[user_id]['text_gpt'] = result
            tokens = gpt_tokens_text_limit(message, result)
            if tokens > MAX_GPT_TOKENS_FOR_QUERE:
                bot.send_message(user_id, 'Слишком большой запрос!', reply_markup=create_keyboard(['/restart', '/debug',
                                                                                                   '/count_token_gpt',
                                                                                                   '/count_all_tokens_gpt',
                                                                                                   '/count_tts_symbol',
                                                                                                   '/count_all_tts_symbol']))
            all_tokens = all_gpt_tokens_limit(message)
            if not all_tokens:
                bot.send_message(user_id, 'У вас закончились токены!', reply_markup=create_keyboard(['/restart']))

                return
            status2, result_voice = text_to_speech(result, user_history[user_id]['voice_answer'],
                                                   user_history[user_id]['type_voice_answer'])
            if not status2:
                bot.send_message(user_id, 'Ошибка. Попробуйте снова.',
                                 reply_markup=create_keyboard(['/debug', '/restart',
                                                               '/count_all_tokens_gpt',
                                                               '/count_all_tts_symbol']))
                return
            len_voice = user_history[user_id]['len_result']
            print(len_voice)
            user_history[user_id]['symbols'] = len_voice
            tts_symbol = check_summ_tts_symbol(user_id, TABLE_NAME)
            tts_symbol = tts_symbol[0]
            all_symbols = tts_symbol + len_voice
            if all_symbols > MAX_FOR_USER_TTS_STT_SYMBOL:
                bot.send_message(user_id, f'Вы израсходовали все токены! {all_symbols}/{MAX_FOR_USER_TTS_STT_SYMBOL}',
                                 reply_markup=create_keyboard(
                                     ['/debug', '/restart', '/count_all_tokens_gpt', '/count_tts_symbol']))
                logging.info(f'Пользователь {user_id}  потратил все токены.')
                return
            bot.send_message(user_id, 'Ответ : ', reply_markup=create_keyboard(['/restart', '/debug',
                                                                                '/count_tts_symbol',
                                                                                '/count_all_tts_symbol',
                                                                                '/count_all_tokens_gpt',
                                                                                '/count_token_gpt']))
            bot.send_voice(user_id, result_voice)
            logging.info('Пользователь получил голосовой ответ')
            insert_info([user_id, 'quest_voice', user_history[user_id]['result_voice'], 'user', tokens, len_voice, user_history[user_id]['blocks']], TABLE_NAME)
            logging.info('Данные записаны в таблицу SQL.')
            return
        else:
            logging.info('Ошибка')
            bot.send_message(user_id, 'Неверный ввод.\n\n Введите тип голоса для синтеза речи. :')
            bot.register_next_step_handler(message, emotion_for_answer)
            return
    except Exception as e:
        bot.send_message(user_id, f'Ошибка ввода. {e}\n'
                                  'Попробуйте снова.', reply_markup=create_keyboard(['/debug', '/restart',
                                                                                     '/count_all_tokens_gpt']))
        logging.info('Ошибка.')
        return



@bot.message_handler(commands=['quest_text'])
def text_quere(message: Message):
    user_id = message.from_user.id
    all_tokens = check_summ_tokens(user_id)
    all_tokens = all_tokens[0]
    logging.info('Получены все токены, использаннные пользователем.')
    if all_tokens > MAX_GPT_TOKENS_USER:
        bot.send_message(user_id, 'Вы превысили лимит токенов!\n'
                                  f'{all_tokens}/{MAX_GPT_TOKENS_USER}')
        logging.info(f'Пользователь превысил лимит токенов: {all_tokens}/{MAX_GPT_TOKENS_USER}')
        return
    bot.send_message(user_id, 'Введи свой запрос :')
    logging.info('Бот запросил запрос.')
    bot.register_next_step_handler(message, get_text)

def get_text(message: Message):
    user_id = message.from_user.id
    try:
        text_quere = message.text
        logging.info('Текст получен')
        status, result = ask_gpt(SYSTEM_CONTENT, text_quere)
        user_history[user_id]['user_quere'] = text_quere
        if not status:
            bot.send_message(user_id, 'Ошибка.\n'
                                      'Попробуйте снова', reply_markup=create_keyboard(['/debug', '/restart',
                                                                           '/count_all_tokens_gpt']))
            return
        logging.info('Произведен запрос.')
        tokens_text_gpt = gpt_tokens_text_limit(message, result)
        user_history[user_id]['tokens_text_gpt'] = tokens_text_gpt
        logging.info('Проверка на лимит токенов.')
        if tokens_text_gpt:
            user_history[user_id]['text_gpt'] = result
            bot.send_message(user_id, 'Ответ :')
            time.sleep(1)
            bot.send_message(user_id, result, reply_markup=create_keyboard(['/count_token_gpt', '/debug', '/restart',
                                                                           '/count_all_tokens_gpt']))
            logging.info('Результат доставлен пользователю.')
            insert_info([user_id, 'quest_text', user_history[user_id]['user_quere'], 'user',
                         user_history[user_id]['tokens_text_gpt'], 0, 0], TABLE_NAME)
            logging.info('Данные занесены в таблицу.')
    except Exception as e:
        bot.send_message(user_id, f'Ошибка ввода. {e}\n'
                                  'Попробуйте снова.', reply_markup=create_keyboard(['/debug', '/restart',
                                                                           '/count_all_tokens_gpt']))
        logging.info('Ошибка.')
        return



@bot.message_handler(commands=['tts'])
def text_to_sp(message):
    logging.info('Пользователь выбрал тип запроса - tts.')
    user_id = message.from_user.id
    bot.send_message(user_id, 'Введите текст, я отправлю тебе голосовой ответ.\n'
                              'Ты можешь выбрать голос, тип голоса')
    bot.send_message(user_id, 'Выбери голос для синетза речи :', reply_markup=create_keyboard(['jane', 'ermil']))
    logging.info('Бот запросил голос для синтеза речи(М/Ж).')
    bot.register_next_step_handler(message, get_voice_gpt)
def get_voice_gpt(message):
    user_id = message.from_user.id
    try:
        voice = message.text
        logging.info('Голос получен.')
        user_history[user_id]['voice'] = voice
        if user_history[user_id]['voice'] == 'jane':
            logging.info('Голос (Jain).')
            bot.send_message(user_id, 'Good. Выбери тип голоса для синтеза речи', reply_markup=create_keyboard(['evil',
                                                                                                                'neutral',
                                                                                                                'good']))
            logging.info('Бот запросил тип голоса для синтеза речи.')
            bot.register_next_step_handler(message, get_type_voice)
            return
        elif user_history[user_id]['voice'] == 'ermil':
            logging.info('Голос Ermil.')
            bot.send_message(user_id, 'Good. Выбери тип голоса для синтеза речи',
                             reply_markup=create_keyboard(['good', 'neutral']))
            logging.info('Бот запросил тип голоса для синтеза речи.')
            bot.register_next_step_handler(message, get_type_voice)
            return
        else:
            logging.info('Ошибка выбора голоса..')
            bot.send_message(user_id, 'Вы неверно выбрали голос для синтеза.\n\nВыберите голос для синтеза.',
                             reply_markup=create_keyboard(['jane', 'ermil']))
            bot.register_next_step_handler(message, get_voice_gpt)
            return
    except Exception as e:
        bot.send_message(user_id, f'Ошибка! {e}\n'
                                  'Попробуйте снова!', reply_markup=create_keyboard(['/debug', '/restart',
                                                                                     '/count_all_tokens_gpt',
                                                                                     '/count_all_tts_symbol']))
        logging.info('Ошибка')
        return

def get_type_voice(message):
    user_id = message.from_user.id
    try:
        type_voice = message.text
        logging.info('Тип голоса получен.')
        if type_voice == 'good' or type_voice == 'strict' or type_voice == 'neutral' or type_voice == 'evil':
            logging.info('Проверка на правильность ввода.')
            user_history[user_id]['emotion'] = type_voice
            logging.info('Эмоция получена')
            bot.send_message(user_id, 'Параметры сохранены.\n\n Введите задачу :', parse_mode='Markdown')
            bot.register_next_step_handler(message, get_text_for_speech)
            return
        else:
            logging.info('Ошибка')
            bot.send_message(user_id, 'Неверный ввод.\n\n Введите тип голоса для синтеза речи. :')
            bot.register_next_step_handler(message, get_type_voice)
            return
    except Exception as e:
        bot.send_message(user_id, f'Ошибка ввода. {e}\n'
                                  'Попробуйте снова.', reply_markup=create_keyboard(['/debug', '/restart',
                                                                                     '/count_all_tokens_gpt',
                                                                                     '/count_all_tts_symbol']))
        logging.info('Ошибка.')
        return



def get_text_for_speech(message):
    user_id = message.from_user.id
    try:
        logging.info('Получен текст запроса.')
        text = message.text
        user_history[user_id]['user_content'] = text
        status2, voice_result = text_to_speech(text, user_history[user_id]['voice'], user_history[user_id]['emotion'])
        if not status2:
            bot.send_message(user_id, 'Ошибка.', reply_markup=create_keyboard(['/count_all_tokens_gpt','/restart', '/debug',
                                                                               '/count_all_tts_symbol']))
            logging.info('Ошибка в запросе.')
            return

        logging.info('tts-запрос')
        tokens_voice = int(len(text))
        print(tokens_voice)
        user_history[user_id]['symbols'] = tokens_voice
        tts_symbol = check_summ_tts_symbol(user_id, TABLE_NAME)
        tts_symbol = tts_symbol[0]
        all_symbol = tokens_voice + tts_symbol
        if all_symbol > MAX_FOR_USER_TTS_STT_SYMBOL:
            bot.send_message(user_id, 'Вы израсходовали все токены на жту функкцию', reply_markup=create_keyboard(['/count_all_tokens_gpt'
                                                                                                                        '/restart',
                                                                                                                        '/debug',
                                                                                                                        '/count_tts_symbol',
                                                                                                                        '/count_all_tts_symbol']))
            logging.info('Пользователь израсходовал токены.')
            return

        if tokens_voice > MAX_TTS_STT_TOKENS:
            bot.send_message(user_id, 'Слишком большой запрос.',reply_markup=create_keyboard(['/count_all_tokens_gpt',
                                                                                              '/restart',
                                                                                              '/debug',
                                                                                              '/count_tts_symbol'
                                                                                              '/count_all_tts_symbol']))
            logging.info('Пользователь ввёл слишком большой запрос.')
            return

        bot.send_message(user_id, 'Голосовой ответ :', reply_markup=create_keyboard(['/count_tts_symbol',
                                                                                     '/count_all_tts_symbol',
                                                                                     '/debug',
                                                                                     '/restart']))
        logging.info('Ответ от бота.')
        time.sleep(1)
        bot.send_voice(user_id, voice_result)
        insert_info([user_id, 'tts',  user_history[user_id]['user_content'], 'user', 0, tokens_voice, 0], TABLE_NAME)
        logging.info('Данные занесены в таблицу SQL.')
    except Exception as e:
        bot.send_message(user_id,
                         f'Ошибка ввода. {e}\n'
                         'Попробуйте снова.', reply_markup=create_keyboard(['/debug', '/restart',
                                                                           '/count_all_tokens_gpt', '/count_tts_symbol',
                                                                            '/count_all_tts_symbol']))
        logging.info('Ошибка')
        return

@bot.message_handler(commands=['stt'])
def s_to_text(message: Message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Запиши гс : ')
    logging.info('Бот попросил прислать ему гс.')
    bot.register_next_step_handler(message, get_voice_for_text)

def get_voice_for_text(message: Message):
    user_id = message.from_user.id
    try:
        if not message.voice:
            bot.send_message(user_id, 'Ошибка ввода.', reply_markup=create_keyboard(['/debug',
                                                                                     '/restart',
                                                                                     '/count_tts_symbol',
                                                                                     '/count_all_tts_symbol']))
            logging.info('Ошибка')
            return
        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        logging.info('Файл записан.')
        blocks = block_duraction_limit(message, message.voice.duration)
        if blocks:
            status, result, stt_symbol = speech_to_text(file)
            user_history[user_id]['symbols'] = stt_symbol
            user_history[user_id]['result_stt'] = result
            all_tts_stt_symbol = check_summ_tts_symbol(user_id, TABLE_NAME)
            all_tts_stt_symbol = all_tts_stt_symbol[0]
            all_tts_stt_symbol += stt_symbol
            if all_tts_stt_symbol > MAX_FOR_USER_TTS_STT_SYMBOL:
                bot.send_message(user_id, 'Привышен лимит токенов!', reply_markup=create_keyboard(['/debug',
                                                                                                        '/restart',
                                                                                                        '/count_tts_symbol',
                                                                                                        '/count_all_tts_symbol']))
                logging.info('Превышен лимит токенов.')
                return
            if status:
                bot.send_message(user_id, 'Вот ваш сообщение : ')
                bot.send_message(user_id, result, reply_markup=create_keyboard(['/debug',
                                                                                '/restart',
                                                                                '/count_tts_symbol',
                                                                                '/count_all_tts_symbol']))
                insert_info([user_id, 'stt', 'user', user_history[user_id]['result_stt'],
                              0, user_history[user_id]['symbols'], blocks], TABLE_NAME)
    except Exception as e:
        bot.send_message(user_id, f'Ошибка! {e}', reply_markup=create_keyboard(['/debug',
                                                                                     '/restart',
                                                                                     '/count_tts_symbol',
                                                                                     '/count_all_tts_symbol']))
        return

@bot.message_handler(commands=['debug'])
def debug(message):
    user_id = message.from_user.id
    with open('log_file.txt', encoding='utf-8') as f:
        logging.info('Бот отпрвил файл с логами.')
        bot.send_document(user_id, f)

@bot.message_handler(commands=['restart'])
def restart(message):
    logging.info('Пользователь решил воспользоваться ботом заново.')
    start_message(message)
    return

@bot.message_handler(commands=['count_token_gpt'])
def count_tokens (message: Message):
    logging.info('Пользователь запросил количетво потраченных токенов в данной сессии.')
    user_id = message.from_user.id
    try:
        tokens = count_gpt_tokens(user_history[user_id]['text_gpt'])
        bot.send_message(user_id, f'За эту сессию вы потратили {tokens} токенов', reply_markup=create_keyboard(['/debug',
                                                                                                                '/restart',
                                                                                                                '/count_all_tokens_gpt',
                                                                                                                ]))
        return
    except Exception as e:
        bot.send_message(user_id, f'Ошибка!')
        logging.info('Бот вывел токены.')
        return

@bot.message_handler(commands=['count_all_tokens_gpt'])
def count(message: Message):
    logging.info('Пользователь запросил потраченные токены за всё время использования.')
    user_id = message.from_user.id
    tokens_all = check_summ_tokens(user_id)[0]
    try:
        bot.send_message(user_id, f'За всё время пользования вы использовали {tokens_all} токенов',
                         reply_markup=create_keyboard(['/debug', '/restart', '/count_token_gpt', '/count_all_tts_symbol']))
        logging.info('Бот вывел все токены.')
    except Exception as e:
        bot.send_message(user_id, f'Запроса не было, поэтому я не могу подсчитать токены.{e}')

@bot.message_handler(commands=['count_all_tts_symbol'])
def count(message):
    user_id = message.from_user.id
    try:
        logging.info('Бот считает все потраченные токены (stt/tts)')
        symbols = check_summ_tts_symbol(user_id, TABLE_NAME)
        symbols = symbols[0]
        bot.send_message(user_id, f'За все время вы потратили {symbols}/{MAX_FOR_USER_TTS_STT_SYMBOL} символов.')
    except:
        bot.send_message(user_id, 'Ошибка!', reply_markup=create_keyboard(['/restart']))

@bot.message_handler(commands=['count_tts_symbol'])
def count(message):
    user_id = message.from_user.id
    try:
        logging.info('Бот считает токены stt/tts за прошедшую сессию.')
        symbols = user_history[user_id]['symbols']
        bot.send_message(user_id, f'За эту сессию вы потратили {symbols}/{MAX_FOR_USER_TTS_STT_SYMBOL} символов.')
    except:
        bot.send_message(user_id, 'Ошибка', reply_markup=create_keyboard(['/restart']))


schedule.every(24).hours.do(quest_day)
Thread(target=shedule_runner).start()

bot.polling()
