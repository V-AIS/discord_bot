"""
Copyright © Krypton 2019-2023 - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 5.5.0
"""

import asyncio
import traceback
import json
import logging
import os
import platform
import sys
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# 컨테이너는 TZ=Asia/Seoul 로 뜨지만, 명시적 tzinfo 가 있어야
# 로컬 실행과 컨테이너 실행의 스케줄이 일치한다.
KST = ZoneInfo("Asia/Seoul")

import aiosqlite
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context

import exceptions
import archiving
import helpers
import helpers.db_manager
import helpers.gemini
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

bot = Bot(
    command_prefix=commands.when_mentioned_or(config["PREFIX"]),
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
# 신규 clone 에는 logs/ 가 없다. 없는 디렉터리에 FileHandler 를 만들면
# 모듈 최상위에서 FileNotFoundError 로 봇이 기동하지 못한다.
LOG_DIR = f"{os.path.realpath(os.path.dirname(__file__))}/logs"
os.makedirs(LOG_DIR, exist_ok=True)
file_handler = logging.FileHandler(
    filename=f"{LOG_DIR}/discord.log",
    encoding="utf-8",
    mode="w",
)
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

# Add the handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)
bot.logger = logger


# 이미 존재하는 DB 에는 CREATE TABLE IF NOT EXISTS 가 아무 일도 하지 않는다.
# 신규 컬럼은 여기에 등록해 ALTER TABLE 로 따로 반영한다.
# ALTER TABLE 은 컬럼을 맨 뒤에 붙이므로, 신규 DB 와 기존 DB 의 물리적 컬럼
# 순서가 달라진다. 그래서 조회는 SELECT * 대신 컬럼을 명시해야 한다.
MIGRATIONS = [
    ("paper", "abstract", "ALTER TABLE paper ADD COLUMN abstract text NOT NULL DEFAULT ''"),
]


async def init_db():
    async with aiosqlite.connect(
        f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
    ) as db:
        with open(
            f"{os.path.realpath(os.path.dirname(__file__))}/database/schema.sql"
        ) as file:
            await db.executescript(file.read())

        for table, column, statement in MIGRATIONS:
            async with db.execute(f"PRAGMA table_info({table})") as cursor:
                columns = {row[1] for row in await cursor.fetchall()}
            if column not in columns:
                await db.execute(statement)
                logger.info(f"Migrated: {table}.{column} 컬럼 추가")

        await db.commit()


"""
Create a bot variable to access the config file in cogs so that you don't need to import it every time.

The config is available using the following code:
- bot.config # In this file
- self.bot.config # In cogs
"""
bot.config = config

# bot.youtube 는 생성자에서 DB를 읽으므로 init_db() 이후에 만든다.
# 파일 하단의 부트스트랩 구간을 볼 것.
bot.youtube = None
bot.tldr = None


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
    weekly_digest.start()
    
    # Insert channel info to DB
    if bot.config["SYNC_COMMANDS_GLOBALLY"]:
        bot.logger.info("Syncing commands globally...")
        await bot.tree.sync()


HEARTBEAT_DIR = "/tmp/bot_heartbeat"


def beat(name: str) -> None:
    """태스크가 살아있음을 파일 mtime 으로 남긴다. HEALTHCHECK 가 이 값을 본다."""
    try:
        os.makedirs(HEARTBEAT_DIR, exist_ok=True)
        with open(f"{HEARTBEAT_DIR}/{name}", "w") as f:
            f.write(datetime.now(KST).isoformat())
    except Exception:
        bot.logger.error(str(traceback.format_exc()))


@tasks.loop(minutes=1.0)
async def status_task() -> None:
    """
    Setup the game status task of the bot.
    """
    try:
        await bot.change_presence(activity=discord.Game("ZzZz"))
        beat("status")
    except Exception:
        # 예외가 새어나가면 루프가 영구 정지하고 봇은 정상으로 보인다.
        bot.logger.error(str(traceback.format_exc()))


@tasks.loop(time=time(hour=9, minute=0, tzinfo=KST))
async def news_feed():
    now = datetime.now(KST)
    channel = bot.get_channel(bot.config["FEED_CHANNEL"]["NEWS"])
    if channel is None:
        bot.logger.error("news_feed: FEED_CHANNEL.NEWS 채널을 찾을 수 없습니다")
        return
    bot.logger.info("Stock Market News Feed")
    try:
        feeds = utils.get_investing_finance_news()
        title = f"{now.strftime('%Y-%m-%d')} Stock Market News (Investing)"
        embed = discord.Embed(title=f"{title}")
        for news in feeds[:25]:
            embed.add_field(name=news.title[:256], value=news.link[:1024], inline=False)
        await channel.send(embed=embed)
    except Exception:
        bot.logger.error(str(traceback.format_exc()))


@tasks.loop(minutes=2.5)
async def youtube_feed():
    channel = bot.get_channel(bot.config["FEED_CHANNEL"]["YOUTUBE"])
    if channel is None:
        bot.logger.error("youtube_feed: FEED_CHANNEL.YOUTUBE 채널을 찾을 수 없습니다")
        return
    try:
        await bot.youtube.get_new_video()
        rows = await helpers.db_manager.get_youtube_video()
        if len(rows):
            bot.logger.info(f"Youtube FeedFeed (Number of new video: {len(rows)})")
        for row in rows:
            await channel.send(row[2])
            await helpers.db_manager.update_youtube_video(row[0], row[1], row[2])
        beat("youtube")
    except Exception:
        bot.logger.error(str(traceback.format_exc()))
        
@tasks.loop(time=time(hour=10, minute=0, tzinfo=KST))
async def tldr_feed():
    now = datetime.now(KST)
    weekday = now.weekday()
    channel = bot.get_channel(bot.config["FEED_CHANNEL"]["TLDR"])
    if channel is None:
        bot.logger.error("tldr_feed: FEED_CHANNEL.TLDR 채널을 찾을 수 없습니다")
        return
    if weekday not in [0, 6]:
        bot.logger.info("TLDR Feed")
        try:
            date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            feeds = await bot.tldr.get_feed(date)
            for field in feeds:
                await channel.send(f"# Daily TLDR {field.upper()} ({date})\n")
                for subject in feeds[field]:
                    if subject == "TLDR": continue
                    divider = len(feeds[field][subject]) if len(feeds[field][subject]) else 1
                    max_length = int(1024/divider)
                    embed = discord.Embed(title=subject)
                    for title in feeds[field][subject]:
                        value =  f"{feeds[field][subject][title]['link']}\n{feeds[field][subject][title]['content'][:]}\n\n"
                        if len(value) > max_length:
                            value = value[:max_length-3] + "..."
                        embed.add_field(name=title, value=value, inline=False)
                    await channel.send(embed=embed)
        except Exception as e:
            bot.logger.error(str(traceback.format_exc()))

ARCHIVE_REACTION = {"paper": "📚", "github": "🔖"}
ARCHIVE_LABEL = {"paper": "논문", "github": "저장소"}

SUMMARY_PROMPT = (
    "다음은 학술 논문의 초록입니다. 한국어로 3문장 이내로 요약하세요.\n"
    "무엇을 푸는 연구인지, 어떤 방법을 쓰는지, 결과가 무엇인지 순으로 쓰세요.\n"
    "서론이나 인사말 없이 요약만 출력하세요.\n\n초록:\n{abstract}"
)
SUMMARY_MAX_CHARS = 900


def utils_clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


async def summarize_abstract(abstract: str) -> str:
    """초록을 한국어로 요약한다. 실패하면 빈 문자열 — 아카이빙 자체는 막지 않는다."""
    if not abstract:
        return ""
    gateway = helpers.gemini.gateway_from(bot.config)
    if not gateway:
        return ""
    try:
        text = await helpers.gemini.generate(
            gateway, SUMMARY_PROMPT.format(abstract=abstract[:6000]), max_output_tokens=512
        )
        return utils_clip(text, SUMMARY_MAX_CHARS)
    except Exception as e:
        bot.logger.error(f"요약 실패: {type(e).__name__}: {e}")
        return ""


async def announce_archive(message: discord.Message, result: dict) -> None:
    """아카이빙 결과를 사용자에게 알린다.

    지금까지는 조용히 DB 에만 넣어서, 사용자는 기능이 동작하는지 알 수 없었다.
    반응이 없는 기능은 잊힌다 — 실제로 2024년부터 아카이빙 사용이 끊겼다.
    """
    kind = result["kind"]
    try:
        if result["added"]:
            await message.add_reaction(ARCHIVE_REACTION[kind])
            summary = await summarize_abstract(result.get("abstract", ""))
            if summary:
                embed = discord.Embed(
                    title=utils_clip(result["title"], 256),
                    description=summary,
                    color=0x9C84EF,
                )
                embed.set_footer(text="Gemini 요약 · 원문을 꼭 확인하세요")
                await message.reply(embed=embed, mention_author=False)
        else:
            author, when = result["original"]
            await message.reply(
                f"이미 공유된 {ARCHIVE_LABEL[kind]}예요! **{author}** 님이 {when[:10]} 에 올렸어요.",
                mention_author=False,
            )
    except discord.HTTPException:
        # 리액션/답장 권한이 없거나 길이 제한에 걸린 경우. 아카이빙 자체는 성공했다.
        bot.logger.error(str(traceback.format_exc()))


@bot.event
async def on_message(message: discord.Message) -> None:
    """
    The code in this event is executed every time someone sends a message, with or without the prefix

    :param message: The message that was sent.
    """
    if message.author == bot.user or message.author.bot:
        return

    # 아카이빙에서 예외가 새어나가면 아래 process_commands 가 실행되지 않아
    # 해당 메시지의 커맨드가 통째로 무시된다. 반드시 격리한다.
    try:
        # 모든 로그 수집
        await helpers.db_manager.add_log(**archiving.chat2log(message))

        results = []
        # Github Repository Archiving
        if "https://github.com/" in message.content:
            results.append(await archiving.archive_github(message))

        # Paper Archiving
        if any(paper in message.content for paper in archiving.PaperSource):
            results.append(await archiving.archive_paper(message))

        for result in results:
            if result:
                await announce_archive(message, result)
    except Exception:
        bot.logger.error(str(traceback.format_exc()))

    await bot.process_commands(message)


@tasks.loop(time=time(hour=10, minute=30, tzinfo=KST))
async def weekly_digest():
    """지난 주 아카이브를 한 번에 돌려준다.

    122건을 모으고도 되돌려주는 경로가 없어 아카이브가 사실상 잠겨 있었다.
    월요일에만 실행한다 — tasks.loop(time=) 는 매일 깨어나므로 요일을 본다.
    """
    if datetime.now(KST).weekday() != 0:
        return

    channel_id = bot.config["FEED_CHANNEL"].get("DIGEST") or bot.config["FEED_CHANNEL"]["NEWS"]
    channel = bot.get_channel(channel_id)
    if channel is None:
        bot.logger.error("weekly_digest: 다이제스트 채널을 찾을 수 없습니다")
        return

    try:
        data = await helpers.db_manager.recent_archives(days=7)
        if not data["papers"] and not data["repos"]:
            bot.logger.info("Weekly digest: 지난 주 아카이브 없음, 발송 생략")
            return

        embed = discord.Embed(
            title="📚 이번 주 공유된 것들",
            description=f"지난 7일 · 논문 {len(data['papers'])}건 · 저장소 {len(data['repos'])}건",
            color=0x9C84EF,
        )
        for title, url, author in data["papers"][:10]:
            embed.add_field(
                name=utils_clip(title, 256),
                value=utils_clip(f"{url}\n{author} 공유", 1024),
                inline=False,
            )
        for owner, repo, author in data["repos"][:10]:
            embed.add_field(
                name=utils_clip(f"{owner}/{repo}", 256),
                value=utils_clip(f"https://github.com/{owner}/{repo}\n{author} 공유", 1024),
                inline=False,
            )
        if data["contributors"]:
            credit = ", ".join(f"{name} ({count})" for name, count in data["contributors"][:8])
            embed.set_footer(text=utils_clip(f"고마워요: {credit}", 2048))

        await channel.send(embed=embed)
        bot.logger.info(f"Weekly digest 발송 (논문 {len(data['papers'])} 저장소 {len(data['repos'])})")
    except Exception:
        bot.logger.error(str(traceback.format_exc()))


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
        embed = discord.Embed(
            title="Error!",
            color=0xE02B2B,
        )
        await context.send(embed=embed)
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

# 스키마가 만들어진 뒤에 피드 객체를 만든다. YoutubeFeed 는 생성자에서
# youtube_channel 테이블을 읽기 때문에, 순서가 바뀌면 신규 배포(테이블 없음)에서
# "no such table" 로 봇이 기동하지 못한다.
bot.youtube = utils.YoutubeFeed(logger)
asyncio.run(bot.youtube.load())
bot.tldr = utils.TLDRFeed()

asyncio.run(load_cogs())
bot.run(bot.config["TOKEN"])
