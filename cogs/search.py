import asyncio
import typing

import arxiv

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks, db_manager

# Discord 임베드 제약. 초과하면 커맨드 전체가 HTTPException 으로 실패한다.
FIELD_NAME_LIMIT = 256
FIELD_VALUE_LIMIT = 1024
MAX_FIELDS = 25

ARXIV_MAX_RESULTS = 5
DB_MAX_RESULTS = 10


def clip(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 3] + "..."


class Search(commands.Cog, name="search"):
    def __init__(self, bot):
        self.bot = bot

    def _fetch_arxiv(self, query: str) -> list:
        """arxiv 라이브러리는 동기 HTTP 를 쓰므로 to_thread 로 감싸 호출한다.

        이벤트 루프에서 직접 부르면 응답이 올 때까지 봇 전체가 멈춘다.
        Search.results() 는 폐기 대상이라 Client.results() 를 쓴다.
        """
        client = arxiv.Client(page_size=ARXIV_MAX_RESULTS, delay_seconds=1, num_retries=2)
        search = arxiv.Search(
            query=query,
            max_results=ARXIV_MAX_RESULTS,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        return list(client.results(search))

    @commands.hybrid_command(name="아카이브검색", description="arXiv의 논문을 검색합니다")
    @checks.not_blacklisted()
    @app_commands.describe(
        keyword="검색 할 키워드",
        category="분야를 좁힐까요? 기본은 전체입니다",
    )
    async def search_arxiv(
        self,
        context: Context,
        category: typing.Literal[
            "전체", "cs.AI", "cs.LG", "cs.CV", "cs.CL", "cs.RO", "stat.ML"
        ] = "전체",
        *,
        keyword: str,
    ) -> None:
        await context.defer()

        # 예전에는 cat:cs.AI 가 하드코딩돼 해당 분야에 교차 등록된 논문만 나왔다.
        query = keyword if category == "전체" else f"{keyword} AND cat:{category}"
        try:
            papers = await asyncio.to_thread(self._fetch_arxiv, query)
        except Exception as e:
            self.bot.logger.error(f"{type(e).__name__}: {e}")
            await context.send(
                embed=discord.Embed(
                    description="arXiv 검색에 실패했어요! 잠시 후 다시 시도해주세요.",
                    color=0xE02B2B,
                )
            )
            return

        if not papers:
            await context.send(
                embed=discord.Embed(
                    description=f"**{keyword}** 에 대한 결과가 없어요!", color=0xE02B2B
                )
            )
            return

        scope = "전체 분야" if category == "전체" else category
        embed = discord.Embed(
            title=f"arXiv 검색: {clip(keyword, 200)}",
            description=f"{scope} · {len(papers)}건",
            color=0x9C84EF,
        )
        for paper in papers[:MAX_FIELDS]:
            authors = ", ".join(a.name for a in paper.authors[:4])
            if len(paper.authors) > 4:
                authors += f" 외 {len(paper.authors) - 4}명"
            body = (
                f"{paper.entry_id}\n"
                f"{authors} · {paper.published:%Y-%m-%d} · {', '.join(paper.categories[:3])}\n"
                f"{paper.summary}"
            )
            embed.add_field(
                name=clip(paper.title, FIELD_NAME_LIMIT),
                value=clip(body, FIELD_VALUE_LIMIT),
                inline=False,
            )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="db검색", description="서버에 공유됐던 논문/저장소를 검색합니다"
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        subject="논문/깃헙 중 하나를 골라주세요",
        keyword="제목이나 설명에 들어갈 말",
        teller="누가 공유했나요?",
        channel="어떤 채널에서 보셨나요?",
    )
    async def search_in_db(
        self,
        context: Context,
        subject: typing.Literal["논문", "깃헙"],
        keyword: str = "",
        teller: discord.User = None,
        channel: str = "",
    ) -> None:
        await context.defer()

        # 표시이름은 바뀌므로 Discord ID 로 찾는다. 슬래시 커맨드에서는
        # teller 가 자동완성되고, 이름을 바꾼 사용자도 한 번에 잡힌다.
        author_id = str(teller.id) if teller else ""

        embed = discord.Embed(title=f"{subject} 검색 결과", color=0x9C84EF)
        conditions = []
        if keyword:
            conditions.append(f"키워드 `{clip(keyword, 60)}`")
        if teller:
            conditions.append(f"공유자 {teller.mention}")
        if channel:
            conditions.append(f"채널 `{clip(channel, 40)}`")
        embed.description = " · ".join(conditions) if conditions else "최근 공유된 순서"

        if subject == "논문":
            rows = await db_manager.search_paper(
                keyword=keyword, author_id=author_id, channel_name=channel,
                limit=DB_MAX_RESULTS,
            )
            for row in rows:
                # (0:title, 1:url, 2:authors, 3:source, 4:year, 5:message_author, 6:created_at)
                embed.add_field(
                    name=clip(row[0], FIELD_NAME_LIMIT),
                    value=clip(
                        f"{row[1]}\n{row[4]} · {row[3]} · {row[5]} 공유 ({row[6][:10]})",
                        FIELD_VALUE_LIMIT,
                    ),
                    inline=False,
                )
        else:
            rows = await db_manager.search_github(
                keyword=keyword, author_id=author_id, channel_name=channel,
                limit=DB_MAX_RESULTS,
            )
            for row in rows:
                # (0:github_username, 1:repository_name, 2:description, 3:message_author, 4:created_at)
                embed.add_field(
                    name=clip(f"{row[0]}/{row[1]}", FIELD_NAME_LIMIT),
                    value=clip(
                        f"https://github.com/{row[0]}/{row[1]}\n"
                        f"{row[2]}\n{row[3]} 공유 ({row[4][:10]})",
                        FIELD_VALUE_LIMIT,
                    ),
                    inline=False,
                )

        if not rows:
            embed.color = 0xE02B2B
            embed.description += "\n\n조건에 맞는 기록이 없어요!"
        await context.send(embed=embed)


# And then we finally add the cog to the bot so that it can load, unload, reload and use it's content.
async def setup(bot):
    await bot.add_cog(Search(bot))
