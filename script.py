import sqlite3



# Функция для создания соединения с базой данных
def connect_db():
    conn = sqlite3.connect("leaderboard.db")
    return conn


# Функция для инициализации таблицы в базе данных
def initialize_db():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leaderboard (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            points INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            games_won INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

initialize_db()
