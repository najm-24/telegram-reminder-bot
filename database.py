import sqlite3
import datetime

def get_connection():
    conn = sqlite3.connect('bot_database.db')
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # جدول المستخدمين
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    # جدول الحسابات المربوطة
    cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                        user_id INTEGER, 
                        session_name TEXT, 
                        phone TEXT,
                        PRIMARY KEY (user_id, session_name))''')
    # جدول المهام المجدولة
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        ad_text TEXT,
                        media_path TEXT,
                        days INTEGER,
                        min_interval INTEGER,
                        max_interval INTEGER,
                        start_time TEXT,
                        end_time TEXT,
                        last_run TEXT,
                        is_active INTEGER DEFAULT 1)''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def add_account(user_id, session_name, phone):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO accounts (user_id, session_name, phone) VALUES (?, ?, ?)', 
                   (user_id, session_name, phone))
    conn.commit()
    conn.close()

def get_user_accounts(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT session_name FROM accounts WHERE user_id = ?', (user_id,))
    accounts = [row[0] for row in cursor.fetchall()]
    conn.close()
    return accounts

def delete_account(user_id, session_name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM accounts WHERE user_id = ? AND session_name = ?', (user_id, session_name))
    conn.commit()
    conn.close()

def add_scheduled_task(user_id, ad_text, media, days, min_int, max_int):
    conn = get_connection()
    cursor = conn.cursor()
    start_time = datetime.datetime.now().isoformat()
    end_time = (datetime.datetime.now() + datetime.timedelta(days=days)).isoformat()
    cursor.execute('''INSERT INTO tasks (user_id, ad_text, media_path, days, min_interval, max_interval, start_time, end_time) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                   (user_id, ad_text, media, days, min_int, max_int, start_time, end_time))
    conn.commit()
    conn.close()

def get_active_tasks():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks WHERE is_active = 1')
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_last_run(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET last_run = ? WHERE id = ?', (datetime.datetime.now().isoformat(), task_id))
    conn.commit()
    conn.close()

def deactivate_task(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET is_active = 0 WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()

def deactivate_all_user_tasks(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET is_active = 0 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
