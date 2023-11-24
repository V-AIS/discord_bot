import asyncio
import os
import requests
import feedparser
from bs4 import BeautifulSoup

from helpers import db_manager

class YoutubeFeed():
    def __init__(self, logger) -> None:
        # 동작 확인    
        self.rss_urls = {}
        rows = asyncio.run(db_manager.get_youtube_channel_info())
        for row in rows:
            self.rss_urls.update({row[0]: row[1]})
        logger.info(f"{len(self.rss_urls)} channels subscribed !")                
        
        return 

    # 동작 확인
    async def get_new_video(self) -> None:
        for rss_url in self.rss_urls.values():
            feeds = feedparser.parse(rss_url)
            for feed in feeds.entries:            
                await db_manager.add_youtube_video(feed['author'], feed['id'], feed['link'], feed['published'])
        return 
    
    async def add_channel_rss_url(self, channel_name) -> str:
        url = f"https://youtube.com/@{channel_name}"
        res = requests.get(url)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            await db_manager.add_youtube_channel_info(channel_name, soup.find('link', {'title': 'RSS'})['href'])
            result = "Channel information added"
        else:
            # 채널명을 잘못 입력했을 시 에러 발생 필요
            result = "Check channel name"
        return  result

    async def del_channel_rss_url(self, channel_name) -> str:
        await db_manager.del_youtube_channel_info(channel_name)
        
class TLDRFeed():
    def __init__(self):
        self.root_url = "https://tldr.tech"
        self.categories = ["tech"]

    async def get_feed(self, date):
        contents = {}
        for category in self.categories:
            url = os.path.join(self.root_url, category, date)
            res = requests.get(url)
            if res.status_code != 200: 
                continue
            else:
                soup = BeautifulSoup(res.content, "html.parser")
                tmp_contents = {}
                for div in soup.find_all("div", class_="mt-3"):
                    if len(div.text)<10: 
                        key = div.parent.text.replace("\n", " ")
                        if key not in tmp_contents:
                            tmp_contents[key] = {}
                        for sub_div in div.parent.parent.find_all("div", class_="mt-3"):
                            if len(sub_div.text) < 40: continue
                            title = sub_div.find("a").text.replace("\n", "")
                            link = sub_div.find("a")["href"]
                            tmp_contents[key][title] = {
                                "link": link,
                                "content": sub_div.find("div").getText()
                            }
            contents[category] = tmp_contents
        return contents

def get_investing_finance_news():
    feed = feedparser.parse("https://kr.investing.com/rss/news_285.rss")
    return feed.entries
