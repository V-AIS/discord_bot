import re
import requests
from datetime import datetime

class ToDiscourse():
    def __init__(self, config):
        self.config = config
        self.HEADERS = {
            "Content-Type": "application/json",
            "Api-Key": config['TOKENS']['DISCOURSE']['KEY'],
            "Api-Username": config['TOKENS']['DISCOURSE']['NAME']
        }

    def post_topic(self, payload):
        URL = f"https://discuss.vais.dev/posts.json"
        res = requests.post(URL, headers=self.HEADERS, params=payload)
        return res

    def get_category_id(self):
        URL = "https://discuss.vais.dev/categories.json"
        res = requests.get(URL, headers=self.HEADERS)
        geeknews_category_id = [category["id"]for category in res.json()["category_list"]["categories"] if category["name"] == "GeekNews"][0]
        return geeknews_category_id

    def get_daily_post_id(self, category_name, category_id):
        title = f'{datetime.today().date().strftime("%Y년 %m월 %d일")} GeekNews'
        URL = f"https://discuss.vais.dev/c/{category_name}/{category_id}.json"
        res = requests.get(URL, headers=self.HEADERS).json()["topic_list"]["topics"]
        post_info = res[0] if len(res) else {}
        if post_info["fancy_title"] != title:
            payload = {
                "title": title,
                "raw": title,
                "category": category_id,
                "target_recipients": self.config['TOKENS']['DISCOURSE']['NAME']
            }
            daily_topic_id = self.post_topic(payload).json()["topic_id"]
        else: 
            daily_topic_id = post_info["id"]
        return daily_topic_id

    def post_geeknews(self, message):
        geeknews_category_id = self.get_category_id()
        daily_topic_id = self.get_daily_post_id("geeknews", geeknews_category_id)
        
        title = re.findall("(?<=\*\*\[).*?(?=])", message.content)
        address = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$\-@\.+:/?=]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', message.content)
        URL = f"https://discuss.vais.dev/posts.json"
        
        payload = {
        "title": title,
        "raw": address,
        "topic_id": daily_topic_id,
        "target_recipients": self.HEADERS,
        }
        
        self.post_topic(payload)