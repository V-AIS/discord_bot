"""
Copyright © Krypton 2019-2023 - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 5.5.0
"""

import asyncio
import json
import logging
import os
import platform
import sys
from datetime import datetime, timedelta

import pymongo
import aiosqlite
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context

import exceptions
import archiving
import helpers
import utils

if not os.path.isfile(f"{os.path.realpath(os.path.dirname(__file__))}/config.json"):
    sys.exit("'config.json' not found! Please add it and try again.")
else:
    with open(f"{os.path.realpath(os.path.dirname(__file__))}/config.json") as file:
        config = json.load(file)

"""	
Setup bot intents (events restrictions)
For more information about intents, please go to the following websites:
https://discordpy.readthedocs.io/en/latest/intents.html
https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents


Default Intents:
intents.bans = True
intents.dm_messages = True
intents.dm_reactions = True
intents.dm_typing = True
intents.emojis = True
intents.emojis_and_stickers = True
intents.guild_messages = True
intents.guild_reactions = True
intents.guild_scheduled_events = True
intents.guild_typing = True
intents.guilds = True
intents.integrations = True
intents.invites = True
intents.messages = True # `message_content` is required to get the content of the messages
intents.reactions = True
intents.typing = True
intents.voice_states = True
intents.webhooks = True

Privileged Intents (Needs to be enabled on developer portal of Discord), please use them only if you need them:
intents.members = True
intents.message_content = True
intents.presences = True
"""

intents = discord.Intents.default()
intents.message_content = True

"""
Uncomment this if you want to use prefix (normal) commands.
It is recommended to use slash commands and therefore not use prefix commands.

If you want to use prefix commands, make sure to also enable the intent below in the Discord developer portal.
"""
# intents.message_content = True

bot = Bot(
    command_prefix=commands.when_mentioned_or(config["prefix"]),
    intents=intents,
    help_command=None,
)

# Setup both of the loggers

class LoggingFormatter(logging.Formatter):
    # Colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record):
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(reset)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


logger = logging.getLogger("discord_bot")
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(LoggingFormatter())
# File handler
file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

# Add the handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)
bot.logger = logger


async def init_db():
    # mongodb setting
        
    # sql setting
    async with aiosqlite.connect(
        f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
    ) as db:
        with open(
            f"{os.path.realpath(os.path.dirname(__file__))}/database/schema.sql"
        ) as file:
            await db.executescript(file.read())
        await db.commit()


"""
Create a bot variable to access the config file in cogs so that you don't need to import it every time.

The config is available using the following code:
- bot.config # In this file
- self.bot.config # In cogs
"""
bot.config = config

bot.youtube = utils.YoutubeFeed(logger)
bot.tldr = utils.TLDRFeed()
bot.discourse = utils.ToDiscourse(bot.config)

@bot.event
async def on_ready() -> None:
    """
    The code in this event is executed when the bot is ready.
    """
    bot.logger.info(f"Logged in as {bot.user.name}")
    bot.logger.info(f"discord.py API version: {discord.__version__}")
    bot.logger.info(f"Python version: {platform.python_version()}")
    bot.logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
    bot.logger.info("-------------------")
    
    status_task.start()
    news_feed.start()
    youtube_feed.start()
    tldr_feed.start()
    
    # Insert channel info to DB
    if config["sync_commands_globally"]:
        bot.logger.info("Syncing commands globally...")
        await bot.tree.sync()


@tasks.loop(minutes=1.0)
async def status_task() -> None:
    """
    Setup the game status task of the bot.
    """
    await bot.change_presence(activity=discord.Game("ZzZz"))

@tasks.loop(seconds=1)
async def news_feed():
    now = datetime.now()
    channel = bot.get_channel(1082998215814688829)
    if now.strftime("%H:%M:%S") == "09:00:00":
        feeds = utils.get_investing_finance_news()
        title = f"{now.strftime('%Y-%m-%d')} Stock Market News (Investing)"
        embed = discord.Embed(title=f"{title}")
        for news in feeds:
            embed.add_field(name=news.title, value=news.link, inline=False)
        await channel.send(embed=embed)

@tasks.loop(minutes=2.5)
async def youtube_feed():
    channel = bot.get_channel(1105872936776245349)
    await bot.youtube.get_new_video()
    rows = await helpers.db_manager.get_youtube_video()
    for row in rows:
        await channel.send(row[2])
        await helpers.db_manager.update_youtube_video(row[0], row[1], row[2])
    
