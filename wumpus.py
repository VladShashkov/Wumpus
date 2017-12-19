from flask import Flask, request
#import telebot
import urllib3
import telepot
import sqlite3
import config3 as config
import random


GSTATUS = (
  (-3, "Отменена"),
  (-2, "Проигрыш"),
  (-1, "Победа"),
  (0, "Новая"),
  (1, "Выбор действия"),
  (2, "Ввод перехода"),
  (3, "Длина выстрела"),
  (4, "Полет 1"),
  (5, "Полет 2"),
  (6, "Полет 3"),
  (7, "Полет 4"),
  (8, "Полет 5"))

EMPTY = 'empty'
WUMPUS = 'wumpus'
BATS = 'bats'
PIT = 'pit'
WARNINGS = {EMPTY:'',
            WUMPUS:"Ощущается запах Wumpus'а.",
            BATS:"Летучие мыши поблизости.",
            PIT:"Чувствуется сквозняк."}

layout = [['1',1,4,7,False,EMPTY], ['2',0,2,9,False,EMPTY], ['3',1,3,11,False,EMPTY], ['4',2,4,13,False,EMPTY], ['5',0,3,5,False,EMPTY],
          ['6',4,6,14,False,EMPTY], ['7',5,7,16,False,EMPTY], ['8',0,6,8,False,EMPTY], ['9',7,9,17,False,EMPTY], ['10',1,8,10,False,EMPTY],
          ['11',9,11,18,False,EMPTY], ['12',2,10,12,False,EMPTY], ['13',11,13,19,False,EMPTY], ['14',3,12,14,False,EMPTY], ['15',5,13,15,False,EMPTY],
          ['16',14,16,19,False,EMPTY], ['17',6,15,17,False,EMPTY], ['18',8,16,18,False,EMPTY],  ['19',10,17,19,False,EMPTY], ['20',12,15,18,False,EMPTY]]

def playerroom(cave, player):
  ret = [WARNINGS[cave[r][5]] for r in (cave[player][1],cave[player][2],cave[player][3])]
  if [r for r in (cave[player][1],cave[player][2],cave[player][3]) if cave[r][4]]:
      ret.insert(0, WARNINGS[WUMPUS])
  ret = ['    ' + r for r in ret if r]
  ret.insert(0, "Ты в комнате {0}.".format(cave[player][0]))
  ret.append("Тунели ведут в команты {0}, {1}, {2}.".format(*[cave[n][0] for n in (cave[player][1],cave[player][2],cave[player][3])]))
  return ret

# Создадим пустой объект
class pChat(object):
    def __init__(self):
        self.id = 0
        self.type = ''
        self.title = ''

class pFromUser(object):
    def __init__(self):
        self.id = 0
        self.first_name = ''
        self.last_name = ''
        self.username = ''

class pMess(object):
    def __init__(self):
        self.text = ''
        self.chat = pChat()
        self.from_user = pFromUser()

