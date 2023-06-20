import typing

import arxiv

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks

class Search(commands.Cog, name="search"):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="아카이브검색", description="arXiv의 논문을 검색합니다")
    @checks.not_blacklisted()
    @app_commands.describe(keyword="검색 할 키워드")
    async def search_arxiv(self, context: Context, *, keyword: str) -> None:
        papers = arxiv.Search(
            query = f"{keyword} AND cat:cs.AI", 
            max_results = 5,
            sort_by = arxiv.SortCriterion.SubmittedDate,
            sort_order = arxiv.SortOrder.Descending
            )
        await context.send(f"**검색 키워드**: {keyword}")
        
        embeds = []
        for paper in papers.results():
            embed = discord.Embed(
                title=f"{paper.title}",
                color=0x9C84EF,
            )
            embed.add_field(name="Authors", value=' '.join(author.name for author in paper.authors), inline=False)    
            embed.add_field(name="Caterogies", value=', '.join(paper.categories), inline=False)    
            embed.add_field(name="Date", value=paper.published, inline=False)    
            embed.add_field(name="Paper Link", value=paper.entry_id, inline=False)
            embeds.append(embed)
        await context.send(embeds=embeds)

    @commands.hybrid_command(name="db검색", description="DB검색",)
    @checks.not_blacklisted()
    @app_commands.describe(subject="논문/깃헙 중 하나를 적어주세요", channel="어떤 채널에서 보셨나요?", teller="누가 얘기했었나요?")
    async def search_in_db(self, context: Context, *,subject: typing.Literal["논문", "깃헙"], channel: str = "", teller: str = "") -> None:
        embed = discord.Embed(
            title="입력 값",
            description=f"{subject}{channel}{teller}",
            color=0x9C84EF,
        )
        embed.set_footer(text=f"{subject}{channel}{teller}")
        await context.send(embed=embed)
# And then we finally add the cog to the bot so that it can load, unload, reload and use it's content.
async def setup(bot):
    await bot.add_cog(Search(bot))
