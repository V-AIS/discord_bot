import requests
import os
from bs4 import BeautifulSoup

class TLDRFeed():
    def __init__(self):
        self.root_url = "https://tldr.tech"
        self.categories = ["tech", "ai"]

    def get_feed(self, date):
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
    
    
tldr = TLDRFeed()
date = "2023-11-22"
feeds = tldr.get_feed(date)
for field in feeds:
    print(f"# Daily TLDR {field.upper()} ({date})")
    for subject in feeds[field]:
        if subject == "TLDR": continue
        divider = len(feeds[field][subject]) if len(feeds[field][subject]) else 1
        max_length = int(1024/divider)
        for title in feeds[field][subject]:
            value =  f"{feeds[field][subject][title]['link']}\n{feeds[field][subject][title]['content'][:]}\n\n"
            if len(value) > max_length:
                value = value[:max_length-3] + "..."
            print(value)