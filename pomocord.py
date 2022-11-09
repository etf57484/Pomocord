import discord
from discord import Option
from discord.ext import tasks
import os, time, datetime, uuid
from dotenv import load_dotenv

# import pymysql.cursors
import MySQLdb
import configparser
import os

load_dotenv()

class DBConnection:

    def __init__(self,sql,params):
        self.sql = sql
        self.params = params

        self.host = os.environ['DB_HOST']
        self.user = os.environ['DB_USER']
        self.password = os.environ['DB_PASSWORD']
        self.db = os.environ['DB_NAME']

        self.conn = MySQLdb.connect(host=self.host, user=self.user, password =self.password, db=self.db, charset='utf8mb4')

        self.rows = None

        self.sql_type = sql.split()[0]

    def select(self):
        cursor = self.conn.cursor()
        try:
            # self.rows = cursor.execute(self.sql,self.params)
            cursor.execute(self.sql,self.params)
        finally:
            self.conn.close()

        return cursor

    def insert(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute(self.sql,self.params)
            self.conn.commit()
        finally:
            self.conn.close()

    def execute(self):
        if self.sql_type=='SELECT':
            return self.select()

        if self.sql_type=='INSERT' or self.sql_type=='UPDATE':
            self.insert()

active_task = None
interval_end = None

bot = discord.Bot()
client = discord.Client()
'''
CREATE TABLE `tasks` (pomodoro_id int auto_increment, task_id varchar(36), task_name varchar(50), start datetime, end datetime, achieved BOOLEAN DEFAULT False, INDEX(pomodoro_id));
'''
class ActivePomodoro:
    def __init__(self,task_id):
        self.task_id = task_id

        sql = "SELECT * FROM `tasks` WHERE `task_id`=%(task_id)s ORDER BY `pomodoro_id` DESC LIMIT 1"
        params = {
            'task_id': self.task_id
        }
        conn = DBConnection(sql, params)
        result = conn.execute().fetchone()

        self.pomodoro_id = result[0]
        self.task_name = result[2]
        self.start = result[3]
        self.end = result[4]

    def get_total_pomodoro(self):
        sql = "SELECT COUNT(`pomodoro_id`) FROM `tasks` WHERE `task_id`=%(task_id)s "
        params = {
            'task_id':self.task_id
        }
        conn = DBConnection(sql,params)
        return conn.execute().fetchone()

    def achieved(self):
        sql = "UPDATE `tasks` SET `achieved`=1 WHERE `pomodoro_id`=%(pomodoro_id)s"
        params = {
            'pomodoro_id': self.pomodoro_id[0]
        }
        conn = DBConnection(sql,params)
        conn.execute()
        del conn



class NewTask:
    def __init__(self,task_name):
        self.task_name = task_name
        self.task_id = str(uuid.uuid4())
        self.pomodoro_id = []

        self.work_time = os.environ['WORK_TIME']
        self.interval_time = os.environ['INTERVAL_TIME']
        
    def add(self):
        global active_task
        # if active_task is not None:
        #     return False
        sql = "INSERT INTO `tasks`(`task_id`,`task_name`,`start`,`end`) VALUES(%(task_id)s,%(task_name)s,%(start)s,%(end)s)"
        params = {
            'task_id': self.task_id,
            'task_name': self.task_name,
            'start': datetime.datetime.now(),
            'end': datetime.datetime.now() + datetime.timedelta(minutes=self.work_time)
        }
        conn = DBConnection(sql,params)
        conn.execute()
        del conn

        sql = "SELECT `pomodoro_id` FROM `tasks` WHERE `task_id`=%(task_id)s ORDER BY `pomodoro_id` DESC LIMIT 1"
        params = {
            'task_id': self.task_id,
        }

        conn = DBConnection(sql,params)
        result = conn.execute().fetchone()
        self.pomodoro_id.insert(0,result[0])
        print(result)
        del conn

        active_task = self.task_id

    def get_end(self):
        sql = "SELECT `end` FROM `tasks` "

    def achieved(self):
        sql = "UPDATE `tasks` SET `end`=%(end)s WHERE `pomodoro_id`=%(pomodoro_id)s"
        params = {
            'end': datetime.datetime.now(),
            'pomodoro_id': self.pomodoro_id[0]
        }
        conn = DBConnection(sql,params)
        conn.execute()
        del conn

    def get_total_pomodoro(self):
        sql = "SELECT COUNT(`pomodoro_id`) FROM `tasks` WHERE `task_id`=%(task_id)s "
        params = {
            'task_id':self.task_id
        }
        conn = DBConnection(sql,params)
        return conn.execute().fetchone()

@bot.slash_command(name="start", description="タスクを開始します")
async def start(ctx, task_name: Option(str, required=True, description="タスク名を入力してください")):
    if not task_name:
        task_name = '無題のタスク'
    new_task = NewTask(task_name=task_name)

    await ctx.respond(f'[{task_name}]を開始します')

    global active_task
    pomodoro_time = 0
    pomodoro_emoji = ''

    while True:
        print(f'active_task:{active_task}')
        # if active_task is None:
        #     break
        pomodoro_time += 1
        pomodoro_emoji = pomodoro_emoji + '🍅'
        await ctx.respond(f'[{new_task.task_name}]\n{pomodoro_time}個目のポモドーロです{pomodoro_emoji}')
        new_task.add()
        time.sleep(int(os.environ['WORK_TIME']))
        
        if active_task is None:
            break
        await ctx.respond(f'{pomodoro_time}個目のポモドーロが終わりました！休憩しましょう！')
        new_task.achieved()
        time.sleep(int(os.environ['INTERVAL_TIME']))


@bot.slash_command(name="finish", description="タスクを完了します")
async def finish(ctx):
    global active_task
    if active_task is None:
        await ctx.respond(f'現在実行中のタスクはありません😥')
    else:
        finished_task = NewTask(task_id=active_task)
        finished_task.achieved()

        await ctx.respond(f'[{task_name}]を完了させました！お疲れ様です！')
        total_pomodoro = finished_task.get_total_pomodoro()
        total_pomodoro_emoji = ''
        for i in range(total_pomodoro):
            total_pomodoro_emoji += '🍅'
        await ctx.respond(f'獲得ポモドーロ：{total_pomodoro} {total_pomodoro_emoji}')
        del finished_task

@tasks.loop(seconds=60)
async def loop():
    # botが起動するまで待つ
    await client.wait_until_ready()

    global active_task, interval_end
    if active_task is not None:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        task = ActivePomodoro(task_id=active_task)
        if datetime.datetime.strptime(task.end, '%Y-%m-%d %H:%M') == now:
            pomodoro_count = task.get_total_pomodoro()
            await channel.send(f'{pomodoro_count}個目のポモドーロが終わりました！休憩しましょう！')
            task.achieved()

            interval_end = datetime.datetime.now() + datetime.timedelta(minutes=os.environ['INTERVAL_TIME'])

    print(os.environ['CHANNEL_ID'])
    channel = client.get_channel(int(os.environ['CHANNEL_ID']))
    await channel.send('時間だよ')  

loop.start()
# bot.run(os.environ['API_KEY'])
client.run(os.environ['API_KEY'])