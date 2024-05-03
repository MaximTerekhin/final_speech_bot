import math
import time
import telebot
import logging
from telebot.types import Message, ReplyKeyboardMarkup
from speech import text_to_speech, speech_to_text, count_gpt_tokens, ask_gpt
from data_bases import selection_stt_blocks,  insert_info, check_quantity, create_table, check_summ_tokens
from config import (TABLE_NAME, MAX_STT_BLOCKS, MAX_GPT_TOKENS_FOR_QUERE, MAX_USERS_IN_DIALOG, TOKEN_TELEGRAMM,
                    MAX_TTS_STT_TOKENS, MAX_GPT_TOKENS_USER)





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
    all_blocks = len(selection_stt_blocks(user_id, TABLE_NAME)) + audio_blocks
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
    logging.info('Получено значение всех токенов, использованных пользователем.')
    if int(len(tokens)) > MAX_GPT_TOKENS_USER:
        bot.send_message(user_id, 'Вы израсходовали все токены.')
        logging.info('Все токены израсходованы.\n'
                     )
        return
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
    users_in_dialog = check_quantity()
    logging.info('Получено количетсво пользоватлей, пользующихся этой нейросетью в данный момент.')
    tokens = all_gpt_tokens_limit(message)
    if not tokens:
        bot.send_message(user_id, 'У вас закончились токены.')
        logging.info(f'У пользователя {user_one_name} {user_last_name}с id {user_id} закончились токены.')
        return
    if len(users_in_dialog) > MAX_USERS_IN_DIALOG:
        bot.send_message(user_id, 'Превышено количество пользователей.\n'
                                  'Мест нет!')
        logging.info('Слишком много пользователей, использующих эту нейросеть.')
        return
    user_history['user_id'] = user_id
    user_history[user_id] = {}
    session = 1
    user_history[user_id]['session'] = session
    bot.send_message(user_id, f'Приветсвую вас, {user_one_name} {user_last_name}!\n'
                              f'Я бот - сценарист, помощник, рассказчик, друг.\n'
                              )
    logging.info('Приветственное сообщения от бота.')
    time.sleep(2)
    bot.send_message(user_id, 'Вот, что я умею:\n'
                              '1. Переводить аудио в текст;\n'
                              '2. Переводить текст в аудио;\n'
                              '3. Создавать интересные истории;\n'
                              '4. Помогать тебе в учебе...')
    time.sleep(2)
    bot.send_message(user_id, 'Как ты хочешь задать мне вопрос?\n'
                              '1. Можешь записать аудио-сообщение - /stt;\n'
                              '2. Можешь ввести текстом. - /ttt\n'
                              '3. Можешь ввести текстом, а я озвучу тебе твой текст голосом - /tts\n',
     reply_markup=create_keyboard(['/stt', '/tts', '/ttt']))

    time.sleep(1)
    logging.info('Все приветственные сообщения выведены.')


@bot.message_handler(commands=['stt'])
def stt(message: Message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Хорошо.\n'
                              'Запиши мне гс')
    logging.info('Пользователь использует запрос методом stt')
    logging.info('Бот запросил ГС.')
    bot.register_next_step_handler(message, get_voice)

