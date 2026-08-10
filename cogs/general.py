import os
import platform
import random

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks

CHANNEL_INFO = {
    "🔊-공지에요": "V-AIS의 공지가 올라옵니다!",
    "💡geek-news": "최신 IT 관련 정보들을 볼 수 있습니다!",
    "💬잡담-잡담": "이런 저런 다양한 얘기를 하는 곳이에요!",
    "🙋질문과-답변": "자유롭게 질문 답변하는 채널입니다!",
    "📈주식-이모저모": "주식 관련 이야기를 나누는 채널입니다!",
    "🎮게임-이모저모": "게임 관련 이야기를 나누는 채널입니다!",
    "💼채용-공고": "채용 관련 정보를 공유하는 채널입니다!",
    "🏬중고-마켓": "중고 마켓을 운영하기 위한 채널입니다!\n자세한 사항은 https://jjerry.notion.site/V-AIS-Market-bd9a224502aa4fed9fd8f7cd6f54e044 여기를 참고해주세요!",
    "📝건의합니다": "V-AIS 서버 관련해서 건의 사항을 적는 곳입니다!\n다양한 의견 많이 많이 주세요!",
    "📚today-i-learned": "오늘은 무엇을 공부했는지 공유하는 채널이에요!",
    
    "📼유튜브-영상": "여러 유튜브 채널의 영상이 올라옵니다!",
    "📖책-공유": "다양한 책들을 공유하는 곳입니다!",
    "📓논문-공유": "힙한 논문을 공유해봅시다!",
    "📂자료-공유": "공부하는데 좋은 자료가 있으면 같이 봐요!",
    "💼진로-정보-공유": "취업/진학등의 정보를 공유하는 채널입니다!",
    "🗣인터뷰-정보-공유":"면접에 관련된 정보를 공유하는 채널입니다!\n추후 깃허브 레포를 만들어 볼 예정이에요!",
    
    "📚스터디-모집": "하고 싶은 스터디가 있고 멤버 모집을 하고 싶으시면 말씀해주세요!",
    "📚프로젝트-모집": "하고 싶은 프로젝트가 있고 멤버 모집을 하고 싶으시면 말씀해주세요!",
    "봇-실험": "이런...저런....봇을 실험 하는 곳입니다...ㅎㅎ",
    
    "스터디 룸 101": "스터디룸101 음성채팅에 참여하신 분들을 위한 공간입니다!",
    "스터디 룸 102": "스터디룸102 음성채팅에 참여하신 분들을 위한 공간입니다!",
    "스터디 룸 103": "스터디룸103 음성채팅에 참여하신 분들을 위한 공간입니다!",
}

