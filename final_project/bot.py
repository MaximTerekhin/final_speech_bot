import math
import time
import telebot
import logging
from telebot.types import Message, ReplyKeyboardMarkup
from speech import text_to_speech, speech_to_text, count_gpt_tokens, ask_gpt
from data_bases import selection_stt_blocks,  insert_info, check_quantity, create_table, check_summ_tokens
from config import TABLE_NAME, MAX_STT_BLOCKS, MAX_GPT_TOKENS_FOR_QUERE, MAX_USERS_IN_DIALOG, TOKEN_TELEGRAMM, MAX_TTS_STT_TOKENS, MAX_GPT_TOKENS_USER





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
    all_blocks = len(selection_stt_blocks(user_id, TABLE_NAME)) + audio_blocks
    if all_blocks > MAX_STT_BLOCKS:
        bot.send_message(user_id, 'Кажется вы перебрали с токенами.\n'
                                  'Попробуйте покороче изложить свои мысли : ')
        bot.register_next_step_handler(message, get_voice)
        return
    if duraction > 60:
        bot.send_message(user_id, 'Длинное гс!\n'
                                  'Перезапишите!')
        bot.register_next_step_handler(message, get_voice)
        return
    return audio_blocks

def gpt_tokens_text_limit(message, text):
    user_id = message.from_user.id
    tokens = count_gpt_tokens(text)
    if not tokens < MAX_GPT_TOKENS_FOR_QUERE:
        bot.send_message(user_id, 'Слишком большой запрос!\n'
                                  'Попробуйте снова.')
        return
    return tokens

def all_gpt_tokens_limit(message):
    user_id = message.from_user.id
    tokens = check_summ_tokens(user_id)
    if int(len(tokens)) > MAX_GPT_TOKENS_USER:
        bot.send_message(user_id, 'Вы израсходовали все токены.')
        return
    return tokens



def create_keyboard(buttons):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, one_time_keyboard=True)
    keyboard.add(*buttons)
    return keyboard

@bot.message_handler(commands=['start'])
def start_message(message: Message):
    create_table(TABLE_NAME)
    user_id = message.from_user.id
    users_in_dialog = check_quantity()
    tokens = all_gpt_tokens_limit(message)
    if  tokens:

        if len(users_in_dialog) > MAX_USERS_IN_DIALOG:
            bot.send_message(user_id, 'Превышено количество пользователей.\n'
                                      'Мест нет!')
            return
        user_history['user_id'] = user_id
        user_history[user_id] = {}
        session = 1
        user_history[user_id]['session'] = session
        user_one_name = message.from_user.first_name
        user_last_name = message.from_user.last_name
        bot.send_message(user_id, f'Приветсвую вас, {user_one_name} {user_last_name}!\n'
                                  f'Я бот - сценарист, помощник, рассказчик, друг.\n'
                                  )
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


        logging.info('Приветственные сообщения выведены.')


@bot.message_handler(commands=['stt'])
def stt(message: Message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Хорошо.\n'
                              'Запиши мне гс')
    bot.register_next_step_handler(message, get_voice)

def get_voice(message: Message):
    user_id = message.from_user.id
    try:
        if not message.voice:
            bot.send_message(user_id, 'Ваш запрос не аудио!\n'
                                      'Перезапишите!')
            bot.register_next_step_handler(message, get_voice)
        blocks = block_duraction_limit(message, message.voice.duration)
        if blocks:
            file_id = message.voice.file_id
            file_info = bot.get_file(file_id)
            file = bot.download_file(file_info.file_path)
            status, result, len_text = speech_to_text(file)
            if not status:
                bot.send_message(user_id, 'ошибка')
                return
            if len_text > MAX_TTS_STT_TOKENS:
                bot.send_message(user_id, 'Слишком большой ответ от GPT,\n Попробуйте перефразировать ваш запрос.')
                return
            bot.send_message(user_id, result)

            status2, quere_gpt = ask_gpt(result)
            tokens_text_gpt = gpt_tokens_text_limit(message,quere_gpt)
            if not status2:
                bot.send_message(user_id, 'Что-то пошло не так.\n'
                                          'Попробуйте заново')
                return
            if tokens_text_gpt:
                insert_info([user_id, result, 'user', tokens_text_gpt, 0, blocks], TABLE_NAME)
                bot.send_message(user_id, quere_gpt, reply_markup=create_keyboard(['count_token', '/debug', '/restart']))
        else:
            bot.send_message(user_id, 'Ошибка.\n'
                                      'Попробуйте снова.')
            return
    except:
        bot.send_message(user_id, 'Ошибка!\n'
                                  'Попробуйте заново!')
        return


@bot.message_handler(commands=['ttt'])
def text_quere(message: Message):
    user_id = message.from_user.id
    all_tokens = check_summ_tokens(user_id)
    if int(len(all_tokens)) > MAX_GPT_TOKENS_USER:
        bot.send_message(user_id, 'Вы превысили лимит токенов!\n'
                                  f'{all_tokens}/{MAX_GPT_TOKENS_USER}')
        return
    bot.send_message(user_id, 'Введи свой запрос :')
    bot.register_next_step_handler(message, get_text)

