import typing
import json
import requests

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
        if not content:
            response = "내용을 입력하세요!"
            color = discord.Color.red()
        else:
            try: 
                response = self.model.generate_content(contents=[content]).text
                color = discord.Color.green()
            except:
                response = "기능 확인이 필요합니다! 운영진에게 알려주세요!"
                color = discord.Color.red()

        embed = discord.Embed(
            description=f"{response}",
            color=color,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(name="exaone", description="Exaone에게 물어봅니다! 일회성 질문이에요!")
    @checks.not_blacklisted()
    @app_commands.describe(content="물어볼 내용!")
    async def ask_to_exaone(self, context: Context, *, content: str=""):
        if not content:
            response = "내용을 입력하세요!"
            color = discord.Color.red()
        else:
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
                response = response["message"]["content"]
                color = discord.Color.green()
            except:
                response = "기능 확인이 필요합니다! 운영진에게 알려주세요!"
                color = discord.Color.red()
         
            embed = discord.Embed(
                        description=f"{response}",
                        color=color,
                    )
            await context.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LLM(bot))