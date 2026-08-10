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


async def add_warn(user_id: int, server_id: int, moderator_id: int, reason: str) -> tuple:
    """
    This function will add a warn to the database.

    :param user_id: The ID of the user that should be warned.
    :param reason: The reason why the user should be warned.
    :return: (warn_id, total) — 새 경고의 ID와 해당 유저의 총 경고 수.
             경고를 삭제한 이력이 있으면 두 값이 갈라지므로 함께 돌려준다.
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
            async with db.execute(
                "SELECT COUNT(*) FROM warns WHERE user_id=? AND server_id=?",
                (user_id, server_id),
            ) as count_cursor:
                total = await count_cursor.fetchone()
            return warn_id, (total[0] if total is not None else 0)


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

async def prune_logs(days: int) -> int:
    """
    보존 기간이 지난 대화 로그를 삭제한다. 운영자가 명시적으로 호출한다.

    :param days: 보관할 일수. 이보다 오래된 log 행을 지운다.
    :return: 삭제된 행 수
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM log WHERE created_at < datetime('now', ?)",
            (f"-{int(days)} days",),
        )
        await db.commit()
        return cursor.rowcount


async def prune_sent_youtube_videos(days: int) -> int:
    """
    이미 전송한 오래된 유튜브 영상 기록을 삭제한다.

    :param days: 보관할 일수
    :return: 삭제된 행 수
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM youtube_video WHERE send!=0 AND created_at < datetime('now', ?)",
            (f"-{int(days)} days",),
        )
        await db.commit()
        return cursor.rowcount


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
                        github_username: str, repository_name: str, description: str) -> tuple:
    """
    아카이브에 저장소를 추가한다.

    :return: (added, original) — add_paper 와 같은 규약.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT message_author, created_at FROM github WHERE github_username=? AND repository_name=?",
            (github_username, repository_name),
        ) as cursor:
            existing = await cursor.fetchone()
        if existing is not None:
            return False, existing

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
                description,
            ),
        )
        await db.commit()
        return True, None

async def add_paper(channel_name: str, channel_id: int, message_author: str, message_author_id: int,
                        source: str, title: str, authors: str, url: str, conference: str, year: str,
                        abstract: str = "") -> tuple:
    """
    아카이브에 논문을 추가한다.

    :return: (added, original) — added 는 새로 넣었는지 여부.
             이미 있으면 original 은 (message_author, created_at), 없으면 None.
             호출부가 중복을 사용자에게 안내할 수 있도록 원본 정보를 함께 돌려준다.
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT message_author, created_at FROM paper WHERE title=? AND authors=?",
            (title, authors),
        ) as cursor:
            existing = await cursor.fetchone()
        if existing is not None:
            return False, existing

        await db.execute(
            "INSERT INTO paper(channel_name, channel_id, message_author, message_author_id, source, title, authors, url, conference, year, abstract) \
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                year,
                abstract,
            ),
        )
        await db.commit()
        return True, None

# About YouTube
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

async def del_youtube_channel_info(channel_name: str) -> None:
    """
    This function will add a evry chat log to the database.
    """
    # DB 내 동일 정보 확인 필요 
    # Fetch DB
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM youtube_channel WHERE channel_name=?", (channel_name,))
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

# About DB search
#
# 조회 함수는 SELECT * 를 쓰지 않는다. 컬럼을 명시하면 반환 인덱스가
# SELECT 절 순서를 따르므로, 스키마에 컬럼이 추가돼도 호출부가 밀리지 않는다.
#
# 작성자 필터는 표시이름(message_author)이 아니라 message_author_id 를 쓴다.
# 표시이름은 바뀐다 — 실제로 최다 기여자를 포함해 3명이 두 이름으로 쪼개져 있다.


async def search_paper(
    keyword: str = "", author_id: str = "", channel_name: str = "", limit: int = 10
) -> list:
    """아카이브된 논문을 검색한다.

    :param keyword: 제목·저자에 대한 부분 일치
    :param author_id: 공유한 사람의 Discord ID (표시이름이 아님)
    :param channel_name: 공유된 채널명
    :return: list[tuple] — (0:title, 1:url, 2:authors, 3:source, 4:year,
             5:message_author, 6:created_at)
    """
    clauses, values = [], []
    if keyword:
        clauses.append("(title LIKE ? OR authors LIKE ?)")
        values += [f"%{keyword}%", f"%{keyword}%"]
    if author_id:
        clauses.append("message_author_id=?")
        values.append(str(author_id))
    if channel_name:
        clauses.append("channel_name=?")
        values.append(channel_name)
    where = " AND ".join(clauses) if clauses else "1=1"

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            f"SELECT title, url, authors, source, year, message_author, created_at "
            f"FROM paper WHERE {where} ORDER BY created_at DESC LIMIT ?",
            (*values, limit),
        ) as cursor:
            return await cursor.fetchall()


async def recent_archives(days: int = 7) -> dict:
    """최근 N일간 아카이브된 논문·저장소와 기여자를 모은다. 주간 다이제스트용.

    :return: {"papers": [(title, url, message_author)],
              "repos": [(github_username, repository_name, message_author)],
              "contributors": [(message_author, count)]}
    """
    window = f"-{int(days)} days"
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            "SELECT title, url, message_author FROM paper "
            "WHERE created_at >= datetime('now', ?) ORDER BY created_at DESC",
            (window,),
        ) as cursor:
            papers = await cursor.fetchall()

        async with db.execute(
            "SELECT github_username, repository_name, message_author FROM github "
            "WHERE created_at >= datetime('now', ?) ORDER BY created_at DESC",
            (window,),
        ) as cursor:
            repos = await cursor.fetchall()

        async with db.execute(
            "SELECT message_author, COUNT(*) c FROM ("
            "  SELECT message_author FROM paper WHERE created_at >= datetime('now', ?)"
            "  UNION ALL"
            "  SELECT message_author FROM github WHERE created_at >= datetime('now', ?)"
            ") GROUP BY 1 ORDER BY c DESC",
            (window, window),
        ) as cursor:
            contributors = await cursor.fetchall()

    return {"papers": papers, "repos": repos, "contributors": contributors}


async def search_github(
    keyword: str = "", author_id: str = "", channel_name: str = "", limit: int = 10
) -> list:
    """아카이브된 저장소를 검색한다.

    :param keyword: 저장소명·설명에 대한 부분 일치
    :param author_id: 공유한 사람의 Discord ID (표시이름이 아님)
    :return: list[tuple] — (0:github_username, 1:repository_name, 2:description,
             3:message_author, 4:created_at)
    """
    clauses, values = [], []
    if keyword:
        clauses.append("(repository_name LIKE ? OR description LIKE ?)")
        values += [f"%{keyword}%", f"%{keyword}%"]
    if author_id:
        clauses.append("message_author_id=?")
        values.append(str(author_id))
    if channel_name:
        clauses.append("channel_name=?")
        values.append(channel_name)
    where = " AND ".join(clauses) if clauses else "1=1"

    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute(
            f"SELECT github_username, repository_name, description, message_author, created_at "
            f"FROM github WHERE {where} ORDER BY created_at DESC LIMIT ?",
            (*values, limit),
        ) as cursor:
            return await cursor.fetchall()