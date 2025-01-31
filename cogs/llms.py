import typing
import json
import requests
import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks, db_manager

from google import generativeai as genai 

class LLM(commands.Cog, name="llm"):
    def __init__(self, bot):
        self.bot = bot
        genai.configure(api_key=bot.config["TOKENS"]["GOOGLE"]["KEY"])
        self.model = genai.GenerativeModel(model_name = 'gemini-2.0-flash-exp', system_instruction="You are a helpful assistant.")
    
    @commands.hybrid_command(name="gemini", description="Gemini에게 물어봅니다! 일회성 질문이에요!")
    @checks.not_blacklisted()
    @app_commands.describe(content="물어볼 내용!")
    async def ask_to_gemini(self, context: Context, *, content: str=""):
        await context.interaction.response.defer(ephemeral=False, thinking=True)

        embed = discord.Embed()
        if not content:
            embed.color = discord.Color.red()
            embed.description =  "내용을 입력하세요!"
        else:
            asyncio.sleep(3)
            try: 
                embed.color = discord.Color.green()
                response = self.model.generate_content(contents=[content])
                embed.description = response.text
                embed.set_author(name="Gemini", icon_url="https://camo.githubusercontent.com/77ba4ba362fc39151379e4e7691125c8bb130eb2ade811ce9f76d4d5236c6847/68747470733a2f2f75706c6f61642e77696b696d656469612e6f72672f77696b6970656469612f636f6d6d6f6e732f7468756d622f662f66302f476f6f676c655f426172645f6c6f676f2e7376672f3132303070782d476f6f676c655f426172645f6c6f676f2e7376672e706e67")
            except Exception as e:
                embed.color = discord.Color.red()
                embed.description =  "기능 확인이 필요합니다! 운영진에게 알려주세요!"
                self.bot.logger.error(f"{e}")
        await context.interaction.followup.send(embed=embed)

    @commands.hybrid_command(name="exaone", description="Exaone에게 물어봅니다! 일회성 질문이에요!")
    @checks.not_blacklisted()
    @app_commands.describe(content="물어볼 내용!")
    async def ask_to_exaone(self, context: Context, *, content: str=""):
        await context.interaction.response.defer()

        embed = discord.Embed()
        if not content:
            embed.color = discord.Color.red()
            embed.description =  "내용을 입력하세요!"
        else:
            asyncio.sleep(3)
            try:
                headers = {"Content-Type": "application/json; charset=utf-8"}
                data = {
                        "model": "exaone3.5:2.4b",
                        "stream": False,
                        "messages": [
                            {
                                "role": "user",
                                "content": content,
                            }
                        ],
                    }
                response = requests.post(f'{self.bot.config["TOKENS"]["ORACLE"]["HOST"]}/api/chat', headers=headers, data=json.dumps(data)) .json()
                embed.color = discord.Color.green()
                embed.description = response["message"]["content"]
            except Exception as e:
                embed.color = discord.Color.red()
                embed.description = "기능 확인이 필요합니다! 운영진에게 알려주세요!"

        await context.interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LLM(bot))