def get_text(message: Message):
    user_id = message.from_user.id
    text_quere = message.text


    status, result = ask_gpt(text_quere)
    tokens_text_gpt = gpt_tokens_text_limit(message, result)
    if not status:
        bot.send_message(user_id, 'Ошибка.\n'
                                  'Попробуйте снова')
    if tokens_text_gpt:
        user_history[user_id]['text_gpt'] = result
        bot.send_message(user_id, result, reply_markup=create_keyboard(['/count_token', '/debug', '/restart',
                                                                       '/count_all_tokens']))
        insert_info([user_id, text_quere, 'user', tokens_text_gpt, 0, 0], TABLE_NAME)



@bot.message_handler(commands=['tts'])
def text_to_sp(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Введите текст, я отправлю тебе голосовой ответ.\n'
                              'Ты можешь выбрать голос, тип голоса')
    bot.send_message(user_id, 'Выбери голос для синетза речи :', reply_markup=create_keyboard(['jane', 'ermil']))
    bot.register_next_step_handler(message, get_voice_gpt)
def get_voice_gpt(message):
    user_id = message.from_user.id
    voice = message.text
    try:
        user_history[user_id]['voice'] = voice
        if user_history[user_id]['voice'] == 'jane':
            logging.info('Голос получен.')
            bot.send_message(user_id, 'Good. Выбери тип голоса для синтеза речи', reply_markup=create_keyboard(['evil',
                                                                                                                'neutral',
                                                                                                                'good']))
            bot.register_next_step_handler(message, get_type_voice)
            return
        elif user_history[user_id]['voice'] == 'ermil':
            logging.info('Голос получен.')
            bot.send_message(user_id, 'Good. Выбери тип голоса для синтеза речи',
                             reply_markup=create_keyboard(['good', 'neutral']))
            bot.register_next_step_handler(message, get_type_voice)
            return
        else:
            logging.info('Голос неполучен.')
            bot.send_message(user_id, 'Вы неверно выбрали голос для синтеза.\n\nВыберите голос для синтеза.',
                             reply_markup=create_keyboard(['jane', 'ermil']))
            bot.register_next_step_handler(message, get_voice_gpt)
            return
    except:
        bot.send_message(user_id, 'Ошибка!\n'
                                  'Попробуйте снова!')
        return

def get_type_voice(message):
    user_id = message.from_user.id
    type_voice = message.text
    if type_voice == 'good' or type_voice == 'strict' or type_voice == 'neutral' or type_voice == 'evil':
        user_history[user_id]['emotion'] = type_voice
        logging.info('Эмоция получена')
        bot.send_message(user_id, 'Параметры сохранены.\n\n Введите задачу :', parse_mode='Markdown')
        bot.register_next_step_handler(message, get_text_for_speech)
        return
    else:
        logging.info('Эмоция неполучена')
        bot.send_message(user_id, 'Неверный ввод.\n\n Введите тип голоса для синтеза речи. :')
        bot.register_next_step_handler(message, get_type_voice)
        return



def get_text_for_speech(message):
    user_id = message.from_user.id
    text = message.text
    user_history[user_id]['user_content'] = text
    status, result = ask_gpt(text)
    tokens_gpt_text = gpt_tokens_text_limit(message, result)
    if not status:
        bot.send_message(user_id, 'Ошибка.\n'
                                  'Попробуйте снова!')
        return
    if not tokens_gpt_text:
        bot.send_message(user_id, 'Слишком большой запрос.\n'
                                  'Попробуйте снова.')
    voice_result, tokens_voice = text_to_speech(result, user_history[user_id]['voice'], user_history[user_id]['emotion'])
    bot.send_voice(user_id, voice_result)
    insert_info([user_id, user_history[user_id]['user_content'], 'user', tokens_gpt_text, tokens_voice, 0], TABLE_NAME)

@bot.message_handler(commands=['debug'])
def debug(message):
    user_id = message.from_user.id
    with open('log_file.txt') as f:
        bot.send_document(user_id, f)

@bot.message_handler(commands=['restart'])
def restart(message):
    start_message(message)
    return

@bot.message_handler(commands=['count_token'])
def tokens (message):
    user_id = message.from_user.id
    tokens = count_gpt_tokens(user_history[user_id]['text_gpt'])[0]
    bot.send_message(user_id, f'За эту сессию вы потратили {tokens} токенов', reply_markup=create_keyboard(['/debug', '/restart', '/count_all_tokens']))



@bot.message_handler(commands=['count_all_tokens'])
def count(message: Message):
    user_id = message.from_user.id
    tokens_all = check_summ_tokens(user_id)[0]
    bot.send_message(user_id, f'За всё время пользования вы использовали {tokens_all} токенов',
                     reply_markup=create_keyboard(['/debug', '/restart', '/count_token']))



bot.polling()