def get_server_info():
    with open("/proc/cpuinfo", "r") as f:
        cpuinfo = f.readlines()
        for tmp in cpuinfo:
            if "model name" in tmp: break
        cpuinfo = tmp.split("model name\t: ")[-1].strip()
    
    with open("/proc/meminfo", "r") as f:
        meminfo = f.readlines()
        memtot, memavailable = None, None
        for tmp in meminfo:
            if "MemTotal" in tmp: 
                memtot = float(tmp.split("MemTotal:")[-1].strip()[:-3])
                
            elif "MemAvailable" in tmp: 
                memavailable = float(tmp.split("MemAvailable:")[-1].strip()[:-3])
            
            if memtot and memavailable: break
        meminfo = f"{(memtot-memavailable)/1024/1024:.2f}GB/{memtot/1024/1024:.2f}GB"
    
    cputemp1 = cputempm = None
    if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            cputemp0 = float(f.readline())
        cputemp1 = int(cputemp0 // 1000)
        cputemp2 = int(cputemp0 // 100)
        cputempm = cputemp2 % cputemp1

    result = {
        "Server Name": platform.node(),
        "OS": platform.version().split(' ')[0][1:],
        "CPU": cpuinfo,
        "Memory": meminfo,
        "Temperature": f"{cputemp1}.{cputempm}°C" if isinstance(cputemp1, int) else f"확인불가"
    }
    return result

class General(commands.Cog, name="general"):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="도움말", description="봇의 명령어 리스트입니다")
    @checks.not_blacklisted()
    async def help(self, context: Context) -> None:
        prefix = self.bot.config["PREFIX"]
        embed = discord.Embed(
            title="도움말", description="봇 명령어 리스트:", color=0x9C84EF
        )
        for i in self.bot.cogs:
            if i.lower() in ["owner", "moderation"]: continue
            cog = self.bot.get_cog(i.lower())
            commands = cog.get_commands()
            data = []
            for command in commands:
                description = command.description.partition("\n")[0]
                data.append(f"{prefix}{command.name} - {description}")
            help_text = "\n".join(data)
            embed.add_field(
                name=i.capitalize(), value=f"```{help_text}```", inline=False
            )
        await context.send(embed=embed)

    @commands.hybrid_command(name="봇정보",description="봇의 정보를 보여줍니다.",)
    @checks.not_blacklisted()
    async def botinfo(self, context: Context) -> None:
        """
        Get some useful (or not) information about the bot.

        :param context: The hybrid command context.
        """
        bot_hardware_info = get_server_info()
        embed = discord.Embed(
            description="[Krypton's](https://krypton.ninja) template을 이용하였습니다!",
            color=0x9C84EF,
        )
        embed.set_author(name="Bot Information")
        embed.add_field(name="Owner:", value="V-AIS", inline=True)
        embed.add_field(
            name="Python Version:", value=f"{platform.python_version()}", inline=True
        )
        embed.add_field(name="OS", value=bot_hardware_info["OS"], inline=False)
        embed.add_field(name="CPU", value=bot_hardware_info["CPU"], inline=False)
        embed.add_field(name="Memory", value=bot_hardware_info["Memory"], inline=True)
        embed.add_field(name="Temperature", value=bot_hardware_info["Temperature"], inline=False)
        embed.add_field(
            name="Prefix:",
            value=f"/ (Slash Commands) 혹은 {self.bot.config['PREFIX']} 를 이용하여 커맨드를 입력하세요",
            inline=False,
        )
        embed.set_footer(text=f"Requested by {context.author}")
        await context.send(embed=embed)

    @commands.hybrid_command(name="서버정보",description="V-AIS 서버 정보를 보여줍니다",)
    @commands.guild_only()
    @checks.not_blacklisted()
    async def serverinfo(self, context: Context) -> None:
        """
        Get some useful (or not) information about the server.

        :param context: The hybrid command context.
        """
        roles = [role.name for role in context.guild.roles]
        total_roles = len(roles)
        if total_roles > 50:
            # 자른 뒤에 len() 을 세면 항상 "50/50" 이 나온다.
            roles = roles[:50]
            roles.append(f">>>> Displaying[50/{total_roles}] Roles")
        roles = ", ".join(roles)

        embed = discord.Embed(
            title="**서버 이름:**", description=f"{context.guild}", color=0x9C84EF
        )
        if context.guild.icon is not None:
            embed.set_thumbnail(url=context.guild.icon.url)
        embed.add_field(name="서버 ID", value=context.guild.id)
        embed.add_field(name="인원 수", value=context.guild.member_count)
        embed.add_field(
            name="채널 수", value=f"{len(context.guild.channels)}"
        )
        await context.send(embed=embed)

    @commands.hybrid_command(name="ping",description="봇...살아있니..?",)
    @checks.not_blacklisted()
    async def ping(self, context: Context) -> None:
        """
        Check if the bot is alive.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"The bot latency is {round(self.bot.latency * 1000)}ms.",
            color=0x9C84EF,
        )
        await context.send(embed=embed)

    @commands.hybrid_command(name="질문",description="봇한테 물어보세요!",)
    @checks.not_blacklisted()
    @app_commands.describe(question="어떤 질문을 하실건가요?")
    async def question(self, context: Context, *, question: str) -> None:
        """
        Ask any question to the bot.

        :param context: The hybrid command context.
        :param question: The question that should be asked by the user.
        """
        answers = [
            "It is certain.",
            "It is decidedly so.",
            "You may rely on it.",
            "Without a doubt.",
            "Yes - definitely.",
            "As I see, yes.",
            "Most likely.",
            "Outlook good.",
            "Yes.",
            "Signs point to yes.",
            "Reply hazy, try again.",
            "Ask again later.",
            "Better not tell you now.",
            "Cannot predict now.",
            "Concentrate and ask again later.",
            "Don't count on it.",
            "My reply is no.",
            "My sources say no.",
            "Outlook not so good.",
            "Very doubtful.",
        ]
        embed = discord.Embed(
            title="**답변:**",
            description=f"{random.choice(answers)}",
            color=0x9C84EF,
        )
        embed.set_footer(text=f"질문: {question}")
        await context.send(embed=embed)
    
    @commands.hybrid_command(name="채널정보", description="해당 채널의 정보를 알려드립니다!",)
    @checks.not_blacklisted()
    async def channel_info(self, context: Context) -> None:
        # DMChannel 에는 name 이 없다.
        channel_name = getattr(context.channel, "name", None)
        embed = discord.Embed(
            title=f"{channel_name or 'DM'}",
            description= CHANNEL_INFO.get(channel_name, "이 채널에 대한 정보가 아직 없습니다!"),
            color=0x9C84EF,
        )
        await context.send(embed=embed)
    @commands.hybrid_command(name="음악봇", description="음악 봇 사용방법을 알려드립니다!")
    @checks.not_blacklisted()
    async def music_bot_info(self, context: Context) -> None:
        embed = discord.Embed(
            title=f"음악 봇 사용방법",
            color=0x9C84EF,
        )
        embed.add_field(name="Ayana (https://ayana.io)", value="명령어: https://ayana.io/docs/commands\n채팅창에 /music play 를 입력하시면 안내가 나옵니다!", inline=False)
        embed.add_field(name="​", value="​", inline=False)
        embed.add_field(name="Mirai (https://mirai.brussell.me)", value="명령어: https://mirai.brussell.me/commands\n1. mm.join 을 입력해서 Mirai를 음성 채널에 참가시켜주세요!\n2. mm.play {youtube URL} 을 하시면 재생됩니다!\n3. mm.queue {youtube URL} 을 하시면 재생 목록이 추가됩니다!", inline=False)
        embed.add_field(name="​", value="​", inline=False)
        embed.add_field(name="Vexera (https://vexera.io)", value="명령어: https://vexera.io/commands\n1. +play {youtube URL} 하시면 Vexera가 음성 채널 참가되고 음악을 재생합니다!\n2. +play-next {youtube URL} 를 하시면 대기열에 추가할 수 있어요!", inline=False)
        await context.send(embed=embed)

async def setup(bot):
    await bot.add_cog(General(bot))
