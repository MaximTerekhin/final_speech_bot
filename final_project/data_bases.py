import sqlite3
from config import DATA_BASES_NAME

def execute_quere(sql_quere, data=None, db_path=DATA_BASES_NAME):
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        if data:
            cursor.execute(sql_quere, data)
        else:
            cursor.execute(sql_quere)
        connection.commit()

def execute_selection_quere(sql_quere, data=None, db_path = DATA_BASES_NAME):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    if data:
        cursor.execute(sql_quere, data)
    else:
        cursor.execute(sql_quere)
    rows = cursor.fetchall()
    return rows

def create_table(table_name):
    sql_table = f'''CREATE TABLE IF NOT EXISTS {table_name}(
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    func TEXT,
    content TEXT,
    role TEXT,
    tokens_text_gpt INTEGER,
    tts_stt_symbol INTEGER,
    stt_blocks INTEGER);
'''
    execute_quere(sql_table)

def select_token_gpt_text(user_id, table_name):
    sql_quere = f'''SELECT tokens_text_gpt FROM {table_name} WHERE user_id={user_id} '''
    data = execute_selection_quere(sql_quere)
    if data and data[0]:
        return data[0]
    else:
        return 0

def selection_stt_blocks(user_id, table_name):
    sql_quere = f'''SELECT SUM (stt_blocks) FROM {table_name} WHERE user_id={user_id}'''
    data = execute_selection_quere(sql_quere)
    if data and data[0]:
        return data[0]
    else:
        return 0

def insert_info(values, table_name):
    sql_quere = f'''INSERT INTO {table_name}(user_id, func, content, role, tokens_text_gpt, tts_stt_symbol, 
     stt_blocks) VALUES (?, ?, ?, ?, ?, ?, ?)'''
    execute_quere(sql_quere, values)

def check_quantity(table_name):
    sql_quere = f'''SELECT DISTINCT (user_id) FROM {table_name}'''
    data = execute_selection_quere(sql_quere)
    if data and data[0]:
        return data[0]
    else:
        return 0


def check_summ_tokens(user_id):
    sql_quere = f'''SELECT SUM (tokens_text_gpt) FROM Users_gpt WHERE user_id={user_id}'''
    data = execute_selection_quere(sql_quere)
    if data and data[0]:
        print(data[0])
        return data[0]
    else:
        print(data)
        return 0



def check_summ_tts_symbol(user_id, table_name):
    quere = f'''SELECT SUM (tts_stt_symbol) FROM {table_name} WHERE user_id={user_id}'''
    data = execute_selection_quere(quere)
    if data and data[0]:
        return data[0]
    else:
        return 0

def user_check(table_name):
    sql_quere = f'''SELECT user_id FROM {table_name}'''
    data = execute_selection_quere(sql_quere)
    if data and data[0]:
        return data[0]
    else:
        return 0