class SQLighter:
    def __init__(self, database):
        self.connection = sqlite3.connect(database)
        self.cursor = self.connection.cursor()
        self.ret = ['',]
        self.arrows = 5

    def reset_game(self, chatid):
        """ Начать игру заново  """
        with self.connection:
          try:
            self.cursor.execute("UPDATE w_games SET status=-3 WHERE (status>=0) and chat_id = ?", (chatid,)).fetchall()
            self.connection.commit()
          except:
            pass

    def select_game(self, chatid):
        """ Получаем игру, если она началась не позже 15 минут назад и еще не закончена """
        with self.connection:
          try:
            game = self.cursor.execute("SELECT * FROM w_games WHERE (status >= 0) and ((strftime('%s','now') - strftime('%s',start_game)) < {time}) and chat_id = {id}".format(time=config.GAME_TIMEOUT,id=chatid)).fetchall()[0]
            self.gameid = game[0]
            self.cave = [[l[0],l[1],l[2],l[3],l[4],l[5],] for l in layout]
            self.cave[game[6]][4] = True
            self.cave[game[7]][5] = BATS
            self.cave[game[8]][5] = BATS
            self.cave[game[9]][5] = PIT
            self.cave[game[10]][5] = PIT
            self.wumpus_room = game[6]
            self.status = game[4]
            self.gamer = game[5]
            self.arrows = game[3]
            self.shootRange = game[11]
            self.shootRoom = game[12]
            self.isnewchat = [0,]
            return game
          except:
            self.isnewchat = self.cursor.execute('SELECT count(*) FROM w_chat_detail WHERE (chat_id = (?))',(chatid,)).fetchall()[0]
            return None

    def log_game(self, m='', user = ''):
        with self.connection:
          try:
            self.cursor.execute('INSERT into w_game_logs (TimeStump, game_id,game_status,wumpus_room,gamer_room,arrow_count,player_cmd) VALUES(CURRENT_TIMESTAMP,(?),(?),(?),(?),(?),(?))',
                (self.gameid,
                  self.status,
                  self.wumpus_room,
                  self.gamer,
                  self.arrows,
                  m,)).fetchall()
            self.connection.commit()
            return "Игра: "+str(self.gameid)+" играет: "+user+" статус игры:"+str(self.status)+" пришла комада:"+m
          except:
            return "Ошибка записи лога в базу"

    def new_game(self, m):
        """ Создаем игровое поле """
        self.cave = [[l[0],l[1],l[2],l[3],l[4],l[5],] for l in layout]

        bats_1_room = random.randint(0, 19)
        self.cave[bats_1_room][5] = BATS
        room = random.randint(0, 19)
        while self.cave[room][5] != EMPTY:
          room = random.randint(0, 19)
        self.cave[room][5] = BATS
        bats_2_room = room
        while self.cave[room][5] != EMPTY:
          room = random.randint(0, 19)
        self.cave[room][5] = PIT
        pit_1_room = room
        while self.cave[room][5] != EMPTY:
          room = random.randint(0, 19)
        self.cave[room][5] = PIT
        pit_2_room = room
        wumpus_room = random.randint(0, 19)
        self.cave[wumpus_room][4] = True
        gamer = random.randint(0, 19)
        while (self.cave[gamer][5] != EMPTY) or self.cave[gamer][4]:
          gamer = random.randint(0, 19)

        with self.connection:
            #isnewchat = self.cursor.execute('SELECT count(*) FROM w_chat_detail WHERE (chat_id = (?))',(m.chat.id,)).fetchall()[0]
            self.cursor.execute('INSERT into w_games (chat_id,start_game,gamer,wumpus,bats_1,bats_2,pit_1,pit_2) VALUES(?,CURRENT_TIMESTAMP,?,?,?,?,?,?)',(m.chat.id,gamer,wumpus_room,bats_1_room,bats_2_room,pit_1_room,pit_2_room,)).fetchall()
            #lid = self.cursor.lastrowid
            if int(self.isnewchat[0]) == 0:
              self.cursor.execute('INSERT into w_chat_detail (chat_create,chat_id,chat_type,chat_title,tel_user_id,tel_first_name,tel_last_name,tel_username) VALUES(CURRENT_TIMESTAMP,(?),(?),(?),(?),(?),(?),(?))',
                (m.chat.id,
                  m.chat.type,
                  m.chat.title,
                  m.from_user.id,
                  m.from_user.first_name,
                  m.from_user.last_name,
                  m.from_user.username,)).fetchall()
            self.connection.commit()
            return playerroom(self.cave, gamer)

    def setstatus(self, chatid, newstatus):
        """ Фиксируем выбор  """
        with self.connection:
          try:
            self.cursor.execute("UPDATE w_games SET status=? WHERE game_id = ?", (newstatus, self.gameid,)).fetchall()
            self.connection.commit()
          except:
            pass

    def move(self, chatid, moveto):
        """ ВОЗВРАЩАЕМ СТАТУС """
        with self.connection:
            if moveto not in (self.cave[self.gamer][1], self.cave[self.gamer][2], self.cave[self.gamer][3]):
              self.ret = playerroom(self.cave, self.gamer)
              self.ret.insert(0, "Невозможно переместиться!")
              self.ret.append("Перейти куда ?")
              return self.ret

            self.gamer = moveto
            self.__move0()

            if self.status > 0:
              self.status = 1
              self.ret = self.ret + playerroom(self.cave, self.gamer)
              self.ret.append("Стрелять или Перейти (С-П)? ")
            else:
              self.ret.append("ХА ХА ХА-Продул!")
              self.ret.append("Как сам? (Р-Расстроен, Н-Норм, В-Воодушевлен)")#Как сам, подстрелить Wumpus'а слабо?

            self.cursor.execute("UPDATE w_games SET status={sts}, gamer={gmr}, wumpus={wmps} WHERE game_id = {cht}".format(wmps=self.wumpus_room,sts=self.status,gmr=self.gamer,cht=self.gameid)).fetchall()
            self.connection.commit()
        return self.ret

    def __move0(self):
        if self.cave[self.gamer][4]:
            self.ret.append("... ОЙ! Наткнулся на Wumpus'а!")
            if random.random() < 0.75:
                self.__movewumpus()
            else:
                #raise PlayerDeath("TSK TSK TSK-Wumpus got you!")
                self.status = -2
                print(self.log_game("ХРУМ, ХРУМ, ХРУМ - Wumpus съел тебя!"))
                self.ret.append("ХРУМ, ХРУМ, ХРУМ - Wumpus съел тебя!")
        elif self.cave[self.gamer][5] == PIT:  # self.player.pit
            #raise PlayerDeath("YYYYIIIIEEEE . . . Fell in a pit.")
            self.status = -2
            print(self.log_game("ААААЙЙЙЙ . . . Упал в яму."))
            self.ret.append("ААААЙЙЙЙ . . . Упал в яму.")
        elif self.cave[self.gamer][5] == BATS: # self.player.bats:
            self.ret.append("ЦАП-Тебя схватили гигантские летучие мыши! И затащили непонятно куда!")
            self.gamer = random.randint(0, 19) #random.choice(self.rooms)
            self.__move0()

    def __movewumpus(self):
        #Move the wumpus to a neighboring room
        self.cave[self.wumpus_room][4] = False
        self.wumpus_room = random.choice((self.cave[self.wumpus_room][1], self.cave[self.wumpus_room][2], self.cave[self.wumpus_room][3],))
        self.cave[self.wumpus_room][4] = True
        if self.wumpus_room == self.gamer:
            #raise PlayerDeath("TSK TSK TSK-Wumpus got you!")
            self.status = -2
            print(self.log_game("ХРУМ, ХРУМ, ХРУМ - Wumpus съел тебя!"))
            self.ret.append("ХРУМ, ХРУМ, ХРУМ - Wumpus съел тебя!\nКак сам? (Р-Расстроен, Н-Норм, В-Воодушевлен)")

    def shoot(self, m, range = 0):
        """ СТРЕЛЯЕМ """
        if self.status == 3:
          self.status = 4
          with self.connection:
            self.cursor.execute("UPDATE w_games SET status={sts}, shootRange={rng}, arrows={arr} WHERE game_id={cht}".format(arr=self.arrows,rng=range,sts=self.status,cht=self.gameid)).fetchall()
            self.connection.commit()
          return ['В напралении комнаты №',]

        elif self.status == 4:
          if range == self.gamer:
            return ['Стрела не может развернуться-попробуй другую комнату.','Комната №',]
          self.status = 5
          if range in (self.cave[self.gamer][1], self.cave[self.gamer][2], self.cave[self.gamer][3],):
            arrow = range
          else:
            arrow = random.choice((self.cave[self.gamer][1], self.cave[self.gamer][2], self.cave[self.gamer][3],))
          if self.shootRange > 1:
            with self.connection:
              self.cursor.execute("UPDATE w_games SET status={sts}, shootRoom={arr} WHERE game_id={cht}".format(arr=arrow,sts=self.status,cht=self.gameid)).fetchall()
              self.connection.commit()
            self.ret = ['Вторая комната №',]
        elif self.status in (5,6,7,8):
          if range == self.shootRoom:
            return ['Стрела не может развернуться-попробуй другую комнату.','Комната №',]
          self.status = self.status + 1
          if range in (self.cave[self.shootRoom][1], self.cave[self.shootRoom][2], self.cave[self.shootRoom][3],):
            arrow = range
          else:
            arrow = random.choice((self.cave[self.shootRoom][1], self.cave[self.shootRoom][2], self.cave[self.shootRoom][3],))
          if self.shootRange > (self.status-4):
            with self.connection:
              self.cursor.execute("UPDATE w_games SET status={sts}, shootRoom={arr} WHERE game_id={cht}".format(arr=arrow,sts=self.status,cht=self.gameid)).fetchall()
              self.connection.commit()
            self.ret = ['Далее комана №',]
        else:
          pass

        if arrow == self.gamer:
          self.setstatus(m.chat.id, -2)
          print(self.log_game("ОЙ! Стрела попала в тебя!"))
          return ["ОЙ! Стрела попала в тебя!","ХА ХА ХА-Продул!","Как сам? (Р-Расстроен, Н-Норм, В-Воодушевлен)"] #Как сам, подстрелить Wumpus'а слабо?
        elif self.cave[arrow][4]:
          self.setstatus(m.chat.id, -1)
          print(self.log_game("ТОЧНО! Ты пристрелил Wumpus'а!"))
          return ["ТОЧНО! Ты пристрелил Wumpus'а!","КХЕ КХЕ КХЕ - В следующий раз Wumpus тебя отведает!!","Как сам? (Р-Расстроен, Н-Норм, В-Воодушевлен)"] #А еще раз подстрелить Wumpus'а слабо?
        if self.shootRange < (self.status - 3):
          self.ret = ["Промах :/",]
          self.status = 1
          self.__movewumpus()
          if self.status > 0:
            if self.arrows < 1: # Стрел больше нет
              self.status = -2
              print(self.log_game("Закончились стрелы!"))
              self.ret.append("Закончились стрелы! Ты проиграл этот поединок. Как сам? (Р-Расстроен, Н-Норм, В-Воодушевлен)")
            else:
              self.ret = self.ret + playerroom(self.cave, self.gamer)
              self.ret.append("Стрелять или Перейти (С-П)? ")
        self.setstatus(m.chat.id, self.status)
        return self.ret

    def close(self):
        """ Закрываем текущее соединение с БД """
        self.connection.close()


