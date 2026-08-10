import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks, gemini

GEMINI_ICON = "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1d/Google_Gemini_icon_2025.svg/250px-Google_Gemini_icon_2025.svg.png"

# Discord 임베드 description 상한. 초과하면 커맨드 전체가 HTTPException 으로 실패한다.
EMBED_DESCRIPTION_LIMIT = 4096


class LLM(commands.Cog, name="llm"):
    def __init__(self, bot):
        self.bot = bot
        # 키가 없어도 cog 가 로딩되도록 방어한다. 미설정이면 커맨드 실행 시점에 안내한다.
        self.gateway = gemini.gateway_from(bot.config)

    @commands.hybrid_command(
        name="gemini", description="Gemini에게 물어봅니다! 일회성 질문이에요!"
    )
    @checks.not_blacklisted()
    @app_commands.describe(content="물어볼 내용!")
    async def ask_to_gemini(self, context: Context, *, content: str = ""):
        await context.defer()

        embed = discord.Embed()
        if not self.gateway:
            embed.color = discord.Color.red()
            embed.description = "Gemini 설정이 아직 없어요! 운영진에게 알려주세요!"
            self.bot.logger.error("TOKENS.GOOGLE.HOST 가 config.json 에 없습니다")
            await context.send(embed=embed)
            return

        if not content:
            embed.color = discord.Color.red()
            embed.description = "내용을 입력하세요!"
            await context.send(embed=embed)
            return

        try:
            answer = await gemini.generate(self.gateway, content)
            if len(answer) > EMBED_DESCRIPTION_LIMIT:
                answer = answer[: EMBED_DESCRIPTION_LIMIT - 3] + "..."
            embed.description = answer
            embed.color = discord.Color.green()
            embed.set_author(name="Gemini", icon_url=GEMINI_ICON)
        except Exception as e:
            embed.color = discord.Color.red()
            embed.description = "기능 확인이 필요합니다! 운영진에게 알려주세요!"
            self.bot.logger.error(f"{type(e).__name__}: {e}")
        await context.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LLM(bot))
