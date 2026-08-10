import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks

# 게이트웨이 주소는 config.json 의 TOKENS.GEMINI.HOST 로 덮어쓸 수 있다.
GEMINI_GATEWAY_DEFAULT = "http://192.168.0.252:8001"
GEMINI_MODEL = "gemini-3.5-flash-lite"
GEMINI_ICON = "https://camo.githubusercontent.com/77ba4ba362fc39151379e4e7691125c8bb130eb2ade811ce9f76d4d5236c6847/68747470733a2f2f75706c6f61642e77696b696d656469612e6f72672f77696b6970656469612f636f6d6d6f6e732f7468756d622f662f66302f476f6f676c655f426172645f6c6f676f2e7376672f3132303070782d476f6f676c655f426172645f6c6f676f2e7376672e706e67"

# Discord 임베드 description 상한. 초과하면 커맨드 전체가 HTTPException 으로 실패한다.
EMBED_DESCRIPTION_LIMIT = 4096
REQUEST_TIMEOUT_SECONDS = 60


class LLM(commands.Cog, name="llm"):
    def __init__(self, bot):
        self.bot = bot
        # 키가 없어도 cog 가 로딩되도록 .get() 으로 방어한다.
        host = (
            bot.config.get("TOKENS", {}).get("GEMINI", {}).get("HOST")
            or GEMINI_GATEWAY_DEFAULT
        )
        self.gateway = host.rstrip("/")

    @commands.hybrid_command(
        name="gemini", description="Gemini에게 물어봅니다! 일회성 질문이에요!"
    )
    @checks.not_blacklisted()
    @app_commands.describe(content="물어볼 내용!")
    async def ask_to_gemini(self, context: Context, *, content: str = ""):
        await context.defer()

        embed = discord.Embed()
        if not content:
            embed.color = discord.Color.red()
            embed.description = "내용을 입력하세요!"
            await context.send(embed=embed)
            return

        try:
            embed.description = await self._generate_content(content)
            embed.color = discord.Color.green()
            embed.set_author(name="Gemini", icon_url=GEMINI_ICON)
        except Exception as e:
            embed.color = discord.Color.red()
            embed.description = "기능 확인이 필요합니다! 운영진에게 알려주세요!"
            self.bot.logger.error(f"{type(e).__name__}: {e}")
        await context.send(embed=embed)

    async def _generate_content(self, content: str) -> str:
        """Gemini Gateway 에 질문을 보내고 답변 텍스트를 돌려준다.

        :param content: 사용자가 물어본 내용
        :return: 임베드에 넣을 수 있도록 길이를 자른 답변 텍스트
        """
        url = f"{self.gateway}/v1beta/models/{GEMINI_MODEL}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": content}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1024},
        }

        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                # 4xx/5xx 본문도 JSON 이라 status 를 먼저 확인하지 않으면
                # 아래 키 접근이 엉뚱한 KeyError 로 바뀐다.
                response.raise_for_status()
                data = await response.json()

        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"candidates 없음: {str(data)[:300]}")

        candidate = candidates[0]
        parts = (candidate.get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            # 안전 필터 차단(SAFETY)이나 토큰 초과(MAX_TOKENS)에서 본문이 비어 온다.
            raise RuntimeError(
                f"본문이 비어 있음 (finishReason={candidate.get('finishReason')})"
            )

        if len(text) > EMBED_DESCRIPTION_LIMIT:
            text = text[: EMBED_DESCRIPTION_LIMIT - 3] + "..."
        return text


async def setup(bot):
    await bot.add_cog(LLM(bot))
