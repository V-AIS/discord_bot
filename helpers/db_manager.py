""""
Copyright © Krypton 2019-2023 - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 5.5.0
"""

# mongo db로 수정?
import os
import aiosqlite

DATABASE_PATH = f"{os.path.realpath(os.path.dirname(__file__))}/../database/database.db"


async def get_blacklisted_users() -> list:
    """
    This function will return the list of all blacklisted users.

    :param user_id: The ID of the user that should be checked.
    :return: True if the user is blacklisted, False if not.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT user_id, strftime('%s', created_at) FROM blacklist") as cursor:
            result = await cursor.fetchall()
            return result


async def is_blacklisted(user_id: int) -> bool:
    """
    This function will check if a user is blacklisted.

    :param user_id: The ID of the user that should be checked.
    :return: True if the user is blacklisted, False if not.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT * FROM blacklist WHERE user_id=?", (user_id,)
        ) as cursor:
            result = await cursor.fetchone()
            return result is not None


async def add_user_to_blacklist(user_id: int) -> int:
    """
    This function will add a user based on its ID in the blacklist.

    :param user_id: The ID of the user that should be added into the blacklist.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("INSERT INTO blacklist(user_id) VALUES (?)", (user_id,))
        await db.commit()
        rows = await db.execute("SELECT COUNT(*) FROM blacklist")
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0


async def remove_user_from_blacklist(user_id: int) -> int:
    """
    This function will remove a user based on its ID from the blacklist.

    :param user_id: The ID of the user that should be removed from the blacklist.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM blacklist WHERE user_id=?", (user_id,))
        await db.commit()
        rows = await db.execute("SELECT COUNT(*) FROM blacklist")
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0


async def add_warn(user_id: int, server_id: int, moderator_id: int, reason: str) -> int:
    """
    This function will add a warn to the database.

    :param user_id: The ID of the user that should be warned.
    :param reason: The reason why the user should be warned.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT id FROM warns WHERE user_id=? AND server_id=? ORDER BY id DESC LIMIT 1",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            warn_id = result[0] + 1 if result is not None else 1
            await db.execute(
                "INSERT INTO warns(id, user_id, server_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
                (
                    warn_id,
                    user_id,
                    server_id,
                    moderator_id,
                    reason,
                ),
            )
            await db.commit()
            return warn_id


async def remove_warn(warn_id: int, user_id: int, server_id: int) -> int:
    """
    This function will remove a warn from the database.

    :param warn_id: The ID of the warn.
    :param user_id: The ID of the user that was warned.
    :param server_id: The ID of the server where the user has been warned
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "DELETE FROM warns WHERE id=? AND user_id=? AND server_id=?",
            (
                warn_id,
                user_id,
                server_id,
            ),
        )
        await db.commit()
        rows = await db.execute(
            "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchone()
            return result[0] if result is not None else 0


async def get_warnings(user_id: int, server_id: int) -> list:
    """
    This function will get all the warnings of a user.

    :param user_id: The ID of the user that should be checked.
    :param server_id: The ID of the server that should be checked.
    :return: A list of all the warnings of the user.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT user_id, server_id, moderator_id, reason, strftime('%s', created_at), id FROM warns WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            result_list = []
            for row in result:
                result_list.append(row)
            return result_list

async def add_discord_channel_info(channel_name: str, channel_id: int) -> None:
    """
    This function will add a evry chat log to the database.
    """
    # DB 내 동일 정보 확인 필요 
    # Fetch DB
    
    # IF not in DB
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT channel_name, channel_id \
                FROM channel_list WHERE channel_id=?",
            ( 
                channel_id, 
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
        if not len(result):
            await db.execute(
                "INSERT INTO channel_list(channel_name, channel_id) \
                    VALUES (?, ?)",
                (
                    channel_name,
                    channel_id
                ),
            )
            await db.commit()
        else:
            await db.execute(
                "UPDATE channel_list \
                    SET channel_name= ? \
                        WHERE channel_id=?",
                (
                    channel_name,
                    channel_id
                ),
            ) 
            await db.commit()
        return 

async def add_log(channel_name: str, channel_id: int, message_author: str, message_author_id: int, message_content: str) -> None:
    """
    This function will add a evry chat log to the database.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO log(channel_name, channel_id, message_author, message_author_id, message_content) \
                VALUES (?, ?, ?, ?, ?)",
            (
                channel_name,
                channel_id,
                message_author,
                message_author_id,
                message_content,
            ),
        )
        await db.commit()
        return 

