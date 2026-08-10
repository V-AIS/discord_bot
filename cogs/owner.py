""""
Copyright © Krypton 2019-2023 - https://github.com/kkrypt0nn (https://krypton.ninja)
Description:
🐍 A simple template to start to code your own and personalized discord bot in Python programming language.

Version: 5.5.0
"""
import typing
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks, db_manager


class Owner(commands.Cog, name="owner"):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="sync", description="Synchonizes the slash commands.",)
    @app_commands.describe(scope="The scope of the sync. Can be `global` or `guild`")
    @checks.is_owner()
    async def sync(self, context: Context, scope: str) -> None:
        """
        Synchonizes the slash commands.

        :param context: The command context.
        :param scope: The scope of the sync. Can be `global` or `guild`.
        """

        if scope == "global":
            await context.bot.tree.sync()
            embed = discord.Embed(
                description="Slash commands have been globally synchronized.",
                color=0x9C84EF,
            )
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.copy_global_to(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(
                description="Slash commands have been synchronized in this guild.",
                color=0x9C84EF,
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description="The scope must be `global` or `guild`.", color=0xE02B2B
        )
        await context.send(embed=embed)

    @commands.hybrid_command(name="unsync", description="Unsynchonizes the slash commands.",)
    @app_commands.describe(scope="The scope of the sync. Can be `global`, `current_guild` or `guild`")
    @checks.is_owner()
    async def unsync(self, context: Context, scope: str) -> None:
        """
        Unsynchonizes the slash commands.

        :param context: The command context.
        :param scope: The scope of the sync. Can be `global`, `current_guild` or `guild`.
        """

        if scope == "global":
            context.bot.tree.clear_commands(guild=None)
            await context.bot.tree.sync()
            embed = discord.Embed(
                description="Slash commands have been globally unsynchronized.",
                color=0x9C84EF,
            )
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.clear_commands(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(
                description="Slash commands have been unsynchronized in this guild.",
                color=0x9C84EF,
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description="The scope must be `global` or `guild`.", color=0xE02B2B
        )
        await context.send(embed=embed)

    @commands.hybrid_command(name="load",description="Load a cog",)
    @app_commands.describe(cog="The name of the cog to load")
    @checks.is_owner()
    async def load(self, context: Context, cog: str) -> None:
        """
        The bot will load the given cog.

        :param context: The hybrid command context.
        :param cog: The name of the cog to load.
        """
        try:
            await self.bot.load_extension(f"cogs.{cog}")
        except Exception:
            embed = discord.Embed(
                description=f"Could not load the `{cog}` cog.", color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"Successfully loaded the `{cog}` cog.", color=0x9C84EF
        )
        await context.send(embed=embed)

    @commands.hybrid_command(name="unload",description="Unloads a cog.",)
    @app_commands.describe(cog="The name of the cog to unload")
    @checks.is_owner()
    async def unload(self, context: Context, cog: str) -> None:
        """
        The bot will unload the given cog.

        :param context: The hybrid command context.
        :param cog: The name of the cog to unload.
        """
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
        except Exception:
            embed = discord.Embed(
                description=f"Could not unload the `{cog}` cog.", color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"Successfully unloaded the `{cog}` cog.", color=0x9C84EF
        )
        await context.send(embed=embed)

    @commands.hybrid_command(name="reload",description="Reloads a cog.",)
    @app_commands.describe(cog="The name of the cog to reload")
    @checks.is_owner()
    async def reload(self, context: Context, cog: str) -> None:
        """
        The bot will reload the given cog.

        :param context: The hybrid command context.
        :param cog: The name of the cog to reload.
        """
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
        except Exception as e:
            embed = discord.Embed(
                description=f"Could not reload the `{cog}` cog. \n\n{e}", color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"Successfully reloaded the `{cog}` cog.", color=0x9C84EF
        )
        await context.send(embed=embed)

    @commands.hybrid_command(name="shutdown",description="Make the bot shutdown.",)
    @checks.is_owner()
    async def shutdown(self, context: Context) -> None:
        """
        Shuts down the bot.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(description="Shutting down. Bye! :wave:", color=0x9C84EF)
        await context.send(embed=embed)
        await self.bot.close()

    @commands.hybrid_command(name="say",description="The bot will say anything you want.",)
    @app_commands.describe(message="The message that should be repeated by the bot")
    @checks.is_owner()
    async def say(self, context: Context, *, message: str) -> None:
        """
        The bot will say anything you want.

        :param context: The hybrid command context.
        :param message: The message that should be repeated by the bot.
        """
        await context.send(message)

    @commands.hybrid_command(name="embed",description="The bot will say anything you want, but within embeds.",)
    @app_commands.describe(message="The message that should be repeated by the bot")
    @checks.is_owner()
    async def embed(self, context: Context, *, message: str) -> None:
        """
        The bot will say anything you want, but using embeds.

        :param context: The hybrid command context.
        :param message: The message that should be repeated by the bot.
        """
        embed = discord.Embed(description=message, color=0x9C84EF)
        await context.send(embed=embed)

    @commands.hybrid_group(name="blacklist",description="Get the list of all blacklisted users.",)
    @checks.is_owner()
    async def blacklist(self, context: Context) -> None:
        """
        Lets you add or remove a user from not being able to use the bot.

        :param context: The hybrid command context.
        """
        if context.invoked_subcommand is None:
            embed = discord.Embed(
                description="You need to specify a subcommand.\n\n**Subcommands:**\n`add` - Add a user to the blacklist.\n`remove` - Remove a user from the blacklist.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)

    @blacklist.command(base="blacklist",name="show",description="Shows the list of all blacklisted users.",)
    @checks.is_owner()
    async def blacklist_show(self, context: Context) -> None:
        """
        Shows the list of all blacklisted users.

        :param context: The hybrid command context.
        """
        blacklisted_users = await db_manager.get_blacklisted_users()
        if len(blacklisted_users) == 0:
            embed = discord.Embed(
                description="There are currently no blacklisted users.", color=0xE02B2B
            )
            await context.send(embed=embed)
            return

        embed = discord.Embed(title="Blacklisted Users", color=0x9C84EF)
        users = []
        for bluser in blacklisted_users:
            user = self.bot.get_user(int(bluser[0])) or await self.bot.fetch_user(
                int(bluser[0])
            )
            users.append(f"• {user.mention} ({user}) - Blacklisted <t:{bluser[1]}>")
        embed.description = "\n".join(users)
        await context.send(embed=embed)

    @blacklist.command(base="blacklist",name="add",description="Lets you add a user from not being able to use the bot.",)
    @app_commands.describe(user="The user that should be added to the blacklist")
    @checks.is_owner()
    async def blacklist_add(self, context: Context, user: discord.User) -> None:
        """
        Lets you add a user from not being able to use the bot.

        :param context: The hybrid command context.
        :param user: The user that should be added to the blacklist.
        """
        user_id = user.id
        if await db_manager.is_blacklisted(user_id):
            embed = discord.Embed(
                description=f"**{user.name}** is already in the blacklist.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return
        total = await db_manager.add_user_to_blacklist(user_id)
        embed = discord.Embed(
            description=f"**{user.name}** has been successfully added to the blacklist",
            color=0x9C84EF,
        )
        embed.set_footer(
            text=f"There {'is' if total == 1 else 'are'} now {total} {'user' if total == 1 else 'users'} in the blacklist"
        )
        await context.send(embed=embed)

    @blacklist.command(base="blacklist",name="remove",description="Lets you remove a user from not being able to use the bot.",)
    @app_commands.describe(user="The user that should be removed from the blacklist.")
    @checks.is_owner()
    async def blacklist_remove(self, context: Context, user: discord.User) -> None:
        """
        Lets you remove a user from not being able to use the bot.

        :param context: The hybrid command context.
        :param user: The user that should be removed from the blacklist.
        """
        user_id = user.id
        if not await db_manager.is_blacklisted(user_id):
            embed = discord.Embed(
                description=f"**{user.name}** is not in the blacklist.", color=0xE02B2B
            )
            await context.send(embed=embed)
            return
        total = await db_manager.remove_user_from_blacklist(user_id)
        embed = discord.Embed(
            description=f"**{user.name}** has been successfully removed from the blacklist",
            color=0x9C84EF,
        )
        embed.set_footer(
            text=f"There {'is' if total == 1 else 'are'} now {total} {'user' if total == 1 else 'users'} in the blacklist"
        )
        await context.send(embed=embed)
    
    @commands.hybrid_command(name="데이터정리", description="보존 기간이 지난 대화 로그와 전송 완료 영상 기록을 삭제합니다")
    @checks.is_owner()
    @app_commands.describe(days="며칠치를 남길까요? (기본 365일)")
    async def prune_data(self, context: Context, days: int = 365) -> None:
        # 회원 데이터 삭제는 되돌릴 수 없으므로 자동 태스크가 아니라
        # 운영자가 직접 호출하는 커맨드로 둔다.
        if days < 1:
            await context.send("보관 일수는 1 이상이어야 합니다.")
            return
        logs = await db_manager.prune_logs(days)
        videos = await db_manager.prune_sent_youtube_videos(days)
        embed = discord.Embed(title="데이터 정리 완료", color=0x9C84EF)
        embed.description = f"{days}일 이전 기록을 삭제했습니다."
        embed.add_field(name="대화 로그", value=f"{logs:,}건", inline=True)
        embed.add_field(name="전송 완료 영상", value=f"{videos:,}건", inline=True)
        await context.send(embed=embed)

    @commands.hybrid_command(name="channel_reset", description="채널 초기화")
    @commands.guild_only()
    @checks.is_owner()
    async def channel_reset(self, context: Context) -> None:
        # 삭제를 먼저 하면 이 채널로 응답을 보낼 수 없고, 복제 대상도 사라진다.
        # 복제 → 위치 조정 → 삭제 순으로 처리한다.
        old_channel = context.channel
        await context.send(f"**채널 초기화**: {old_channel.name} 을(를) 다시 만듭니다.")
        new_channel = await old_channel.clone(reason="Channel was purged")
        await new_channel.edit(position=old_channel.position)
        await old_channel.delete(reason="Channel was purged")

    @commands.hybrid_command(name="subscribe_youtube_channel", description="유튜브 구독")
    @checks.is_owner()
    @app_commands.describe(channel_name="유튜브 채널 핸들아이디")
    async def subscribe_youtube_channel(self, context: Context, channel_name: str) -> None:
        result = await self.bot.youtube.add_channel_rss_url(channel_name)
        if result == "Channel information added":
            await context.send(f"**채널 구독 완료**: {channel_name}")
        else:
            await context.send(f"**구독 실패**: 채널명을 확인해주세요 — {channel_name}")

    @commands.hybrid_command(name="unsubscribe_youtube_channel", description="유튜브 구독 취소")
    @checks.is_owner()
    @app_commands.describe(channel_name="유튜브 채널 핸들아이디")
    async def unsubscribe_youtube_channel(self, context: Context, channel_name: str) -> None:
        await self.bot.youtube.del_channel_rss_url(channel_name)
        await context.send(f"**채널 구독 해지**: {channel_name}")
                
async def setup(bot):
    await bot.add_cog(Owner(bot))