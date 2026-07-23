import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
# 메시지 내용이 필요한 기능(접두사 명령 등)을 쓸 게 아니면 기본 intents로 충분합니다.

bot = commands.Bot(command_prefix="!", intents=intents)

INITIAL_EXTENSIONS = [
    "cogs.dice",
    "cogs.character",
    "cogs.combat",
]


@bot.event
async def on_ready():
    print(f"✅ 로그인 완료: {bot.user} (id: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"슬래시 커맨드 {len(synced)}개 동기화 완료")
    except Exception as e:
        print(f"커맨드 동기화 실패: {e}")


async def main():
    await db.init_db()
    async with bot:
        for ext in INITIAL_EXTENSIONS:
            await bot.load_extension(ext)
        await bot.start(TOKEN)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("❌ .env 파일에 DISCORD_TOKEN을 설정해주세요. (.env.example 참고)")
    asyncio.run(main())
