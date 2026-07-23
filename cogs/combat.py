import discord
from discord import app_commands
from discord.ext import commands

import db
from utils import dice


class CombatCog(commands.Cog):
    """이니셔티브 순서/턴 진행/HP를 채널 단위로 관리."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="combat_start",
        description='전투를 시작합니다. 참가자를 "이름:HP" 로 쉼표 구분해서 입력하면 이니셔티브(1d20)를 자동으로 굴려요.',
    )
    @app_commands.describe(participants='예: "고블린A:15,고블린B:12,전사:20"')
    async def combat_start(self, interaction: discord.Interaction, participants: str):
        entries = []
        for part in participants.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" in part:
                name, hp_str = part.split(":", 1)
                hp = int(hp_str.strip())
            else:
                name, hp = part, 0
            init_roll = dice.roll("1d20")
            entries.append({
                "name": name.strip(),
                "init": init_roll.total,
                "hp_current": hp,
                "hp_max": hp,
            })

        if not entries:
            await interaction.response.send_message("⚠️ 참가자를 최소 1명 입력해주세요.", ephemeral=True)
            return

        entries.sort(key=lambda e: e["init"], reverse=True)
        await db.save_combat(str(interaction.channel_id), round_=1, turn_index=0, order=entries)

        lines = [f"{i+1}. **{e['name']}** (이니셔티브 {e['init']}, HP {e['hp_current']})" for i, e in enumerate(entries)]
        embed = discord.Embed(title="⚔️ 전투 시작!", description="\n".join(lines), color=discord.Color.red())
        embed.set_footer(text=f"1라운드 - {entries[0]['name']}의 턴")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="combat_status", description="현재 전투 상황을 봅니다.")
    async def combat_status(self, interaction: discord.Interaction):
        combat = await db.get_combat(str(interaction.channel_id))
        if not combat:
            await interaction.response.send_message("진행 중인 전투가 없어요.", ephemeral=True)
            return

        order = combat["order"]
        lines = []
        for i, e in enumerate(order):
            marker = "👉 " if i == combat["turn_index"] else "　"
            lines.append(f"{marker}{i+1}. **{e['name']}** (init {e['init']}) HP {e['hp_current']}/{e['hp_max']}")

        embed = discord.Embed(
            title=f"⚔️ 전투 현황 - {combat['round']}라운드",
            description="\n".join(lines),
            color=discord.Color.orange(),
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="combat_next", description="다음 턴으로 넘어갑니다.")
    async def combat_next(self, interaction: discord.Interaction):
        combat = await db.get_combat(str(interaction.channel_id))
        if not combat:
            await interaction.response.send_message("진행 중인 전투가 없어요.", ephemeral=True)
            return

        order = combat["order"]
        next_index = combat["turn_index"] + 1
        round_ = combat["round"]
        if next_index >= len(order):
            next_index = 0
            round_ += 1

        await db.save_combat(str(interaction.channel_id), round_, next_index, order)
        current = order[next_index]
        await interaction.response.send_message(
            f"➡️ **{round_}라운드** - **{current['name']}**의 턴입니다! (HP {current['hp_current']}/{current['hp_max']})"
        )

    @app_commands.command(name="combat_damage", description="전투 참가자의 HP를 증감시킵니다.")
    @app_commands.describe(name="참가자 이름", delta="변화량 (데미지는 음수, 회복은 양수)")
    async def combat_damage(self, interaction: discord.Interaction, name: str, delta: int):
        combat = await db.get_combat(str(interaction.channel_id))
        if not combat:
            await interaction.response.send_message("진행 중인 전투가 없어요.", ephemeral=True)
            return

        order = combat["order"]
        target = next((e for e in order if e["name"] == name), None)
        if not target:
            await interaction.response.send_message(f"⚠️ `{name}` 참가자를 찾을 수 없어요.", ephemeral=True)
            return

        target["hp_current"] = max(0, min(target["hp_max"], target["hp_current"] + delta))
        await db.save_combat(str(interaction.channel_id), combat["round"], combat["turn_index"], order)

        change = f"+{delta}" if delta >= 0 else str(delta)
        status = " (전투불능)" if target["hp_current"] <= 0 else ""
        await interaction.response.send_message(
            f"❤️ **{name}** HP {change} → 현재 **{target['hp_current']}/{target['hp_max']}**{status}"
        )

    @app_commands.command(name="combat_end", description="전투를 종료합니다.")
    async def combat_end(self, interaction: discord.Interaction):
        await db.end_combat(str(interaction.channel_id))
        await interaction.response.send_message("🏁 전투가 종료되었습니다.")


async def setup(bot: commands.Bot):
    await bot.add_cog(CombatCog(bot))