telepot.api._pools = {
    'default': urllib3.ProxyManager(proxy_url=config.proxy_url, num_pools=3, maxsize=10, retries=False, timeout=30),
}
telepot.api._onetime_pool_spec = (urllib3.ProxyManager, dict(proxy_url=config.proxy_url, num_pools=1, maxsize=1, retries=False, timeout=30))

bot = telepot.Bot(config.TOKEN)
bot.setWebhook("https://wumpusbot.pythonanywhere.com/{}".format(config.secret), max_connections=100)

app = Flask(__name__)


#@bot.message_handler(commands=['start'])
def start(message):
 # Подключаемся к БД
  db_worker = SQLighter(config.database_name)
  game = db_worker.select_game(message.chat.id)
  if game:
    db_worker.reset_game(message.chat.id)
    bot.sendMessage(message.chat.id, "Игра сброшена.")
  else:
    bot.sendMessage(message.chat.id, 'Готов!))')
  # Отсоединяемся от БД
  db_worker.close()
  bot.sendMessage(message.chat.id, "Поиграем в игру Охота на Wumpus'а? (О-описание, И-Играем)")

#@bot.message_handler(commands=['stop'])
def stop(message):
 # Подключаемся к БД
  db_worker = SQLighter(config.database_name)
  game = db_worker.select_game(message.chat.id)
  if game:
    db_worker.reset_game(message.chat.id)
    bot.sendMessage(message.chat.id, "Игра остановлена.")
  else:
    bot.sendMessage(message.chat.id, 'Стою!))')
  # Отсоединяемся от БД
  db_worker.close()