async def add_github(channel_name: str, channel_id: int, message_author: str, message_author_id: int, 
                        github_username: str, repository_name: str, description: str) -> None:
    """
    This function will add a evry chat log to the database.
    """
    # DB 내 동일 정보 확인 필요 
    # Fetch DB
    
    # IF not in DB
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT channel_name, channel_id, message_author, message_author_id, github_username, repository_name, description \
                FROM github WHERE github_username=? AND repository_name=?",
            (
                github_username, 
                repository_name, 
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
        if not len(result):
            await db.execute(
                "INSERT INTO github(channel_name, channel_id, message_author, message_author_id, github_username, repository_name, description) \
                    VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    channel_name,
                    channel_id,
                    message_author,
                    message_author_id,
                    github_username, 
                    repository_name,
                    description
                ),
            )
            await db.commit()
        return 

async def add_paper(channel_name: str, channel_id: int, message_author: str, message_author_id: int, 
                        source: str, title: str, authors: str, url: str, conference: str, year: str) -> None:
    """
    This function will add a evry chat log to the database.
    """
    # DB 내 동일 정보 확인 필요 
    # Fetch DB
    
    # IF not in DB
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT channel_name, channel_id, message_author, message_author_id, source, title, authors, url, conference, year \
                FROM paper WHERE title=? AND authors=?",
            (
                title, 
                authors, 
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
        if not len(result):
            await db.execute(
                "INSERT INTO paper(channel_name, channel_id, message_author, message_author_id, source, title, authors, url, conference, year) \
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    channel_name,
                    channel_id,
                    message_author,
                    message_author_id,
                    source, 
                    title,
                    authors,
                    url,
                    conference,
                    year
                ),
            )
            await db.commit()
        return 

async def get_youtube_channel_info() -> list:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT channel_name, rss_link FROM youtube_channel") as cursor:
            result = await cursor.fetchall()
            return result

async def add_youtube_channel_info(channel_name: str, rss_link: str) -> None:
    """
    This function will add a evry chat log to the database.
    """
    # DB 내 동일 정보 확인 필요 
    # Fetch DB
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT channel_name, rss_link \
                FROM youtube_channel WHERE channel_name=?",
            (
                channel_name, 
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
        if not len(result):
            await db.execute(
                "INSERT INTO youtube_channel(channel_name, rss_link) \
                    VALUES (?, ?)",
                (
                    channel_name,
                    rss_link
                ),
            )
            await db.commit()
        return

async def add_youtube_video(channel_name: str, video_id: int, video_link: str, published: str) -> None:
    # DB 내 동일 정보 확인 필요 
    # Fetch DB
    
    # IF not in DB
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT channel_name, video_id, video_link, published, send \
                FROM youtube_video WHERE channel_name=? AND video_id=? AND video_link=?",
            (
                channel_name, 
                video_id, 
                video_link,
            ),
        )
        async with rows as cursor:
            result = await cursor.fetchall()
        if not len(result):
            await db.execute(
                "INSERT INTO youtube_video(channel_name, video_id, video_link, published, send) \
                    VALUES (?, ?, ?, ?, ?)",
                (
                    channel_name,
                    video_id,
                    video_link,
                    published,
                    False
                ),
            )
            await db.commit()
        return 

async def get_youtube_video():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        rows = await db.execute(
            "SELECT channel_name, video_id, video_link \
                FROM youtube_video \
                    WHERE send=0"
        )
        async with rows as cursor:
            result = await cursor.fetchall()
            return result
async def update_youtube_video(channel_name: str, video_id: int, video_link: str) -> None:
    # DB 내 동일 정보 확인 필요 
    # Fetch DB
    
    # IF not in DB
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE youtube_video \
                SET send= True \
                    WHERE channel_name=? AND video_id=? AND video_link=?",
            (
                channel_name,
                video_id,
                video_link
            ),
        ) 
        await db.commit()
        return 

if __name__ == "__main__":
    import asyncio
    rows = asyncio.run(get_youtube_video())
    for row in rows[:-2]:
        print(row[0], row[1], row[2])
        asyncio.run(update_youtube_video(row[0], row[1], row[2]))