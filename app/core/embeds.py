import discord
from discord import File

from app.tools.utils import rang01, rang02, rang03, rang04, rang05, rang06


def create_help_embed():
    """Создает embed для команды !help"""
    embed = discord.Embed(
        title="📋 Справка по командам бота",
        color=discord.Color.blue(),
        description="Все доступные команды и их использование:"
    )

    embed.add_field(
        name="🎯 Основные команды",
        value=(
            "`!reset` - очистка истории чата\n"
            "`!help` - показать эту справку\n"
            "`!rang` - узнать свой ранг и статистику\n"
            "`!rang list` - показать все возможные ранги\n"
            "`!birthday DD.MM.YYYY` - добавить/обновить дату рождения"
        ),
        inline=False
    )

    embed.add_field(
        name="📺 Команды для YouTube",
        value=(
            "`!add_youtube` - добавить YouTube канал для отслеживания\n"
            "*(только для администраторов)*"
        ),
        inline=False
    )

    embed.add_field(
        name="🌤️ Погода",
        value=(
            "`погода [город]` - текущая погода\n"
            "`погода [город] завтра` - прогноз на завтра"
        ),
        inline=False
    )
    return embed


def create_rang_embed(display_name: str, message_count: int, rang_description: str):
    """Создает embed для команды !rang с цветом в зависимости от ранга"""
    if message_count == 0:
        color = discord.Color.light_grey()
        next_threshold = 50
        rank_level = 0
    elif message_count < 50:
        color = discord.Color.green()
        next_threshold = 50
        rank_level = 1
    elif message_count < 100:
        color = discord.Color.blue()
        next_threshold = 100
        rank_level = 2
    elif message_count < 200:
        color = discord.Color.gold()
        next_threshold = 200
        rank_level = 3
    elif message_count < 500:
        color = discord.Color.purple()
        next_threshold = 500
        rank_level = 4
    else:
        color = discord.Color.red()
        next_threshold = 500
        rank_level = 5

    embed = discord.Embed(
        title=display_name,
        description=f"### {rang_description}",
        color=color
    )

    progress_bar = f"{message_count}/{next_threshold}"
    exp_title = "EXP"

    image_buffer = create_image_with_text(display_name, rang_description, progress_bar, exp_title, rank_level)
    file = File(image_buffer, filename="rang_with_text.jpg")

    embed = discord.Embed()
    embed.set_image(url="attachment://rang_with_text.jpg")

    return embed, file


def create_rang_list_embed():
    """Создает embed для команды !rang list"""
    embed = discord.Embed(
        title="🎖️ Система рангов",
        color=discord.Color.blurple(),
        description="Все возможные ранги и условия их получения:"
    )

    embed.add_field(
        name=rang01,
        value="0 сообщений",
        inline=False
    )

    embed.add_field(
        name=rang02,
        value="1-49 сообщений",
        inline=False
    )

    embed.add_field(
        name=rang03,
        value="50-99 сообщений",
        inline=False
    )

    embed.add_field(
        name=rang04,
        value="100-199 сообщений",
        inline=False
    )

    embed.add_field(
        name=rang05,
        value="200-499 сообщений",
        inline=False
    )

    embed.add_field(
        name=rang06,
        value="500+ сообщений",
        inline=False
    )

    embed.set_footer(text="Пишите сообщения, чтобы повысить свой ранг!")

    return embed


from PIL import Image, ImageDraw, ImageFont
import io


def create_image_with_text(display_name, rang_description, progress_bar, exp_title):
    # Загружаем фоновое изображение
    background = Image.open("./app/resource/fon.jpg")
    draw = ImageDraw.Draw(background)

    # Загружаем шрифт (укажите путь к шрифту на вашем сервере)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except:
        font = ImageFont.load_default()

    # Рисуем текст на изображении
    draw.text((50, 50), f"{display_name} {rang_description}", font=font, fill=(255, 255, 255))
    draw.text((50, 100), exp_title, font=font, fill=(255, 255, 255))
    draw.text((50, 150), progress_bar, font=font, fill=(255, 255, 255))

    # Сохраняем изображение в буфер
    img_buffer = io.BytesIO()
    background.save(img_buffer, format='JPEG')
    img_buffer.seek(0)

    return img_buffer