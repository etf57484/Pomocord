import os, datetime

from notion_client import Client
from dotenv import load_dotenv

load_dotenv()

class NotionEdit:
    def __init__(self):
        self.notion_api = os.environ['NOTION_API']
        self.notion_db = os.environ['NOTION_DB']

        self.notion_total_pomodoro_id = os.environ['NOTION_TOTAL_POMODORO_ID']
        self.notion_today_pomodoro_id = os.environ['NOTION_TODAY_POMODORO_ID']

        self.notion = Client(auth=self.notion_api)

    def add_new_task(self, task_id, task_name, start, end, achieved, pomodoro):
        pomodoro_emoji = '🍅' * pomodoro
        self.notion.pages.create(
            **{
                # データベースID
                'parent': {'database_id': self.notion_db},
                'properties': {
                    'Pomodoro': {'select': {'name': pomodoro_emoji},},
                    'Achieved': {'checkbox': achieved, },
                    'End': {'date': {'end': None,
                                    'start': end.strftime('%Y-%m-%d %H:%M'),
                                    'time_zone': "Asia/Tokyo"},
                            },
                    'Task id': {'rich_text': [{'text': {'content': task_id,
                                                        'link': None}, }],
                                },
                    'Start': {'date': {'end': None,
                                    'start': start.strftime('%Y-%m-%d %H:%M'),
                                    'time_zone': "Asia/Tokyo"},
                            },
                    'Task name': {'title': [{'text': {'content': task_name,
                                                        'link': None}, }],
                                },
                }
                # ここにカラム名と値を記載
            }
        )

    def get_id_from_task_id(self, task_id):
        result = self.notion.databases.query(
            **{
                "database_id": self.notion_db,
                "filter": {
                    "or": [
                        {
                            "property": "Task id",
                            "rich_text": {"equals": task_id}
                        }
                    ]
                }
            }
        )
        id = result['results'][0]['id']
        return id

    def update_pomodoro(self, page_id, end, new_pomodoro, achieved):
        pomodoro_emoji = '🍅' * new_pomodoro
        ret = self.notion.pages.update(
            **{
                "page_id": page_id,
                "properties": {
                    "Pomodoro": {'select': {'name': pomodoro_emoji},},
                    "End": {'date': {'end': None,
                                        'start': end.strftime('%Y-%m-%d %H:%M'),
                                        'time_zone': "Asia/Tokyo"},
                            },
                    'Achieved': {'checkbox': achieved}
                }
            }
        )

    def update_pomodoro_count(self,notion_total_pomodoro,notion_today_pomodoro):
        ret = self.notion.blocks.update(
            **{
                "block_id": self.notion_total_pomodoro_id,
                "heading_3":{
                    'rich_text': [
                        {
                            'text': {
                                'content': is_multiple(notion_total_pomodoro,"pomodoro")
                            }
                        }
                    ]
                }
            }
        )

        ret = self.notion.blocks.update(
            **{
                "block_id": self.notion_today_pomodoro_id,
                "heading_3":{
                    'rich_text': [
                        {
                            'text': {
                                'content': is_multiple(notion_today_pomodoro,"pomodoro")
                            }
                        }
                    ]
                }
            }
        )


    def __del__(self):
        del self.notion

def is_multiple(number, noun, nouns=None):
    if nouns is None:
        nouns = noun + "s"
    if number > 1:
        return str(number)+f" {nouns}"
    else:
        return str(number)+f" {noun}"