def get_voice(message: Message):
    user_id = message.from_user.id
    try:
        if not message.voice:
            bot.send_message(user_id, 'Ваш запрос не аудио!\n'
                                      'До свидания!', reply_markup=create_keyboard(['/debug', '/restart',
                                                                           '/count_all_tokens']))
            logging.info('Пользователь ошибся с вводом.')
            return
        blocks = block_duraction_limit(message, message.voice.duration)
        if blocks:
            logging.info(f'Количество блоков получено.{blocks} блок(-a;-ов).')
            file_id = message.voice.file_id
            file_info = bot.get_file(file_id)
            file = bot.download_file(file_info.file_path)
            logging.info('Аудио файл успешно сохранен.')
            status, result, len_text = speech_to_text(file)
            logging.info('Запрос пользователя (из речи в текст).')
            if not status:
                bot.send_message(user_id, 'ошибка')
                logging.info('Ошибка!')
                return
            if len_text > MAX_TTS_STT_TOKENS:
                bot.send_message(user_id, 'Слишком большой ответ от GPT,\n Попробуйте перефразировать ваш запрос.')
                logging.info('Пользователь запросил слишком длинный запрос.')
                return
            bot.send_message(user_id, result)
            logging.info('Результат поучен.')

            status2, quere_gpt = ask_gpt(result)
            logging.info('Текстовый запрос к yandex_gpt.')
            if not status2:
                bot.send_message(user_id, 'Что-то пошло не так.\n'
                                          'Попробуйте заново')
                logging.info('Ошибка в запросе')
                return
            tokens_text_gpt = gpt_tokens_text_limit(message, quere_gpt)
            logging.info('Подсчет токенов в запросе.')
            if tokens_text_gpt:
                logging.info('Токены получены.')
                insert_info([user_id, result, 'user', tokens_text_gpt, 0, blocks], TABLE_NAME)
                logging.info('Данные занесены в таблицу.')
                user_history[user_id]['text_gpt'] = quere_gpt
                bot.send_message(user_id, 'Ответ :')
                time.sleep(1)
                bot.send_message(user_id, quere_gpt, reply_markup=create_keyboard(['/count_all_tokens'
                                                                                      , '/debug', '/restart']))
                logging.info('Пользователь получил ответ от нейросети.')
        else:
            bot.send_message(user_id, 'Ошибка.\n'
                                      'Попробуйте снова.')
            logging.info('Ошибка!')
            return
    except Exception as e:
        bot.send_message(user_id, f'Ошибка! {e}\n'
                                  'Попробуйте заново!', reply_markup=create_keyboard(['/count_all_tokens'
                                                                                      , '/debug', '/restart']))
        logging.info('Ошибка запроса.')
        return


@bot.message_handler(commands=['ttt'])
def text_quere(message: Message):
    user_id = message.from_user.id
    all_tokens = check_summ_tokens(user_id)
    logging.info('Получены все токены, использаннные пользователем.')
    if int(len(all_tokens)) > MAX_GPT_TOKENS_USER:
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
        status, result = ask_gpt(text_quere)
        if not status:
            bot.send_message(user_id, 'Ошибка.\n'
                                      'Попробуйте снова', reply_markup=create_keyboard([ '/debug', '/restart',
                                                                           '/count_all_tokens']))
            return
        logging.info('Произведен запрос.')
        tokens_text_gpt = gpt_tokens_text_limit(message, result)
        logging.info('Проверка на лимит токенов.')
        if tokens_text_gpt:
            user_history[user_id]['text_gpt'] = result
            bot.send_message(user_id, 'Ответ :')
            time.sleep(1)
            bot.send_message(user_id, result, reply_markup=create_keyboard(['/count_token', '/debug', '/restart',
                                                                           '/count_all_tokens']))
            logging.info('Результат доставлен пользователю.')
            insert_info([user_id, text_quere, 'user', tokens_text_gpt, 0, 0], TABLE_NAME)
            logging.info('Данные занесены в таблицу.')
    except Exception as e:
        bot.send_message(user_id, f'Ошибка ввода. {e}\n'
                                  'Попробуйте снова.', reply_markup=create_keyboard(['/debug', '/restart',
                                                                           '/count_all_tokens']))
        logging.info('Ошибка.')
        return



@bot.message_handler(commands=['tts'])
def text_to_sp(message):
    logging.info('Пользователь выбрал тип запроса - tts.')
    user_id = message.from_user.id
    bot.send_message(user_id, 'Введите текст, я отправлю тебе голосовой ответ.\n'
                              'Ты можешь выбрать голос, тип голоса')
    bot.send_message(user_id, 'Выбери голос для синетза речи :', reply_markup=create_keyboard(['Jane', 'Ermil']))
    logging.info('Бот запросил голос для синтеза речи(М/Ж).')
    bot.register_next_step_handler(message, get_voice_gpt)