@app.route('/{}'.format(config.secret), methods=["POST"])
def telegram_webhook():
  update = request.get_json()
  if not "message" in update:
    return "OK"
#  try:
  message = pMess()
  message.text = update["message"]["text"]
  message.chat.id = int(update["message"]["chat"]["id"])
  try:
    message.chat.type = update["message"]["chat"]["type"]
  except:
    pass
  try:
    message.chat.title = update["message"]["chat"]["title"]
  except:
    pass
  try:
    message.from_user.first_name = update["message"]["from"]["first_name"]
  except:
    pass
  try:
    message.from_user.last_name = update["message"]["from"]["last_name"]
  except:
    pass
  try:
    message.from_user.username = update["message"]["from"]["username"]
  except:
    pass
#    return "OK"
# Проверяем команды
  if message.text == '/stop':
      stop(message)
      return "OK"
  if message.text == '/start':
      start(message)
      return "OK"

 # Подключаемся к БД
  db_worker = SQLighter(config.database_name)
  game = db_worker.select_game(message.chat.id)
  if game:
    print(db_worker.log_game(message.text, message.from_user.first_name))

    if db_worker.status in (0,1):
      if message.text.lower() == 'с':
        db_worker.setstatus(message.chat.id, 3)
        bot.sendMessage(message.chat.id, "Дальность полета стрелы (1-5) комнат?")
      elif message.text.lower() == 'п':
        db_worker.setstatus(message.chat.id, 2)
        bot.sendMessage(message.chat.id, "Перейти куда ?")
      else:
        bot.sendMessage(message.chat.id, "Стрелять или Перейти (С-П)? ")
    elif db_worker.status == 2:
      try:
        roomnum = int(message.text)
      except:
        roomnum = -1
      if roomnum in range(1, 21):
        msg = db_worker.move(message.chat.id, roomnum-1)
        str1 = '\n'.join(msg)
      else:
        str1 = "Перейти куда ?"
      bot.sendMessage(message.chat.id, str1)
    elif db_worker.status == 3:
      try:
        shootRange = int(message.text)
      except:
        shootRange = -1
      if shootRange in range(1, 6):
        db_worker.arrows = db_worker.arrows - 1
        msg = db_worker.shoot(message, shootRange)
        str1 = '\n'.join(msg)
      else:
        str1 = "Дальность полета стрелы (1-5) комнат?"
      bot.sendMessage(message.chat.id, str1)

    elif db_worker.status in (4,5,6,7,8):
      try:
        shootRoom1 = int(message.text)
      except:
        shootRoom1 = -1
      if shootRoom1 in range(1, 21):
        msg = db_worker.shoot(message, shootRoom1-1)
        str1 = '\n'.join(msg)
      else:
        str1 = "Комната №"
      bot.sendMessage(message.chat.id, str1)
    else:
      bot.sendMessage(message.chat.id, "Есть игра {name}.".format(name=game[0]))
  else:
    if message.text.lower() == 'о':
      bot.sendMessage(message.chat.id, config.INSTRUCTIONS0)
    elif message.text.lower() == 'п':
      bot.sendMessage(message.chat.id, config.INSTRUCTIONS1)
      bot.sendMessage(message.chat.id, config.INSTRUCTIONS2)
      bot.sendMessage(message.chat.id, config.INSTRUCTIONS3)
      bot.sendMessage(message.chat.id, config.INSTRUCTIONS4)
      msg = db_worker.new_game(message)
      str1 = '\n'.join(msg)
      bot.sendMessage(message.chat.id, str1 + "\nСтрелять или Перейти (С-П)? ")
    elif message.text.lower() in ('р','н','в'):
      eS = {"р":-1,"н":0,"в":1}
      str = "UPDATE w_games SET emoStatus={est} WHERE chat_id={cht} and game_id in (select max(game_id) from w_games where chat_id={cht} and ((strftime('%s','now') - strftime('%s',start_game)) < {time}))".format(est=eS[message.text.lower()], cht=message.chat.id, time=config.GAME_TIMEOUT)
      #print (str)
      db_worker.cursor.execute(str).fetchall()
      db_worker.connection.commit()
      bot.sendMessage(message.chat.id, "Благодарю за отзыв))\nПоиграем в игру Охота на Wumpus'а? (О-описание, И-Играем)")
    elif message.text.lower() == 'и':
      msg = db_worker.new_game(message)
      str1 = '\n'.join(msg)
      bot.sendMessage(message.chat.id, str1 + "\nСтрелять или Перейти (С-П)? ")
    else:
      if int(db_worker.isnewchat[0]) == 0:
        bot.sendMessage(message.chat.id, config.INSTRUCTIONS0)
      bot.sendMessage(message.chat.id, "Поиграем в игру Охота на Wumpus'а? (О-описание, И-Играем)")
  # Отсоединяемся от БД
  db_worker.close()
  return "OK"

