import logging
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from stukt import Game, Mafia, DonMafia, Commissioner, Doctor, Villager, Lover, Kamikaze, Hobo, Judge, Maniac
import random
import sqlite3
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os

# Функция для создания соединения с базой данных
def connect_db():
    conn = sqlite3.connect("leaderboard.db")
    return conn

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Создаем экземпляры бота и маршрутизатора
load_dotenv()
API_TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()
port = os.getenv('PORT', 10000)

# Хранилище активных игр
active_games = {}
user_data = {}

# Функция для проверки информации о пользователе
def get_user_info(telegram_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leaderboard WHERE telegram_id = ?", (telegram_id,))
    user = cursor.fetchone()
    conn.close()

    if user:
        if user[1] != "":
            return f"Пользователь: *{user[2]} (@{user[1]})*\nЧисло очков: *{user[3]}*\nСыграно игр: *{user[4]}*\nВыиграно игр: *{user[5]}*"
        else: return f"Пользователь: [{user[2]}](tg://user?id={telegram_id})\nЧисло очков: *{user[3]}*\nСыграно игр: *{user[4]}*\nВыиграно игр: *{user[5]}*"
    else:
        print(f"Пользователь с ID {telegram_id} не найден.")
        return None

# Функция для добавления игроков в таблицу
def add_pdb(message):
    conn = connect_db()
    cursor = conn.cursor()
    # Если username отсутствует, заменить на уникальный идентификатор
    username = message.from_user.username or ""
    cursor.execute("SELECT * FROM leaderboard WHERE telegram_id = ?", (message.from_user.id,))
    user = cursor.fetchone()

    if not user:
        # Если пользователя нет в базе, добавляем его
        cursor.execute('''
                    INSERT INTO leaderboard (telegram_id, username, full_name)
                    VALUES (?, ?, ?)
                ''', (message.from_user.id, username, message.from_user.full_name))
        print(f"Пользователь {message.from_user.full_name} добавлен в базу.")
    else:
        print(f"Пользователь {message.from_user.full_name} уже существует в базе.")

    conn.commit()
    conn.close()

# Функция для вывода топ-15 лидеров
def get_top_leaders():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT username, full_name, points
        FROM leaderboard
        ORDER BY points DESC
        LIMIT 15
    ''')
    leaders = cursor.fetchall()
    conn.close()
    leaderboard_text = "🏅 *Топ-15 лидеров:* 🏅\n\n"
    leaderboard_text += "` # | Игрок       |   Очки`\n"
    leaderboard_text += "`-------------------------`\n"

    for idx, (username, full_name, points) in enumerate(leaders, start=1):
        if username != "":
            leaderboard_text += f"`{idx:2} | @{username[:10]:<10} | {points:6}`\n"
        else:
            leaderboard_text += f"`{idx:2} | {full_name[:11]:<11} | {points:6}`\n"

    return leaderboard_text

# Команда start
@router.message(Command(commands=['start']))
async def start_f(message: Message):
    add_pdb(message)

# Команда help
@router.message(Command(commands=['help']))
async def help_f(message: Message):
    chat_id = message.chat.id
    txt = ("📖 Правила игры и команды бота\n\n"+
    "🔹 Как начать игру?\n"+
    "Создайте игру: /newgame.\n"+
    "Присоединяйтесь: /join.\n"+
    "Запустите игру: /startgame.\n\n"+
    "🔹 Фазы игры:\n"+
    "Ночь: Игроки с активными ролями выполняют действия через приватные сообщения бота.\n"+
    "День: Все обсуждают события произошедшие ночью и голосуют за исключение подозреваемого.\n\n"+
    "🔹 Основные роли:\n"+
    "Мафия: Убивает ночью.\n"+
    "Дон мафии: Принимает финальное решение при разногласии мафии.\n"+
    "Комиссар: Проверяет роли игроков.\n"+
    "Доктор: Лечит игроков.\n"+
    "Мирный житель: Голосует днём и ищет мафию.\n"+
    "Дополнительные роли (для больших игр): Любовница, Камикадзе, Маньяк, Судья, Бомж.\n\n"+
    "🔹 Команды:\n"+
    "/newgame - Создать новую игру.\n"+
    "/endgame - Закончить игру.\n" +
    "/join - Присоединиться к текущей игре.\n"+
    "/leave - Покинуть игру до её начала.\n"+
    "/help - Получить список доступных команд и информацию о боте.\n"+
    "/startgame - Начать игру.\n"+
    "/leaderboard - Посмотреть таблицу лидеров.\n"+
    "/mystats - Узнать свои личные достижения\n\n"+
    "🔹 Как начисляются баллы?\n"+
    "Победа вашей стороны.\n"+
    "Активное участие в дневных обсуждениях.\n"+
    "Успешное выполнение действий роли.\n\n"+
    "🔹 Цель игры:\n"+
    "Мирные побеждают, если уничтожат всех мафий.\n"+
    "Мафия побеждает, если других игроков останется столько же сколько их или меньше.\n"+
    "Маньяк побеждает, если останется единственным выжившим.\n\n"+
    "Играй честно, будь активным, и удачи в игре! 🎭")

    if message.chat.is_forum:
        await bot.send_message(chat_id=chat_id, message_thread_id=message.message_thread_id,
                               text=txt,
                               parse_mode="Markdown")
        return
    if not message.chat.is_forum:
        await bot.send_message(chat_id,
                               txt,
                               parse_mode="Markdown")
        return

# Функция для проверки информации о пользователе
@router.message(Command(commands=['mystats']))
async def stats_f(message: Message):
    chat_id = message.chat.id
    if message.chat.is_forum:
        await bot.send_message(chat_id=chat_id, message_thread_id=message.message_thread_id,
                               text=f"Информация о игроке *{message.from_user.first_name}*:\n\n{get_user_info(message.from_user.id)}", parse_mode="Markdown")
        return
    if not message.chat.is_forum:
        await bot.send_message(chat_id, f"Информация о игроке *{message.from_user.first_name}*:\n\n{get_user_info(message.from_user.id)}", parse_mode="Markdown")
        return



# Функция для вывода топ-15 лидеров
@router.message(Command(commands=['leaderboard']))
async def board_f(message: Message):
    chat_id = message.chat.id
    if message.chat.is_forum:
        await bot.send_message(chat_id=chat_id, message_thread_id=message.message_thread_id,
                               text=f"{get_top_leaders()}", parse_mode="Markdown")
        return
    if not message.chat.is_forum:
        await bot.send_message(chat_id=chat_id,
                               text=f"{get_top_leaders()}", parse_mode="Markdown")
        return

# Команда для создания новой игры
@router.message(Command(commands=['newgame']))
async def create_game(message: Message):
    chat_id = message.chat.id
    if chat_id == message.from_user.id:
        return

    if chat_id in active_games:
        await message.answer("Игра уже создана. Вы можете присоединиться или дождаться её завершения.")
        return
    if message.chat.is_forum:
        # Получение ID топика (если это группа с несколькими темами)
        topic_id = message.message_thread_id
        game = Game()
        active_games[chat_id] = game
        game.creator_id = message.from_user.id
        game.topic_id = topic_id
        # Сохраняем ID чата для использования в дальнейшем
        game.chat_id = chat_id  # Сохраняем ID чата в объекте игры
    else:
        game = Game()
        active_games[chat_id] = game
        game.creator_id = message.from_user.id
        # Сохраняем ID чата для использования в дальнейшем
        game.chat_id = chat_id  # Сохраняем ID чата в объекте игры

    await message.answer("Игра создана! Используйте /join, чтобы присоединиться. Минимум 4 игрока.\nДля игры каждый игрок должен запустить @ImpostIgor_wehbot")

# Команда для удаления игры
@router.message(Command(commands=['endgame']))
async def end_game(message: Message):
    chat_id = message.chat.id
    if chat_id == message.from_user.id:
        return

    if chat_id not in active_games:
        await message.answer("Нет активной игры. Создайте игру с помощью команды /newgame.")
        return
    game = active_games[chat_id]
    active_games[chat_id].end_game()
    del game
    del active_games[chat_id]  # Завершаем игру и удаляем из активных

    await message.answer("Игра Закончена!")

# Команда для присоединения к игре
@router.message(Command(commands=['join']))
async def join_game(message: Message):
    chat_id = message.chat.id
    add_pdb(message)
    if message.from_user.id  in user_data:
        del user_data[message.from_user.id]

    user_data[message.from_user.id] = {"timestamps": [], "last_message": ""}
    if chat_id == message.from_user.id:
        return

    if chat_id not in active_games:
        await message.answer("Нет активной игры. Создайте игру с помощью команды /newgame.")
        return

    game = active_games[chat_id]

    if game.state != "waiting":
        await message.answer("Игра уже начата")
        return

    if message.from_user.id in [player["player_id"] for player in game.players]:
        await message.answer("Вы уже присоединились к игре.")
        return

    if len(game.players) >= 15:
        await message.answer("Достигнуто максимальное количество игроков.")
        return

    game.add_player(player_id=message.from_user.id, player_name=message.from_user.first_name, role=None)
    await message.answer(f"Игрок {message.from_user.first_name} присоединился к игре. Всего игроков: {len(game.players)}")

# Команда для выхода из игры
@router.message(Command(commands=['leave']))
async def join_game(message: Message):
    chat_id = message.chat.id

    if chat_id == message.from_user.id:
        return

    if chat_id not in active_games:
        await message.answer("Нет активной игры. Создайте игру с помощью команды /newgame.")
        return

    game = active_games[chat_id]

    if game.state != "waiting":
        await message.answer("Игра уже начата")
        return

    if message.from_user.id not in [player["player_id"] for player in game.players]:
        await message.answer("Вы не в игре.")
        return


    game.del_player(player_id=message.from_user.id)
    await message.answer(f"Игрок {message.from_user.first_name} вышел из игры. Всего игроков: {len(game.players)}")

# Команда для начала игры
@router.message(Command(commands=['startgame']))
async def start_game(message: Message):
    chat_id = message.chat.id

    if chat_id == message.from_user.id:
        return

    if chat_id not in active_games:
        await message.answer("Нет активной игры. Создайте игру с помощью команды /newgame.")
        return

    game = active_games[chat_id]

    if game.state != "waiting":
        await message.answer("Игра уже начата")
        return

    if message.from_user.id != game.creator_id:
        await message.answer("Только создатель игры может запустить её.")
        return

    if len(game.players) < 4:
        await message.answer("Недостаточно игроков для начала игры. Минимум 4.")
        return

    try:
        game.start_game()
        player_roles = distribute_roles(game.players)
        #game.player_roles = player_roles

        for player_id, role in player_roles.items():
            await bot.send_message(player_id, f"Ваша роль: {role.role_name}. {role.role_desk}")
            if 1 < sum(1 for p in game.players if isinstance(p["role"], (Mafia, DonMafia))) and player_id in [p['player_id'] for p in game.players if isinstance(p["role"], (Mafia, DonMafia))]:
                mtxt = "Ваши напарники:\n"
                for p in game.players:
                    if isinstance(p["role"], (Mafia, DonMafia)) and p["player_id"] != player_id:
                        mtxt += f"{p['player_name']} {p['role'].role_name}\n"
                await bot.send_message(player_id, mtxt)

        await message.answer("Роли распределены, игра начинается! Ночная фаза началась.")
        await start_night_phase(chat_id)
        #await end_night_phase(chat_id)
    except Exception as e:
        await message.answer(f"Ошибка при запуске игры: {e}")

@router.message()
async def restrict_non_players(message: Message):
    chat_id = message.chat.id
    current_time = datetime.now()

    if chat_id == message.from_user.id:
        game = next((g for g in active_games.values() if chat_id in [p['player_id'] for p in g.players]), None)
        if game and game.state == "night":
            for p in game.players:
                if p["player_id"] == chat_id and isinstance(p["role"], (Mafia, DonMafia)):
                    mes = message.text
                    writer = message.from_user.first_name
                    for po in game.players:
                        if isinstance(po["role"], (Mafia, DonMafia)) and po["player_id"] != chat_id:
                            await bot.send_message(po["player_id"], f"{writer}: {mes}")
            return

        return
    user_id = message.from_user.id
    if user_id not in user_data:
        user_data[user_id] = {"timestamps": [], "last_message": ""}

    if chat_id in active_games :
        if active_games[chat_id].state == "night":
            for player in active_games[chat_id].players:
                if user_id != player["player_id"] or user_id == active_games[chat_id].lblock_player:
                    if message.chat.is_forum and message.message_thread_id == active_games[chat_id].topic_id:
                        await message.delete()  # Удаляем сообщение
                        return
                    if not message.chat.is_forum:
                        await message.delete()  # Удаляем сообщение
                        return
        elif active_games[chat_id].state !=  "waiting":
            game = next((g for g in active_games.values() if user_id in [p['player_id'] for p in g.players]), None)
            if user_id == game.lblock_player or user_id not in [p["player_id"] for p in game.players]:
                await message.delete()  # Удаляем сообщение
                return

            user = user_data[user_id]
            timestamps = user["timestamps"]
            last_message = user["last_message"]
            # Удаляем старые записи (старше 10 секунд)
            timestamps = [ts for ts in timestamps if current_time - ts <= timedelta(seconds=10)]
            # Проверка флуда: не более 4 сообщений за 10 секунд
            if len(timestamps) >= 4:
                return

            # Проверка спама: сообщение не должно повторяться подряд
            if message.text == last_message:
                return

            # Обновляем данные
            timestamps.append(current_time)
            user["timestamps"] = timestamps
            user["last_message"] = message.text

            # Начисление баллов
            game.update_user_stats(user_id, 1)
            user_data[user_id] = user




# Ночная фаза
async def start_night_phase(chat_id):
    game = active_games[chat_id]
    game.state = "night"
    await bot.send_message(chat_id=game.chat_id, message_thread_id=game.topic_id, text="Ночная фаза: роли начинают свои действия.")
    await notify_roles(game.chat_id, game)

async def notify_roles(chat_id, game):
    for player in game.players:
        role = player["role"]
        buttons = None  # Для каждого игрока определяем свои кнопки
        if not isinstance(role, (Villager, Kamikaze)):
            if isinstance(role, Mafia):
                buttons = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text=f"Убить {target['player_name']}",
                            callback_data=f"action:kill:{target['player_id']}"
                        )] for target in game.players if target["player_id"] != player["player_id"]
                    ]
                )
                await bot.send_message(player["player_id"], "Выберите кого убить этой ночью:", reply_markup=buttons)
            elif isinstance(role, DonMafia):
                buttons = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text=f"Решить судьбу {target['player_name']}",
                            callback_data=f"action:final_kill:{target['player_id']}"
                        )] for target in game.players if target["player_id"] != player["player_id"]
                    ]
                )
                await bot.send_message(player["player_id"], "Выберите кого убить этой ночью:", reply_markup=buttons)
            elif isinstance(role, Doctor):
                if role.self_heal:
                    buttons = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(
                                text=f"Лечить {target['player_name']}",
                                callback_data=f"action:heal:{target['player_id']}"
                            )] for target in game.players
                        ]
                    )
                else:
                    buttons = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(
                                text=f"Лечить {target['player_name']}",
                                callback_data=f"action:heal:{target['player_id']}"
                            )] for target in game.players if target["player_id"] != player["player_id"]
                        ]
                    )
                await bot.send_message(player["player_id"], "Выберите кого лечить этой ночью:", reply_markup=buttons)
            elif isinstance(role, Commissioner):
                buttons = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text=f"Проверить {target['player_name']}",
                            callback_data=f"action:investigate:{target['player_id']}"
                        )] for target in game.players if target["player_id"] != player["player_id"]
                    ]
                )
                await bot.send_message(player["player_id"], "Выберите кого проверить этой ночью:", reply_markup=buttons)
            elif isinstance(role, Lover):
                buttons = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text=f"Блокировать {target['player_name']}",
                            callback_data=f"action:block:{target['player_id']}"
                        )] for target in game.players if target["player_id"] != player["player_id"]
                    ]
                )
                await bot.send_message(player["player_id"], "Выберите с кем Вы будете этой ночью:", reply_markup=buttons)
            elif isinstance(role, Maniac):
                buttons = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text=f"Зарезать {target['player_name']}",
                            callback_data=f"action:m_kill:{target['player_id']}"
                        )] for target in game.players if target["player_id"] != player["player_id"]
                    ]
                )
                await bot.send_message(player["player_id"], "Выберите кого порешать этой ночью:", reply_markup=buttons)
            elif isinstance(role, Judge):
                if role.vote_canceled:
                    buttons = InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(
                                text=f"Оправдать {target['player_name']}",
                                callback_data=f"action:cancel_vote:{target['player_id']}"
                            )] for target in game.players
                        ] + [[InlineKeyboardButton(text="Пропустить", callback_data="action:skip")]]
                    )
                await bot.send_message(player["player_id"], "Выберите кому дать иммунитет от дневного голосования:", reply_markup=buttons)
            elif isinstance(role, Hobo):
                buttons = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text=f"Пойти к {target['player_name']}",
                            callback_data=f"action:start_tracking:{target['player_id']}"
                        )] for target in game.players if target["player_id"] != player["player_id"]
                    ]
                )
                await bot.send_message(player["player_id"], "Выберите у кого поспать под дверью:", reply_markup=buttons)

@router.callback_query(lambda c: c.data.startswith("action:"))
async def handle_action(callback: CallbackQuery):
    player_id = callback.from_user.id
    action = callback.data.split(":")[1]

    # Проверяем, в какой игре находится игрок
    game = next((g for g in active_games.values() if player_id in [p['player_id'] for p in g.players]), None)
    if not game:
        await callback.answer("Вы не участвуете в текущей игре.", show_alert=True)
        return

    # Проверка, не совершал ли игрок уже действие
    if player_id in [a['player_id'] for a in game.night_actions]:
        await callback.answer("Вы уже выбрали действие!", show_alert=True)
        return

    # Логика обработки действий
    if action == "skip":
        game.night_actions.append({"action": action, "player_id": player_id})
        await callback.message.edit_text(text=f"Вы не дали никому иммунитет", reply_markup=None)
        return

    target_id = int(callback.data.split(":")[-1])

    game.night_actions.append({"action": action, "player_id": player_id, "target_id": target_id})
    await callback.answer("Ваше действие принято.")
    t = next(p for p in game.players if p["player_id"] == target_id)
    await callback.message.edit_text(text = f"Ваш выбор {t['player_name']}",reply_markup=None)

    players_with_actions = [p for p in game.players if not isinstance(p["role"], (Villager, Kamikaze))]
    # Отладочная информация для проверки логики
    if any(isinstance(player['role'], Judge) for player in game.players):
        Ju = next(p for p in game.players if isinstance(p["role"], Judge))
        if not Ju["role"].vote_canceled:
            players_with_actions = [p for p in game.players if not isinstance(p["role"], (Villager, Kamikaze, Judge))]


    actions_done = len([p for p in players_with_actions if p['player_id'] in [a['player_id'] for a in game.night_actions]])

    print(f"Players with actions: {players_with_actions}")
    print(f"Night actions: {game.night_actions}")
    print(f"Actions done: {actions_done}")
    print(f"Total players with actions: {len(players_with_actions)}")

    # Проверяем, все ли игроки выполнили действия
    if actions_done == len(players_with_actions):
        await end_night_phase(game.chat_id)
    else:
        print("Not all players have completed their actions yet.")


async def end_night_phase(chat_id):
    game = active_games[chat_id]
    results = game.process_night_actions()
    blocked_players = {action["target_id"] for action in game.night_actions if action["action"] == "block"}
    start_day_text = ""
    for result in results:
        if result["action"] == "kill":
            game.del_player(result["target_id"])
            start_day_text += result["text"] + "\n"

        if result["action"] == "m_kill":
            game.del_player(result["target_id"])
            start_day_text += result["text"] + "\n"

        if result["action"] == "explode":
            game.del_player(result["target_id"])
            start_day_text += result["text"] + "\n"

        if result["action"] == "investigate":
            await bot.send_message(chat_id=result["player_id"], text=result["text"])

        if result["action"] == "start_tracking":
            await bot.send_message(chat_id=result["player_id"], text=result["text"])

    if not any(isinstance(player['role'], DonMafia) for player in game.players) and any(isinstance(player['role'], Mafia) for player in game.players):
        ma = [po for po in game.players if isinstance(po["role"], Mafia)]
        m = random.choice(ma)
        game.change_role(m['player_id'], DonMafia)
        await bot.send_message(chat_id=m['player_id'], text=f"Ваш Дон погиб, вы занимаете его место. {m['role'].role_desk}")

    if start_day_text != "":
        await bot.send_message(chat_id=game.chat_id, message_thread_id=game.topic_id, text=start_day_text)
    else:
        await bot.send_message(chat_id=game.chat_id, message_thread_id=game.topic_id, text="Этой ночью всё спокойно")

    if await declare_winner(game):
        return

    game.night_actions = []
    game.state = "day"

    await bot.send_message(chat_id=game.chat_id, message_thread_id=game.topic_id, text="Наступает день. Обсудите и голосуйте.")
    await asyncio.sleep(60)
    await bot.send_message(chat_id=game.chat_id, message_thread_id=game.topic_id,
                           text="Обсуждение закончилось. Выдвигайте кандидатов на голосование в личных сообщениях.")
    game.nominations = {}

    for player in game.players:
        if player["player_id"] != game.lblock_player:
            buttons = InlineKeyboardMarkup(
                inline_keyboard=[
                                    [InlineKeyboardButton(text=p["player_name"],
                                                          callback_data=f"nominate:{p['player_id']}")]
                                    for p in game.players if p["player_id"] != player["player_id"] and p["player_id"] != game.vote_canceled
                                ] + [[InlineKeyboardButton(text="Пропустить", callback_data="nominate:skip")]]
            )
            await bot.send_message(
                player["player_id"],
                "Выберите игрока для номинации или воздержитесь.",
                reply_markup=buttons
            )


# Обработка номинаций
@router.callback_query(lambda c: c.data.startswith("nominate:"))
async def handle_nomination(callback: CallbackQuery):
    nominee_data = callback.data.split(":")[-1]
    player_id = callback.from_user.id

    chat_id = next((g.chat_id for g in active_games.values() if player_id in [p["player_id"] for p in g.players]), None)
    if not chat_id:
        await callback.answer("Вы не в игре.", show_alert=True)
        return

    game = active_games[chat_id]

    if game.state != "day" or game.nominations.get(player_id):
        await callback.answer("Сейчас нельзя голосовать", show_alert=True)
        return

    if player_id == game.lblock_player:
        await callback.answer("Вы заблокированы любовницей и не можете голосовать.", show_alert=True)
        return

    if nominee_data == "skip":
        game.nominations[player_id] = None
        await callback.message.edit_text("Вы воздержались от номинации.", reply_markup=None)
    else:
        nominee_id = int(nominee_data)
        if nominee_id not in [p["player_id"] for p in game.players]:
            await callback.answer("Некорректный выбор.", show_alert=True)
            return
        nominee_name = next(p["player_name"] for p in game.players if p["player_id"] == nominee_id)
        game.nominations[player_id] = nominee_id
        await callback.message.edit_text(f"Вы выбрали игрока {nominee_name}.", reply_markup=None)
    print(f"Total game.nominations: {len(game.nominations)}")
    print(f"Total players with actions: {len(game.players) - 1 if game.lblock_player else len(game.players)}")
    if len(game.nominations) == (len(game.players) - 1 if game.lblock_player else len(game.players)):
        await process_nominations(chat_id)
    else:
        print("Not all players have completed their actions yet.")

# Обработка результатов номинации
async def process_nominations(chat_id):
    game = active_games[chat_id]

    vote_counts = {}
    for nominee in game.nominations.values():
        if nominee:
            vote_counts[nominee] = vote_counts.get(nominee, 0) + 1

    if not vote_counts:
        await bot.send_message(chat_id=game.chat_id, message_thread_id=game.topic_id, text="Никто не был номинирован. День заканчивается.")
        await start_night_phase(chat_id)
        return

    max_votes = max(vote_counts.values())
    top_nominees = [player_id for player_id, count in vote_counts.items() if count == max_votes]

    if len(top_nominees) > 1:
        await bot.send_message(
            chat_id=game.chat_id,
            message_thread_id=game.topic_id,
            text="Несколько игроков номинированы с равным количеством голосов. Никто не будет линчеван. День заканчивается."
        )
        await start_night_phase(chat_id)
    else:
        await start_final_vote(chat_id, top_nominees[0])

# Финальное голосование
async def start_final_vote(chat_id, nominee_id):
    game = active_games[chat_id]
    game.nominations = {}

    nominee_name = next(p["player_name"] for p in game.players if p["player_id"] == nominee_id)

    buttons = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data=f"final_vote:yes:{nominee_id}"),
             InlineKeyboardButton(text="Нет", callback_data=f"final_vote:no:{nominee_id}")]
        ]
    )
    await bot.send_message(
        chat_id=game.chat_id,
        message_thread_id=game.topic_id,
        text=f"Голосуйте за казнь игрока {nominee_name}. Да или Нет?",
        reply_markup=buttons
    )

# Обработка голосования
@router.callback_query(lambda c: c.data.startswith("final_vote:"))
async def handle_final_vote(callback: CallbackQuery):
    player_id = callback.from_user.id
    data = callback.data.split(":")
    decision = data[1]
    nominee_id = int(data[2])

    game = next((g for g in active_games.values() if player_id in [p["player_id"] for p in g.players]), None)

    if not game or game.state != "day":
        await callback.answer("Сейчас нельзя голосовать.", show_alert=True)
        return

    if player_id in game.nominations:
        await callback.answer("Вы уже проголосовали.", show_alert=True)
        return

    if player_id == game.lblock_player:
        await callback.answer("Вы заблокированы и не можете голосовать.", show_alert=True)
        return

    if player_id == nominee_id:
        await callback.answer("Вы не можете голосовать за себя", show_alert=True)
        return

    game.nominations[player_id] = decision
    await callback.answer("Ваш голос учтен.")

    if len(game.nominations) == (len(game.players) - 1 if game.lblock_player else len(game.players)):
        await finalize_final_vote(game.chat_id, nominee_id)

# Завершение финального голосования
async def finalize_final_vote(chat_id, nominee_id):
    game = active_games[chat_id]
    yes_votes = sum(1 for vote in game.nominations.values() if vote == "yes")
    no_votes = sum(1 for vote in game.nominations.values() if vote == "no")

    nominee_name = next(p["player_name"] for p in game.players if p["player_id"] == nominee_id)

    if yes_votes > no_votes:
        victim = next(p for p in game.players if p["player_id"] == nominee_id)
        game.players.remove(victim)
        await bot.send_message(chat_id=game.chat_id, message_thread_id=game.topic_id, text=f"Игрок {nominee_name} был линчёван.")
    else:
        await bot.send_message(chat_id=game.chat_id, message_thread_id=game.topic_id, text=f"Игрок {nominee_name} остался жив.")

    if not await declare_winner(game):
        await start_night_phase(chat_id)


# Распределение ролей
def distribute_roles(players):
    num_players = len(players)
    roles = []

    if num_players <= 6:
        roles = [DonMafia(None), Commissioner(None), Doctor(None)] + [Villager(None)] * (num_players - 3)
    elif num_players <= 9:
        roles = [Mafia(None), DonMafia(None), Commissioner(None), Doctor(None), Lover(None)] + [Villager(None)] * (num_players - 5)
    elif num_players <= 12:
        roles = [DonMafia(None), Commissioner(None), Doctor(None), Lover(None), Kamikaze(None), Hobo(None)] + [Villager(None)] * (num_players - 8) + [Mafia(None)]* 2
    elif num_players <= 15:
        roles = [DonMafia(None), Commissioner(None), Doctor(None), Lover(None), Kamikaze(None), Hobo(None), Judge(None), Maniac(None)] + [Villager(None)] * (num_players - 11) + [Mafia(None)]* 3


    random.shuffle(players)
    random.shuffle(roles)

    player_roles = {}
    for player, role in zip(players, roles):
        player["role"] = role
        role.player_id = player["player_id"]
        player_roles[player["player_id"]] = role

    return player_roles


async def declare_winner(game):
    winner = game.check_winner()
    if winner:
        if winner == "peaceful":
            text = "Мирные жители победили! Мафия уничтожена."
        elif winner == "mafia":
            text = "Мафия победила! Мирные жители проиграли."
        elif winner == "maniac":
            text = "Маньяк победил!"
        await bot.send_message(chat_id=game.chat_id, message_thread_id=game.topic_id, text=text)
        del active_games[game.chat_id]  # Завершаем игру и удаляем из активных
        game.end_game()
        del game
        return True


# Регистрация маршрутизатора
dp.include_router(router)

# Запуск бота
if __name__ == "__main__":
    import asyncio

    async def main():
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

    asyncio.run(main())
