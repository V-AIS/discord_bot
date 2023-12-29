import json
import requests

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks

COLOR_MAP = {
    "판매": {"color": "pink", "id":"52ce2d6a-72c2-4040-a00d-96da20c5ceac"},
    "나눔": {"color": "purple", "id":"a817738e-96cc-448d-9bd3-95477beca7ce"},
    "구매": {"color": "yellow", "id":"cbfe5d72-b66d-4b33-a7b1-e7a5db904710"},
}


class Market(commands.Cog, name="market"):
    def __init__(self, bot):
        self.bot = bot
        self.header = {
                "Authorization": f"Bearer {self.bot.config['TOKENS']['NOTION']['KEY']}", 
                "Notion-Version": "2021-08-16",
                "Content-Type":"application/json"
                }
    
    @commands.hybrid_command(name="중고마켓", description="V-AIS 중고 마켓에 대한 설명입니다")
    @checks.not_blacklisted()
    async def help(self, context: Context) -> None:
        prefix = self.bot.config["PREFIX"]
        embed = discord.Embed(
            title="중고 마켓", description="물품을 사고 팔고 나눌 수 있어요!", color=0x9C84EF
        )
        
        commands = self.get_commands()
        data = []
        for command in commands:
            description = command.description.partition("\n")[0]
            data.append(f"{prefix}{command.name} - {description}")
        help_text = "\n".join(data)
        embed.add_field(
            name="명령어", value=f"```{help_text}```", inline=False
        )
        await context.send(embed=embed)
        
    @commands.hybrid_command(name="마켓등록",description="구매/판매/나눔을 해요")
    @checks.not_blacklisted()
    @app_commands.describe(kind="무엇을 하시나요? (구매/판매/나눔)", product="무엇을 구매/판매/나눔을 하시나요?", price="얼마인가요?", other="참고해야 할 사항이 있나요?")
    async def market_enroll(self, context: Context, *, kind: str, product: str, price: int, other: str) -> None:
        
        readurl = f"https://api.notion.com/v1/pages/"
        new_page_data = {
                        'parent': {'database_id': self.bot.config['TOKENS']['NOTION']['MARKET_TABLE_ID'],
                        'type': 'database_id'},
                        'properties': {
                            '가격': {'id': 'nSGB', 
                                    'number': 0 if kind=="나눔" else price, 
                                    'type': 'number'},

                            '물품명': {'id': '~A%60K',
                                'rich_text': [{
                                            'text': {'content': product},
                                            }],
                                'type': 'rich_text'},

                            '분류': {'id': 'cI%3Dy',
                                'select': {'color': COLOR_MAP[kind]["color"], 
                                            'id': COLOR_MAP[kind]["id"],
                                            'name': kind},
                                'type': 'select'},
                            
                            '사진': {
                                    'files': [], 
                                    'id': '%7By%40c', 
                                    'type': 'files'
                                    },
                            
                            '참고': {
                                'id': '%3Aste',
                                'rich_text': [{
                                            'text': {'content': other},
                                            }],
                                'type': 'rich_text'
                                },
                            
                            '판매자': {
                                'id': 'title',
                                'title': [{
                                        'text': {'content': context.author.name}
                                        }],
                                'type': 'title'
                                }}
        }
        
        res = requests.post(readurl, headers=self.header, data=json.dumps(new_page_data))
        if res.status_code == 200:
            text = f"{context.author.name}님의 {product}, 등록되었습니다!"
        else:
            text = F"{context.author.name}님의 {product}, 등록하지 못했습니다, {res.status_code}"
            
        embed = discord.Embed(
            title="**처리 상태**",
            description=f"{text}",
            color=0x9C84EF,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(name="마켓완료",description="구매/판매/나눔을 완료했어요")
    @checks.not_blacklisted()
    @app_commands.describe(kind="무엇을 하셨나요?(구매/판매/나눔)", product="무엇을 구매하시나요?")
    async def marker_complete(self, context: Context, *, kind: str, product: str) -> None:
        query_url = f"https://api.notion.com/v1/databases/{self.bot.config['TOKENS']['NOTION']['MARKET_TABLE_ID']}/query"
        filter = {
            "filter": {
                "and": [
                {
                    "property": "진행상태",
                            "checkbox": {
                                "equals": False
                            }
                },
                {
                            "property": "분류",
                            "select": {
                                "equals": kind
                            }
                },
                {
                            "property": "판매자",
                            "text": {
                                "equals": context.author.name
                            }
                },
                {
                            "property": "물품명",
                            "text": {
                                "equals": product
                            }
                        }
                    ]
                }
        }
        res = requests.post(query_url, headers=self.header, data=json.dumps(filter))
        page_id = res.json()["results"][0]["id"]
        
        page_url = f"https://api.notion.com/v1/pages/{page_id}"

        data = {
            "properties":{
                "진행상태": {"checkbox": True}
            }
        }

        res = requests.patch(page_url, headers=self.header, data = json.dumps(data))
        
        if res.status_code == 200:
            text = f"{context.author.name}님의 {product}, 완료되었습니다!"
        else:
            text = F"{context.author.name}님의 {product}, 완료하지 못했습니다, {res.status_code}"
            
        embed = discord.Embed(
            title="**처리 상태**",
            description=f"{text}",
            color=0x9C84EF,
        )
        await context.send(embed=embed)

# And then we finally add the cog to the bot so that it can load, unload, reload and use it's content.
async def setup(bot):
    await bot.add_cog(Market(bot))
