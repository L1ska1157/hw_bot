from datetime import *
from telebot import TeleBot
from telebot import types
import sqlite3


with open('token.txt') as f:
    token = f.readline().strip()
bot = TeleBot(token=token)

ACTION = ''

subject = ''

SUBJECTS = {
    'mth': {'name': 'Матаналіз',
               'profs': [['Аджубей', 'mth_ad'], ['Вовк', 'mth_v']],
            'weekday': 2},
    'ds': {'name': 'Дискретка',
              'profs': [['Ляшко', 'ds_l'], ['Голубов', 'ds_g']],
           'weekday': 4},
    'ag': {'name': 'Алгебра і геометрія',
           'profs': [['Якимів', 'ag_yak'], ['Давидов', 'ag_d']],
           'weekday': 2},
    'pg': {'name': 'Програмування',
           'profs': [['Самойлов', 'pg_sm'], ['Савчук', 'pg_sv']],
           'weekday': 4},
    'eng': {'name': 'Англійська',
            'profs': [['Красовська', 'eng_k'], ['Степанечко', 'eng_s']],
            'weekday': 3},
    'vstup_kn': {
        'name': 'Вступ до кн',
        'profs': [],
        'weekday': 3
    }
}


def sql_execute(str :str):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    result = c.execute(str)
    conn.commit()
    conn.close()
    return result


def send_prof(chat_id, sub):
    markup = types.InlineKeyboardMarkup()


    for prof in SUBJECTS[sub]['profs']:
        markup.add(types.InlineKeyboardButton(text=prof[0], callback_data=f'{prof[1]}'))

    bot.send_message(chat_id, 'Оберіть викладача: ', reply_markup=markup)


def send_subj(chat_id):
    markup = types.InlineKeyboardMarkup()

    for sub in SUBJECTS.keys():
        markup.add(types.InlineKeyboardButton(text=SUBJECTS[sub]['name'], callback_data=f'{ACTION}_{sub}'))

    bot.send_message(chat_id, 'Оберіть предмет:', reply_markup=markup)


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Хелоу. Для початку треба обрати своїх викладачів')

    #saving user data
    sql_execute(f'''
    INSERT OR IGNORE 
    INTO users 
    VALUES ({message.chat.id}, 0, 0, 0, 0, 0, 'vstup_kn');
    ''')


@bot.message_handler(commands=['choose_prof'])
def choose_prof(message):
    #choosing professor for some subject
    global ACTION
    ACTION = 'sp'
    send_subj(message.chat.id)


@bot.message_handler(commands=['add_hw'])
def add_hw(message):
    global ACTION
    ACTION = 'add'
    send_subj(message.chat.id)


@bot.message_handler(commands=['get_hw'])
def get_hw(message):
    global ACTION
    ACTION = 'get'
    send_subj(message.chat.id)
    # TODO get homework (asking for subject, inform if doesn't exist(or it's older then 1 week))


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    global SUBJECTS
    global ACTION
    global SUBJ
    cb = call.data.split('_')

# * SET PROFESSOR
    if cb[0] in SUBJECTS.keys():
        # if professor was chosen
        bot.edit_message_reply_markup(  # deleting last keyboard
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=types.InlineKeyboardMarkup()
        )
        # saving data
        sql_execute(f"""
            UPDATE users 
            SET {cb[0]} = '{cb[0]}_{cb[1]}' 
            WHERE id={call.message.chat.id};
            """)

        ACTION = ''

# * CHOOSE SUBJECT TO SET PROFESSOR
    if cb[0] == 'sp':
        ACTION = ''
        #if subject was chosen
        bot.edit_message_reply_markup( #deleting last keyboard
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=types.InlineKeyboardMarkup()
        )
        if cb[1] == 'vstup':
            bot.send_message(call.message.chat.id, text = 'Тут у всіх 1 препод...')
        else:
            send_prof(call.message.chat.id, cb[1])

