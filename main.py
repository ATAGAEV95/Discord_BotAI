import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
from app import handlers

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Бот {bot.user} готов к работе!')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if not message.content.startswith("!"):
        return

    if message.content.startswith("!reset"):
        await handlers.reset_history()
        await message.channel.send("История разговоров была очищена.")
        return

    response = await handlers.ai_generate(message.content, message.author)

    await message.channel.send(response)


bot.run(TOKEN)
