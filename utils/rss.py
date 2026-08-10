import asyncio
import os
import requests
import feedparser
from bs4 import BeautifulSoup

from helpers import db_manager

class YoutubeFeed():
    def __init__(self, logger) -> None:
        # 생성자에서 DB를 읽거나 asyncio.run() 을 부르지 않는다.
        # 이미 실행 중인 이벤트 루프 안에서 생성하면 RuntimeError 가 되고,
        # 스키마 생성 전에 생성하면 no such table 로 봇이 기동하지 못한다.
        self.logger = logger
        self.rss_urls = {}

    async def load(self) -> None:
        """구독 채널 목록을 DB에서 읽어 캐시를 채운다. init_db() 이후에 호출한다."""
        rows = await db_manager.get_youtube_channel_info()
        self.rss_urls = {row[0]: row[1] for row in rows}
        self.logger.info(f"{len(self.rss_urls)} channels subscribed !")

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
        if res.status_code != 200:
            # 채널명을 잘못 입력했을 시
            return "Check channel name"

        soup = BeautifulSoup(res.text, 'html.parser')
        link = soup.find('link', {'title': 'RSS'})
        if link is None or not link.get('href'):
            return "Check channel name"

        rss_link = link['href']
        await db_manager.add_youtube_channel_info(channel_name, rss_link)
        # DB만 고치면 폴링이 도는 self.rss_urls 에 반영되지 않아
        # 재시작 전까지 새 채널의 영상이 한 건도 올라오지 않는다.
        self.rss_urls[channel_name] = rss_link
        return "Channel information added"

    async def del_channel_rss_url(self, channel_name) -> str:
        await db_manager.del_youtube_channel_info(channel_name)
        # 캐시에서도 지워야 재시작 전까지 계속 수집되는 것을 막는다.
        self.rss_urls.pop(channel_name, None)
        return "Channel information deleted"
        
class TLDRFeed():
    def __init__(self):
        self.root_url = "https://tldr.tech"
        self.categories = ["tech", "ai"]
        self.headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
                }
    async def get_feed(self, date):
        contents = {}
        for category in self.categories:
            url = os.path.join(self.root_url, category, date)
            res = requests.get(url, headers=self.headers)
            if res.status_code != 200: 
                continue
            else:
                soup = BeautifulSoup(res.content, "html.parser")
                tmp_contents = {}

                for section in soup.find_all("section"):
                    if len(section.text)>10:
                        # header 가 없는 section 이 섞여 있다. .text 를 먼저 만지면
                        # None 접근으로 그날 피드 전체가 날아간다.
                        header_tag = section.find("header")
                        if header_tag is None: continue
                        header = header_tag.text
                        if not header: continue
                        if header not in tmp_contents:
                                tmp_contents[header] = {}
                        for article in section.find_all("article"):
                            tmp = article.find("a")
                            title = tmp.text
                            link = tmp["href"]
                            content = article.find("div").text
                            tmp_contents[header][title] = {
                                                "link": link,
                                                "content": content
                                            }
            contents[category] = tmp_contents
        return contents

def get_investing_finance_news():
    feed = feedparser.parse("https://kr.investing.com/rss/news_285.rss")
    return feed.entries