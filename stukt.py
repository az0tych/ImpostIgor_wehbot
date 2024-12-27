import uuid
import sqlite3
import random
from contextlib import nullcontext
from typing import List, Optional
from datetime import datetime

# Функция для создания соединения с базой данных
def connect_db():
    conn = sqlite3.connect("leaderboard.db")
    return conn



class Role:
    """
    Базовый класс для ролей.
    """
    def __init__(self, player_id: int, role_name: str, role_desk: str):
        self.player_id = player_id  # Идентификатор игрока
        self.role_name = role_name  # Название роли
        self.role_desk = role_desk  # Описание роли

    def perform_action(self, *args, **kwargs):
        """
        Метод для выполнения действия роли. Реализуется в подклассах.
        """
        pass

class Mafia(Role):
    def __init__(self, player_id: int):
        role_desk = "Каждую ночь Вы голосуете за жертву. Но последнее слово за Доном.\nВы также можете общаться с напарниками в этом чате."
        super().__init__(player_id, "Мафия", role_desk)


    def perform_action(self, target_id: int):
        """
        Убивает одного игрока ночью.
        """
        return {"action": "kill", "target": target_id}

class DonMafia(Mafia):

    def __init__(self, player_id: int):
        super().__init__(player_id)
        self.role_name = "Дон Мафии"
        self.role_desk = "Каждую ночь Вы голосуете за жертву. Но помните последнее слово за Вами.\nВы также можете общаться с напарниками в этом чате."

    def finalize_decision(self, target_id: int):
        """
        Принимает окончательное решение при разногласиях.
        """
        return {"action": "final_kill", "target": target_id}

class Commissioner(Role):
    def __init__(self, player_id: int):
        role_desk = "Каждую ночь Вы можете проверить одного игрока на принадлежность его к мафии."
        super().__init__(player_id, "Комиссар", role_desk)

    def perform_action(self, target_id: int):
        """
        Проверяет роль одного игрока ночью.
        """
        return {"action": "investigate", "target": target_id}

class Doctor(Role):
    def __init__(self, player_id: int):
        role_desk = "Каждую ночь Вы можете вылечить одного игрока и спасти его от ночного убийства. Но помните, себя можно выбрать один раз."
        super().__init__(player_id, "Доктор", role_desk)
        self.self_heal = True

    def perform_action(self, target_id: int):
        """
        Лечит одного игрока. Предотвращает убийство, если цель жертва мафии.
        """
        return {"action": "heal", "target": target_id}

class Villager(Role):
    def __init__(self, player_id: int):
        role_desk = "Вы не имеете активных действий ночью. Ждите утра и вершите правосудие."
        super().__init__(player_id, "Мирный житель", role_desk)

class Lover(Role):
    def __init__(self, player_id: int):
        role_desk = "Каждую ночь Вы можете выбрать одного игрока и лишить его всех активных действий до следующей ночи."
        super().__init__(player_id, "Любовница", role_desk)

    def perform_action(self, target_id: int):
        """
        Блокирует действия одного игрока ночью.
        """
        return {"action": "block", "target": target_id}

class Kamikaze(Role):
    def __init__(self, player_id: int):
        role_desk = "Если вас убивают ночью, вы забираете убийцу с собой в могилу."
        super().__init__(player_id, "Камикадзе", role_desk)

    def perform_action(self, target_id: int):
        """
        Взорвать игрока ночью, умирая вместе с ним.
        """
        return {"action": "explode", "target": target_id}


class Maniac(Role):
    def __init__(self, player_id: int):
        role_desk = "Вы действуете независимо от всех. Каждую ночь убиваете одного игрока. Цель — остаться последним выжившим."
        super().__init__(player_id, "Маньяк", role_desk)

    def perform_action(self, target_id: int):
        """
        Убивает одного игрока ночью.
        """
        return {"action": "kill", "target": target_id}