# * ADD HOMEWORK
    if cb[0] == 'add':
        ACTION = ''
        bot.edit_message_reply_markup(  # deleting last keyboard
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=types.InlineKeyboardMarkup()
        )
        con = sqlite3.connect('data.db')
        cur = con.cursor()

        SUBJ = cur.execute(f'''
                SELECT {cb[1]} FROM users WHERE id={call.message.chat.id};''').fetchone()[0]
        hw_date = date.today() - timedelta(days=(date.today().weekday()+7 - SUBJECTS[SUBJ.split('_')[0]]['weekday'])%7)
        id =(
            f'{hw_date.year}'
            f'{hw_date.month}'
            f'{hw_date.day}'
            f'{SUBJ}')
        cur.execute(f'''
        SELECT * FROM homeworks WHERE hw_id = '{id}'
        ''')
        if cur.fetchone() is None:
            ACTION = 'input-hw'
            bot.send_message(chat_id=call.message.chat.id,
                             text = 'Введіть текст домашнього завдання(фото не приймаються, можна посилання)')

        else:
            ACTION = 'change-hw'
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text='Так',
                                                  callback_data=f'{ACTION}_y'))
            markup.add(types.InlineKeyboardButton(text='Ні',
                                                  callback_data=f'{ACTION}_n'))
            bot.send_message(chat_id=call.message.chat.id,
                             text='Таке домашнє вже існує. Ви впевнені, що хочете його переписати?',
                             reply_markup=markup)
        con.close()

# * CHANGE HOMEWORK
    if cb[0] == 'change-hw':
        ACTION = ''
        bot.edit_message_reply_markup(  # deleting last keyboard
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=types.InlineKeyboardMarkup()
        )
        if cb[1] == 'y':
            ACTION = 'input-hw'
            bot.send_message(chat_id=call.message.chat.id,
                             text='Введіть текст домашнього завдання(фото не приймаються, можна посилання)')

# * GET HOMEWORK
    if cb[0] == 'get':
        ACTION = ''
        bot.edit_message_reply_markup(  # deleting last keyboard
            chat_id=call.message.chat.id,
            message_id=call.message.id,
            reply_markup=types.InlineKeyboardMarkup()
        )
        con = sqlite3.connect('data.db')
        cur = con.cursor()

        # get last homework
        SUBJ = cur.execute(f'''
                        SELECT {cb[1]} FROM users WHERE id={call.message.chat.id};''').fetchone()[0]
        hw = cur.execute(f'''
        SELECT * FROM homeworks WHERE subj = '{SUBJ}' ORDER BY date DESC;
        ''').fetchone()

        if hw is None:
            #if no hw added
            bot.send_message(chat_id=call.message.chat.id, text = 'Домашки немає')
        elif  (date.today() - datetime.strptime(hw[3], '%Y-%m-%d').date()).days > 7:
            # if hw older then 1 week
            bot.send_message(chat_id=call.message.chat.id, text='Останнє дз застаріле')
        else:
            #if hw is new enough
            bot.send_message(chat_id=call.message.chat.id, text = f'''
            {hw[-1]}\nДата: {hw[-2]}
            ''')




@bot.message_handler(func=lambda message: True)
def message(message):
    global ACTION

# * SAVE HOMEWORK
    if ACTION == 'input-hw':
        hw_date = date.today() - timedelta(days=(date.today().weekday() - SUBJECTS[SUBJ.split('_')[0]]['weekday']) % 7)
        id = (f'{hw_date.year}'
              f'{hw_date.month}'
              f'{hw_date.day}'
              f'{SUBJ}')
        sql_execute(f'''
        INSERT OR REPLACE INTO homeworks (hw_id, subj, date, text) VALUES ('{id}', '{SUBJ}', '{hw_date}', '{message.text}')
        ''')
        ACTION = ''
        bot.send_message(message.chat.id, text = 'Збережено!')



if __name__ == '__main__':
    bot.infinity_polling()