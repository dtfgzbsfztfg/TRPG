import discord
from discord import app_commands
from discord.ext import commands

from utils import dice


class DiceCog(commands.Cog):
    """주사위 굴리기 관련 명령어."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="roll", description="주사위를 굴립니다. 예: 1d20+5, 2d6+1d4-2, 4d6kh3, 1d20adv")
    @app_commands.describe(expression="주사위 수식", label="이 굴림에 대한 설명 (선택)")
    async def roll(self, interaction: discord.Interaction, expression: str, label: str = None):
        try:
            result = dice.roll(expression)
        except ValueError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        title = f"🎲 {label}" if label else "🎲 주사위 굴림"
        embed = discord.Embed(title=title, color=discord.Color.blurple())
        embed.add_field(name="수식", value=f"`{expression}`", inline=True)
        embed.add_field(name="결과", value=f"**{result.total}**", inline=True)
        embed.add_field(name="상세", value=result.breakdown, inline=False)
        embed.set_footer(text=f"굴린 사람: {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="check", description="목표치 이하로 굴리면 성공하는 판정 (퍼센타일류 시스템용)")
    @app_commands.describe(dice_expr="예: 1d100", target="성공 기준치 (이 값 이하면 성공)", label="판정 이름 (선택)")
    async def check(self, interaction: discord.Interaction, dice_expr: str, target: int, label: str = None):
        try:
            result, success = dice.roll_under(dice_expr, target)
        except ValueError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        outcome = "✅ 성공" if success else "❌ 실패"
        title = f"🎯 {label}" if label else "🎯 판정"
        embed = discord.Embed(
            title=title,
            color=discord.Color.green() if success else discord.Color.red(),
        )
        embed.add_field(name="굴림", value=f"{result.breakdown} = **{result.total}**", inline=False)
        embed.add_field(name="기준치", value=str(target), inline=True)
        embed.add_field(name="결과", value=outcome, inline=True)
        embed.set_footer(text=f"굴린 사람: {interaction.user.display_name}")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(DiceCog(bot))