def get_voice_gpt(message):
    user_id = message.from_user.id
    try:
        voice = message.text
        logging.info('Голос получен.')
        user_history[user_id]['voice'] = voice
        if user_history[user_id]['voice'] == 'Jane':
            logging.info('Голос (Jain).')
            bot.send_message(user_id, 'Good. Выбери тип голоса для синтеза речи', reply_markup=create_keyboard(['evil',
                                                                                                                'neutral',
                                                                                                                'good']))
            logging.info('Бот запросил тип голоса для синтеза речи.')
            bot.register_next_step_handler(message, get_type_voice)
            return
        elif user_history[user_id]['voice'] == 'Ermil':
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
    except:
        bot.send_message(user_id, 'Ошибка!\n'
                                  'Попробуйте снова!', reply_markup=create_keyboard(['/debug', '/restart',
                                                                           '/count_all_tokens']))
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
    except:
        bot.send_message(user_id, 'Ошибка ввода.\n'
                                  'Попробуйте снова.', reply_markup=create_keyboard(['/debug', '/restart',
                                                                           '/count_all_tokens']))
        logging.info('Ошибка.')
        return



def get_text_for_speech(message):
    user_id = message.from_user.id
    try:
        logging.info('Получен текст запроса.')
        text = message.text
        user_history[user_id]['user_content'] = text
        status, result = ask_gpt(text)
        if not status:
            bot.send_message(user_id, 'Ошибка.\n'
                                      'Попробуйте снова!')
            return
        logging.info('Произведен запрос.')
        tokens_gpt_text = gpt_tokens_text_limit(message, result)
        logging.info('Подсчитаны токены в запросе.')
        if not tokens_gpt_text:
            bot.send_message(user_id, 'Слишком большой запрос.\n'
                                      'Попробуйте снова.')
            logging.info('Слишком большой запрос.')
            return
        bot.send_message(user_id, result)
        user_history[user_id]['text_gpt'] = result
        voice_result = text_to_speech(result, user_history[user_id]['voice'], user_history[user_id]['emotion'])
        logging.info('tts-запрос')
        tokens_voice = int(len(result))
        logging.info('Подсчёт токенов в запросе')
        bot.send_message(user_id, 'Ответ :', reply_markup=create_keyboard(['/count_token', '/count_all_tokens', '/debug',
                                                                           '/restart']))
        logging.info('Ответ от бота.')
        time.sleep(1)
        bot.send_voice(user_id, voice_result)
        insert_info([user_id, user_history[user_id]['user_content'], 'user', tokens_gpt_text, tokens_voice, 0], TABLE_NAME)
        logging.info('Данные занесены в таблицу SQL.')
    except:
        bot.send_message(user_id,
                         'Ошибка ввода.\n'
                         'Попробуйте снова.', reply_markup=create_keyboard(['/debug', '/restart',
                                                                           '/count_all_tokens']))
        logging.info('Ошибка')
        return

@bot.message_handler(commands=['debug'])
def debug(message):
    user_id = message.from_user.id
    with open('log_file.txt', encoding='utf-8') as f:
        bot.send_document(user_id, f)

@bot.message_handler(commands=['restart'])
def restart(message):
    logging.info('Пользователь решил воспользоваться ботом заново.')
    start_message(message)
    return

@bot.message_handler(commands=['count_token'])
def count_tokens (message: Message):
    logging.info('Пользователь запросил количетво потраченных токенов в данной сессии.')
    user_id = message.from_user.id
    tokens = count_gpt_tokens(user_history[user_id]['text_gpt'])
    bot.send_message(user_id, f'За эту сессию вы потратили {tokens} токенов', reply_markup=create_keyboard(['/debug',
                                                                                                            '/restart',
                                                                                                            '/count_all_tokens']))
    logging.info('Бот вывел токены.')
    return

@bot.message_handler(commands=['count_all_tokens'])
def count(message: Message):
    logging.info('Пользователь запросил потраченные токены за всё время использования.')
    user_id = message.from_user.id
    tokens_all = check_summ_tokens(user_id)[0]
    bot.send_message(user_id, f'За всё время пользования вы использовали {tokens_all} токенов',
                     reply_markup=create_keyboard(['/debug', '/restart', '/count_token']))
    logging.info('Бот вывел все токены.')

bot.polling()
