""""
Copyright © Krypton 2019-2023 - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 5.5.0
"""

import random

import asyncio
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks

# For Kalro
import os
import urllib
from PIL import Image

class Choice(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="앞", style=discord.ButtonStyle.blurple)
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "앞"
        self.stop()

    @discord.ui.button(label="뒤", style=discord.ButtonStyle.blurple)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = "뒤"
        self.stop()


class RockPaperScissors(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="가위", description="가위를 선택", emoji="✂"
            ),
            discord.SelectOption(
                label="바위", description="바위를 선택", emoji="🪨"
            ),
            discord.SelectOption(
                label="보", description="보를 선택", emoji="🧻"
            ),
        ]
        super().__init__(
            placeholder="선택의....순간....",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        choices = {
            "바위": 0,
            "가위": 1,
            "보": 2,
        }
        user_choice = self.values[0].lower()
        user_choice_index = choices[user_choice]

        bot_choice = random.choice(list(choices.keys()))
        bot_choice_index = choices[bot_choice]

        result_embed = discord.Embed(color=0x9C84EF)
        result_embed.set_author(
            name=interaction.user.name, icon_url=interaction.user.avatar.url
        )

        if user_choice_index == bot_choice_index:
            result_embed.description = f"**비겼습니다!**\n 둘 다 {user_choice}를 냈습니다!"
            result_embed.colour = 0xF59E42
        
        elif user_choice_index == 0 and bot_choice_index == 1:
            result_embed.description = f"**이겼습니다!!**\n 당신의 {user_choice}가 저의 {bot_choice}."
            result_embed.colour = 0x9C84EF
        
        elif user_choice_index == 1 and bot_choice_index == 2:
            result_embed.description = f"**이겼습니다!!**\n 당신의 {user_choice}가 저의 {bot_choice}."
            result_embed.colour = 0x9C84EF
        
        elif user_choice_index == 2 and bot_choice_index == 0:
            result_embed.description = f"**이겼습니다!!**\n 당신의 {user_choice}가 저의 {bot_choice}."
            result_embed.colour = 0x9C84EF
        
        else:
            result_embed.description = (
                f"**졌습니다...**\n {user_choice}는..... {bot_choice} 를 이길 수 없어요."
            )
            result_embed.colour = 0xE02B2B
        await interaction.response.edit_message(
            embed=result_embed, content=None, view=None
        )


class RockPaperScissorsView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(RockPaperScissors())


class Fun(commands.Cog, name="fun"):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="주저리주저리", description="아무 실화..를 출력합니다.")
    @app_commands.guilds(discord.Object(id=1082978815334170684)) # Place your guild ID here
    @checks.not_blacklisted()
    async def randomfact(self, context: Context) -> None:
        """
        Get a random fact.

        :param context: The hybrid command context.
        """
        # This will prevent your bot from stopping everything when doing a web request - see: https://discordpy.readthedocs.io/en/stable/faq.html#how-do-i-make-a-web-request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://uselessfacts.jsph.pl/random.json?language=en"
            ) as request:
                if request.status == 200:
                    data = await request.json()
                    embed = discord.Embed(description=data["text"], color=0xD75BF4)
                else:
                    embed = discord.Embed(
                        title="Error!",
                        description="There is something wrong with the API, please try again later",
                        color=0xE02B2B,
                    )
                await context.send(embed=embed)

    @commands.hybrid_command(name="코인토스", description="앞? 뒤? 맞춰보세요!")
    @checks.not_blacklisted()
    async def coinflip(self, context: Context) -> None:
        """
        Make a coin flip, but give your bet before.

        :param context: The hybrid command context.
        """
        buttons = Choice()
        embed = discord.Embed(description="어디에 걸어볼텐가....?", color=0x9C84EF)
        message = await context.send(embed=embed, view=buttons)
        await buttons.wait()  # We wait for the user to click a button.
        result = random.choice(["앞", "뒤"])
        if buttons.value == result:
            embed = discord.Embed(
                description=f"오올!! 도박에 성공했어요!!",
                color=0x9C84EF,
            )
        else:
            embed = discord.Embed(
                description=f"땡!! 도박하지마셈. 국번없이 1336.",
                color=0xE02B2B,
            )
        await message.edit(embed=embed, view=None, content=None)

    @commands.hybrid_command(name="가위바위보", description="자...가위바위보를 시작하지...")
    @checks.not_blacklisted()
    async def rock_paper_scissors(self, context: Context) -> None:
        """
        Play the rock paper scissors game against the bot.

        :param context: The hybrid command context.
        """
        view = RockPaperScissorsView()
        await context.send("게임 시작!", view=view)

    @commands.hybrid_command(name="칼로생성", description="Karlo를 이용해서 이미지를 생성합니다")
    @checks.not_blacklisted()
    @app_commands.describe(prompt="입력 할 프롬프트(영어로!!!)", negative_prompt="영어로!!!")
    async def karlo_generation(self, context: Context, *, prompt: str, negative_prompt: str=""):
        try:
            await context.defer()
            response = self.bot.kakao.karlo_t2i(prompt, negative_prompt)
            embed = discord.Embed(title="칼로 생성 결과", description=f"prompt: {prompt}\nnegative prompt: {negative_prompt}")
            # embed.set_image(url=response.get("images")[0].get("image"))
            # await asyncio.sleep(delay=0)
            # await context.reply(embed=embed)
            Image.open(urllib.request.urlopen(response.get("images")[0].get("image"))).save("tmp.jpg")
            file = discord.File("tmp.jpg", filename="tmp.jpg")
            embed.set_image(url="attachment://tmp.jpg")
            await asyncio.sleep(delay=0)
            await context.reply(file=file, embed=embed)
            os.remove("tmp.jpg")
        except:
            await context.reply("에러가 발생했습니다.")
async def setup(bot):
    await bot.add_cog(Fun(bot))
