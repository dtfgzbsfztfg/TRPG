import json

import discord
from discord import app_commands
from discord.ext import commands

import db
from utils import dice, systems


class CharacterCog(commands.Cog):
    """캐릭터 시트 생성/조회/수정 명령어."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="char_create", description="새 캐릭터를 생성합니다.")
    @app_commands.describe(name="캐릭터 이름", system="시스템 프로필 이름 (예: generic)", hp="최대 HP (선택, 기본값은 시스템 기본치)")
    async def char_create(self, interaction: discord.Interaction, name: str, system: str = "generic", hp: int = None):
        try:
            profile = systems.load_system(system)
        except FileNotFoundError:
            available = ", ".join(systems.list_systems())
            await interaction.response.send_message(
                f"⚠️ `{system}` 시스템 프로필을 찾을 수 없어요. 사용 가능: {available}", ephemeral=True
            )
            return

        stats = systems.default_stats(system)
        hp_max = hp if hp is not None else profile.get("default_hp", 10)

        try:
            await db.create_character(
                str(interaction.guild_id), str(interaction.user.id), name, system, stats, hp_max
            )
        except Exception:
            await interaction.response.send_message(f"⚠️ 이미 `{name}` 캐릭터가 있어요.", ephemeral=True)
            return

        await interaction.response.send_message(
            f"✅ **{name}** ({profile['name']}) 캐릭터를 생성했어요! `/char_sheet name:{name}` 으로 확인해보세요."
        )

    @app_commands.command(name="char_sheet", description="캐릭터 시트를 확인합니다.")
    @app_commands.describe(name="캐릭터 이름")
    async def char_sheet(self, interaction: discord.Interaction, name: str):
        char = await db.get_character(str(interaction.guild_id), str(interaction.user.id), name)
        if not char:
            await interaction.response.send_message(f"⚠️ `{name}` 캐릭터를 찾을 수 없어요.", ephemeral=True)
            return

        profile = systems.load_system(char["system"])
        stats = json.loads(char["stats_json"])

        embed = discord.Embed(title=f"📜 {char['name']}", color=discord.Color.gold())
        embed.add_field(name="시스템", value=profile["name"], inline=True)
        embed.add_field(name="HP", value=f"{char['hp_current']} / {char['hp_max']}", inline=True)

        stat_lines = []
        for stat_def in profile.get("stats", []):
            key = stat_def["key"]
            value = stats.get(key, stat_def.get("default", 0))
            stat_lines.append(f"**{stat_def['label']}**: {value}")
        embed.add_field(name="능력치", value="\n".join(stat_lines) or "-", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="char_list", description="내 캐릭터 목록을 봅니다.")
    async def char_list(self, interaction: discord.Interaction):
        chars = await db.list_characters(str(interaction.guild_id), str(interaction.user.id))
        if not chars:
            await interaction.response.send_message("아직 생성한 캐릭터가 없어요.", ephemeral=True)
            return
        lines = [f"• **{c['name']}** ({c['system']}) HP {c['hp_current']}/{c['hp_max']}" for c in chars]
        await interaction.response.send_message("\n".join(lines))

    @app_commands.command(name="char_set", description="캐릭터 능력치를 수정합니다.")
    @app_commands.describe(name="캐릭터 이름", stat="능력치 key (예: str, dex)", value="새 값")
    async def char_set(self, interaction: discord.Interaction, name: str, stat: str, value: int):
        updated = await db.update_stat(str(interaction.guild_id), str(interaction.user.id), name, stat, value)
        if updated is None:
            await interaction.response.send_message(f"⚠️ `{name}` 캐릭터를 찾을 수 없어요.", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ **{name}**의 `{stat}` 값을 **{value}**로 변경했어요.")

    @app_commands.command(name="char_hp", description="캐릭터 HP를 증감시킵니다. (음수 입력 시 감소)")
    @app_commands.describe(name="캐릭터 이름", delta="변화량 (데미지는 음수, 회복은 양수)")
    async def char_hp(self, interaction: discord.Interaction, name: str, delta: int):
        new_hp = await db.update_hp(str(interaction.guild_id), str(interaction.user.id), name, delta)
        if new_hp is None:
            await interaction.response.send_message(f"⚠️ `{name}` 캐릭터를 찾을 수 없어요.", ephemeral=True)
            return
        change = f"+{delta}" if delta >= 0 else str(delta)
        await interaction.response.send_message(f"❤️ **{name}** HP {change} → 현재 **{new_hp}**")

    @app_commands.command(name="char_delete", description="캐릭터를 삭제합니다.")
    @app_commands.describe(name="캐릭터 이름")
    async def char_delete(self, interaction: discord.Interaction, name: str):
        ok = await db.delete_character(str(interaction.guild_id), str(interaction.user.id), name)
        if not ok:
            await interaction.response.send_message(f"⚠️ `{name}` 캐릭터를 찾을 수 없어요.", ephemeral=True)
            return
        await interaction.response.send_message(f"🗑️ **{name}** 캐릭터를 삭제했어요.")

    @app_commands.command(name="check_stat", description="캐릭터 능력치로 판정을 굴립니다. (시스템의 check_type에 따라 자동 처리)")
    @app_commands.describe(name="캐릭터 이름", stat="능력치 key")
    async def check_stat(self, interaction: discord.Interaction, name: str, stat: str):
        char = await db.get_character(str(interaction.guild_id), str(interaction.user.id), name)
        if not char:
            await interaction.response.send_message(f"⚠️ `{name}` 캐릭터를 찾을 수 없어요.", ephemeral=True)
            return

        profile = systems.load_system(char["system"])
        stats = json.loads(char["stats_json"])
        value = stats.get(stat)
        if value is None:
            await interaction.response.send_message(f"⚠️ `{stat}` 능력치가 없어요.", ephemeral=True)
            return

        check_type = profile.get("check_type", "d20_high")

        if check_type == "percentile_under":
            result, success = dice.roll_under("1d100", value)
            outcome = "✅ 성공" if success else "❌ 실패"
            msg = f"🎯 **{name}**의 {stat} 판정: {result.breakdown} = **{result.total}** (기준 {value}) → {outcome}"
        else:  # d20_high
            modifier = eval(profile.get("modifier_formula", "0"), {}, {"value": value})
            expr = f"1d20{'+' if modifier >= 0 else ''}{modifier}"
            result = dice.roll(expr)
            msg = f"🎯 **{name}**의 {stat} 판정: {result.breakdown} = **{result.total}**"

        await interaction.response.send_message(msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(CharacterCog(bot))