@tasks.loop(seconds=1)
async def tldr_feed():
    now = datetime.now()
    channel = bot.get_channel(1110112301106860052)
    if now.strftime("%H:%M:%S") == "09:00:00":
        date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        feeds = await bot.tldr.get_feed(date)
        for field in feeds:
            await channel.send(f"# Daily TLDR {field.upper()} ({date})\n")
            for subject in feeds[field]:
                max_length = int(1024/len(feeds[field][subject]))
                embed = discord.Embed(title=subject)
                for title in feeds[field][subject]:
                    value =  f"{feeds[field][subject][title]['link']}\n{feeds[field][subject][title]['content'][:]}\n\n"
                    if len(value) > max_length:
                        value = value[:max_length-3] + "..."
                    embed.add_field(name=title, value=value, inline=False)
                await channel.send(embed=embed)

@bot.event
async def on_message(message: discord.Message) -> None:
    """
    The code in this event is executed every time someone sends a message, with or without the prefix

    :param message: The message that was sent.
    """
    if message.author == bot.user or message.author.bot:
        if message.channel.name == "💡geek-news":
            bot.discourse.post_geeknews(message)
        else:
            return
    # 모든 로그 수집
    await helpers.db_manager.add_log(**archiving.chat2log(message))
    
    # Github Repository Archiving
    if ("https://github.com/" in message.content):
        await archiving.archive_github(message)
    
    # Paper Archiving 
    if any(paper in message.content for paper in archiving.PaperSource):
        await archiving.archive_paper(message)
    
    await bot.process_commands(message)


@bot.event
async def on_command_completion(context: Context) -> None:
    """
    The code in this event is executed every time a normal command has been *successfully* executed.

    :param context: The context of the command that has been executed.
    """
    full_command_name = context.command.qualified_name
    split = full_command_name.split(" ")
    executed_command = str(split[0])
    if context.guild is not None:
        bot.logger.info(
            f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
        )
    else:
        bot.logger.info(
            f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
        )


@bot.event
async def on_command_error(context: Context, error) -> None:
    """
    The code in this event is executed every time a normal valid command catches an error.

    :param context: The context of the normal command that failed executing.
    :param error: The error that has been faced.
    """
    if isinstance(error, commands.CommandOnCooldown):
        minutes, seconds = divmod(error.retry_after, 60)
        hours, minutes = divmod(minutes, 60)
        hours = hours % 24
        embed = discord.Embed(
            description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
            color=0xE02B2B,
        )
        await context.send(embed=embed)
    elif isinstance(error, exceptions.UserBlacklisted):
        """
        The code here will only execute if the error is an instance of 'UserBlacklisted', which can occur when using
        the @checks.not_blacklisted() check in your command, or you can raise the error by yourself.
        """
        embed = discord.Embed(
            description="You are blacklisted from using the bot!", color=0xE02B2B
        )
        await context.send(embed=embed)
        if context.guild:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried to execute a command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is blacklisted from using the bot."
            )
        else:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried to execute a command in the bot's DMs, but the user is blacklisted from using the bot."
            )
    elif isinstance(error, exceptions.UserNotOwner):
        """
        Same as above, just for the @checks.is_owner() check.
        """
        embed = discord.Embed(
            description="You are not the owner of the bot!", color=0xE02B2B
        )
        await context.send(embed=embed)
        if context.guild:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the guild {context.guild.name} (ID: {context.guild.id}), but the user is not an owner of the bot."
            )
        else:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the bot's DMs, but the user is not an owner of the bot."
            )
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            description="You are missing the permission(s) `"
            + ", ".join(error.missing_permissions)
            + "` to execute this command!",
            color=0xE02B2B,
        )
        await context.send(embed=embed)
    elif isinstance(error, commands.BotMissingPermissions):
        embed = discord.Embed(
            description="I am missing the permission(s) `"
            + ", ".join(error.missing_permissions)
            + "` to fully perform this command!",
            color=0xE02B2B,
        )
        await context.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="Error!",
            # We need to capitalize because the command arguments have no capital letter in the code.
            description=str(error).capitalize(),
            color=0xE02B2B,
        )
        await context.send(embed=embed)
    else:
        raise error

async def load_cogs() -> None:
    """
    The code in this function is executed whenever the bot will start.
    """
    for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
        if file.endswith(".py"):
            extension = file[:-3]
            try:
                await bot.load_extension(f"cogs.{extension}")
                bot.logger.info(f"Loaded extension '{extension}'")
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                bot.logger.error(f"Failed to load extension {extension}\n{exception}")


asyncio.run(init_db())
asyncio.run(load_cogs())
bot.run(config["token"])