class Judge(Role):
    def __init__(self, player_id: int):
        role_desk = "Вы можете один раз за игру отменить дневное голосование дав игроку иммунитет."
        super().__init__(player_id, "Судья", role_desk)
        self.vote_canceled = True  # Индикатор использования способности

    def perform_action(self):
        """
        Отменяет дневное голосование, если ещё не было использовано.
        """
        if not self.vote_canceled:
            self.vote_canceled = True
            return {"action": "cancel_vote"}
        else:
            return {"action": "ability_used"}


class Hobo(Role):
    def __init__(self, player_id: int):
        role_desk = "Каждую ночь вы можете наведаться к любому игроку и выпить. Будьте внимательны, возможно вы увидите убийцу."
        super().__init__(player_id, "Бомж", role_desk)
        self.current_target = None

    def perform_action(self, target_id: Optional[int] = None):
        """
        Начинает следить за игроком или, если цель умерла, раскрывает убийцу.
        """
        if self.current_target is None:
            self.current_target = target_id
            return {"action": "start_tracking", "target": target_id}
        else:
            return {"action": "reveal_killer", "target": self.current_target}


class Game:
    def __init__(self, game_id: Optional[str] = None, topic_id=None):
        self.game_id = game_id or str(uuid.uuid4())  # Уникальный идентификатор игры
        self.topic_id = topic_id
        self.players = []  # Список игроков
        self._players = []  # полный список игроков
        self.roles = []  # Список ролей
        self.state = "waiting"  # Состояние игры: waiting, night, day, finished
        self.creator_id = None
        self.player_roles = {}  # Хранение привязки игрока к роли
        self.night_actions = []  # Список действий на ночь
        self.lblock_player = None
        self.nominations = {}
        self.vote_canceled = None

    @staticmethod
    def update_user_stats(telegram_id, points_to_add=0, game_played=False, game_won=False):
        with connect_db() as conn:
            cursor = conn.cursor()

            # Обновление данных пользователя
            cursor.execute('''
                UPDATE leaderboard
                SET points = points + ?,
                    games_played = games_played + ?,
                    games_won = games_won + ?,
                    last_updated = ?
                WHERE telegram_id = ?
            ''', (
                points_to_add,  # Добавляемые очки
                1 if game_played else 0,  # Увеличение количества игр, если игра сыграна
                1 if game_won else 0,  # Увеличение побед, если игра выиграна
                datetime.now().isoformat(),  # Текущее время для last_updated
                int(telegram_id)
            ))

    def del_player(self, player_id: int):
        victim = next(p for p in self.players if p["player_id"] == player_id)
        self.players.remove(victim)

    def add_player(self, player_id: int, player_name: str, role: Optional[Role] = None):
        """
        Добавляет игрока в игру.
        """
        if any(player["player_id"] == player_id for player in self.players):
            raise ValueError("Игрок с таким ID уже существует.")
        self.players.append({"player_id": player_id, "player_name": player_name, "role": role})
        if role:
            self.roles.append(role)

    def start_game(self):
        """
        Начинает игру, переводя её в ночной этап.
        """
        if len(self.players) >= 4:
            self.state = "night"
            self._players = self.players
        else:
            raise ValueError("Недостаточно игроков для начала игры.")

    def end_game(self):
        """
        Завершает игру.
        """
        self.state = "finished"

    def change_role(self, player_id, new_role):
        # Ищем игрока с указанным id
        for player in self.players:
            if player['player_id'] == player_id:
                player['role'] = new_role(player_id)  # Меняем роль
                return f"Успешное изменение роли  игрока id: {player['player_id']} name: {player['player_name']} на роль: {player['role']}"
        return f"игрок с id: {player_id} не найден"

    # Проверка на победу одной из сторон
    def check_winner(self):
        mafia_count = sum(1 for p in self.players if isinstance(p["role"], (Mafia, DonMafia)))
        gray_count = sum(1 for p in self.players if isinstance(p["role"], Maniac))
        peaceful_count = len(self.players) - mafia_count - gray_count

        if gray_count > mafia_count + peaceful_count:
            for p in self._players:
                if isinstance(p["role"], Maniac):
                    self.update_user_stats(p["player_id"], 15, True, True)
                else:
                    self.update_user_stats(p["player_id"], 0, True, False)
            return "maniac"

        elif mafia_count == 0:
            for p in self._players:
                if not isinstance(p["role"], (Mafia, DonMafia, Maniac)):
                    self.update_user_stats(p["player_id"], 10, True, True)
                else:
                    self.update_user_stats(p["player_id"], 0, True, False)
            return "peaceful"  # Мирные жители победили

        elif mafia_count >= peaceful_count + gray_count:
            for p in self._players:
                if isinstance(p["role"], (Mafia, DonMafia)):
                    self.update_user_stats(p["player_id"], 10, True, True)
                else:
                    self.update_user_stats(p["player_id"], 0, True, False)
            return "mafia"  # Мафия победила

        else:
            return None  # Игра продолжается

    def process_night_actions(self):
        """
        Обрабатывает действия игроков ночью.
        """
        results = []
        kill_votes = {}
        final_kill_target = None
        heal_target = None
        m_kill_target = None


        for action in self.night_actions:
            if action["action"] == "block":
                # Блокировка действия
                results.append({"action": "block", "target_id": action["target_id"]})
                self.lblock_player = action["target_id"]
                for p in self._players:
                    if isinstance(p["role"], (Mafia, DonMafia, Commissioner, Doctor)) and p["player_id"] == action["target_id"]:
                        self.update_user_stats(int(action["player_id"]), 2, False, False)

            elif action["action"] == "investigate" and action["player_id"] != self.lblock_player:
                # Проверка роли игрока
                s = next(po for po in self.players if po["player_id"] == action["target_id"])
                t = f"Игрок {s['player_name']} не мафия."

                if isinstance(s["role"], (Mafia, DonMafia)):
                    t = f"Игрок {s['player_name']} мафия."
                    self.update_user_stats(int(action["player_id"]), 4, False, False)

                # Добавляем результат
                results.append({
                    "action": "investigate",
                    "player_id": action["player_id"],
                    "target_id": action["target_id"],
                    "text": t
                })

            elif action["action"] == "heal" and action["player_id"] != self.lblock_player:
                # Осуществляем лечение
                heal_target = action["target_id"]
                results.append({"action": "heal", "target_id": action["target_id"]})
                if action["target_id"] == action["player_id"]:
                    v = next(p for p in self.players if p["player_id"] == action["player_id"])
                    v["role"].self_heal = False

            elif action["action"] == "kill" and action["player_id"] != self.lblock_player:
                target_id = action["target_id"]
                kill_votes[target_id] = kill_votes.get(target_id, 0) + 1

            # Сохраняем выбор Дона мафии (final_kill)
            elif action["action"] == "final_kill" and action["player_id"] != self.lblock_player:
                target_id = action["target_id"]
                kill_votes[target_id] = kill_votes.get(target_id, 0) + 1
                final_kill_target = target_id


        # Определяем цели с наибольшим количеством голосов
        if kill_votes:
            max_votes = max(kill_votes.values())
            top_targets = [target_id for target_id, votes in kill_votes.items() if votes == max_votes]
            dead_pm = None

            # Если несколько целей с одинаковыми голосами, выбираем цель Дона мафии
            if len(top_targets) > 1 :
                if final_kill_target:
                    if heal_target == final_kill_target:
                        final_kill_target = None
            else:
                if heal_target != top_targets[0]:
                    final_kill_target = top_targets[0]
                else:
                    final_kill_target = None

            if final_kill_target:
                dead_pm = next(po for po in self.players if po["player_id"] == final_kill_target)
                textki = f"У игрока {dead_pm['player_name']} этой ночью побывала мафия."

                if isinstance(dead_pm["role"], Kamikaze):
                    ma = [po for po in self.players if isinstance(po["role"], (Mafia, DonMafia))]
                    m = random.choice(ma)
                    if m["player_id"] != heal_target:
                        results.append({"action": "explode", "player_id": dead_pm["player_id"], "target_id": m["player_id"],
                                        "text": f"Игрок {m['player_name']} нарвался на камикадзе"})
                        self.update_user_stats(int(dead_pm["player_id"]), 5, False, False)
                    #else:
                        #doc = next(po for po in self.players if isinstance(po["role"], Doctor))
                        #update_user_stats(int(doc["player_id"]), 5, False, False)

                for p in self.players:
                    if isinstance(p["role"], Mafia):
                        self.update_user_stats(int(p["player_id"]), 3, False, False)
                    if isinstance(p["role"], DonMafia):
                        self.update_user_stats(int(p["player_id"]), 4, False, False)

                results.append({
                    "action": "kill", "target_id": final_kill_target,
                    "text": textki
                })

            else:
                doc = next(po for po in self.players if isinstance(po["role"], Doctor))
                self.update_user_stats(int(doc["player_id"]), 5, False, False)


        for action in self.night_actions:
            # Логика Маньяка
            if action["action"] == "m_kill" and action["player_id"] != self.lblock_player and action["player_id"] != final_kill_target:
                if heal_target != action["target_id"]:
                    m_kill_target = action["target_id"]
                    self.update_user_stats(int(action["player_id"]), 3, False, False)
                    # Добавляем результат
                    a = next(p for p in self.players if p["player_id"] == action["target_id"])
                    results.append({
                        "action": "m_kill",
                        "player_id": action["player_id"],
                        "target_id": action["target_id"],
                        "text": f"Этой ночью был зверски убит игрок {a['player_name']}."
                    })
                    if isinstance(a["role"], Kamikaze):
                        m = next(po for po in self.players if isinstance(po["role"], Maniac))
                        if m["player_id"] != heal_target:
                            results.append(
                                {"action": "explode", "player_id": p["player_id"], "target_id": m["player_id"],
                                 "text": f"Игрок {m['player_name']} нарвался на камикадзе"})
                            self.update_user_stats(int(p["player_id"]), 5, False, False)
                        else:
                            doc = next(po for po in self.players if isinstance(po["role"], Doctor))
                            self.update_user_stats(int(doc["player_id"]), 5, False, False)


            # Логика Судьи
            elif action["action"] == "cancel_vote" and action["player_id"] != self.lblock_player and action["player_id"] != final_kill_target and action["player_id"] != m_kill_target:
                v = next(p for p in self.players if p["player_id"] == action["player_id"])
                v["role"].vote_canceled = False
                self.vote_canceled = action["target_id"]
                self.update_user_stats(int(action["player_id"]), 5, False, False)

            # Логика Бомжа
            elif action["action"] == "start_tracking" and action["player_id"] != self.lblock_player and action[
                "player_id"] != final_kill_target and action["player_id"] != m_kill_target:
                t = "Сегодня всё тихо."

                # Проверяем, совпадает ли цель с жертвой мафии
                if action["target_id"] == final_kill_target:
                    ma = [po for po in self.players if isinstance(po["role"], (Mafia, DonMafia))]
                    p = random.choice(ma)
                    t = f"ОЙ!! Кажется, вы видели {p['player_name']} на месте преступления."

                # Проверяем, совпадает ли цель с жертвой маньяка
                elif action["target_id"] == m_kill_target:
                    p = next(po for po in self.players if isinstance(po["role"], Maniac))
                    t = f"ОЙ!! Кажется, вы видели {p['player_name']} на месте преступления."

                # Проверяем, если игрок следит за мафией или маньяком
                elif action["target_id"] in [po["player_id"] for po in self.players if isinstance(po["role"], (Mafia, DonMafia, Maniac))]:
                    t = "Странно, но дома никого не было..."

                # Добавляем результат
                results.append({
                    "action": "start_tracking",
                    "player_id": action["player_id"],
                    "target_id": action["target_id"],
                    "text": t
                })
                if t != "Сегодня всё тихо.":
                    self.update_user_stats(int(action["player_id"]), 4, False, False)

        return results
