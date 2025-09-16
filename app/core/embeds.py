import discord
from discord import File
from PIL import Image, ImageDraw, ImageFont
import io
import requests

from app.tools.utils import rang01, rang02, rang03, rang04, rang05, rang06, darken_color


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


def create_rang_embed(display_name: str, message_count: int, rang_description: str, avatar_url: str):
    """Создает embed для команды !rang с цветом и фоном в зависимости от ранга"""
    # Цвета текста и фон для каждого ранга
    rank_designs = [
        {  # 0 сообщений
            "color": discord.Color.light_grey(),
            "next_threshold": 50,
            "rank_level": 0,
            "text_color": (130, 130, 130),
            "bg_filename": "rang0.jpg",
        },
        {  # 1-49
            "color": discord.Color.green(),
            "next_threshold": 50,
            "rank_level": 1,
            "text_color": (44, 255, 109),
            "bg_filename": "rang1.png",
        },
        {  # 50-99
            "color": discord.Color.blue(),
            "next_threshold": 100,
            "rank_level": 2,
            "text_color": (76, 142, 255),
            "bg_filename": "rang2.png",
        },
        {  # 100-199
            "color": discord.Color.gold(),
            "next_threshold": 200,
            "rank_level": 3,
            "text_color": (255, 215, 0),
            "bg_filename": "rang3.jpg",
        },
        {  # 200-499
            "color": discord.Color.purple(),
            "next_threshold": 500,
            "rank_level": 4,
            "text_color": (197, 94, 255),
            "bg_filename": "rang4.jpg",
        },
        {  # 500+
            "color": discord.Color.red(),
            "next_threshold": 500,
            "rank_level": 5,
            "text_color": (255, 73, 73),
            "bg_filename": "rang5.jpg",
        },
    ]

    if message_count == 0:
        rank = rank_designs[0]
    elif message_count < 50:
        rank = rank_designs[1]
    elif message_count < 100:
        rank = rank_designs[2]
    elif message_count < 200:
        rank = rank_designs[3]
    elif message_count < 500:
        rank = rank_designs[4]
    else:
        rank = rank_designs[5]

    progress_bar = f"{message_count}/{rank['next_threshold']}"
    exp_title = "EXP"

    # Передаем цвет текста и фон
    image_buffer = create_image_with_text(
        display_name,
        rang_description,
        progress_bar,
        exp_title,
        rank['rank_level'],
        text_color=rank['text_color'],
        bg_filename=rank['bg_filename'],
        avatar_url=avatar_url
    )
    file = File(image_buffer, filename="rang_with_text.png")

    embed = discord.Embed()
    embed.set_image(url="attachment://rang_with_text.png")

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


def create_image_with_text(
    display_name,
    rang_description,
    progress_bar,
    exp_title,
    rank_level,
    text_color=(44, 255, 109),
    bg_filename="rang0.jpg",
    avatar_url=None,
):
    # Загрузка фонового изображения
    background = Image.open(f"./app/resource/{bg_filename}").convert("RGBA")
    background = background.resize((1000, 250))

    width, height = background.size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    rect_color = (30, 30, 30, 180)

    # --- цвета для разных надписей ---
    main_dark_color = darken_color(text_color, 0.75)  # более темный цвет для основных надписей

    # Отступы и параметры блоков
    margin_x = int(width * 0.035)
    margin_y = int(height * 0.12)
    radius = 28

    # Определяем координаты блоков
    a_left = margin_x
    a_top = margin_y
    a_right = int(width * 0.70) - margin_x // 2
    a_bottom = height - margin_y
    b_left = a_right + margin_x
    b_top = margin_y
    b_right = width - margin_x
    b_bottom = margin_y + (height - 2 * margin_y) // 2 - 5
    c_left = b_left
    c_top = b_bottom + margin_y // 2
    c_right = b_right
    c_bottom = a_bottom

    # --- АВАТАР ПОЛЬЗОВАТЕЛЯ ---
    avatar_size = int((a_bottom - a_top) * 0.7)
    avatar_margin = int(avatar_size * 0.08)
    avatar_left = a_left + avatar_margin
    avatar_top = a_top + ((a_bottom - a_top) - avatar_size) // 2
    avatar_img = None

    # Сначала рисуем все прямоугольники
    draw.rounded_rectangle([a_left, a_top, a_right, a_bottom], radius, fill=rect_color)
    draw.rounded_rectangle([b_left, b_top, b_right, b_bottom], radius, fill=rect_color)
    draw.rounded_rectangle([c_left, c_top, c_right, c_bottom], radius, fill=rect_color)

    if avatar_url:
        try:
            resp = requests.get(avatar_url)
            avatar_img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
            avatar_img = avatar_img.resize((avatar_size, avatar_size))
            # Круглая маска
            mask = Image.new("L", (avatar_size, avatar_size), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
            avatar_img.putalpha(mask)
            # Вставляем аватар поверх прямоугольников
            overlay.paste(avatar_img, (avatar_left, avatar_top), avatar_img)
        except Exception as e:
            print("Ошибка загрузки аватара:", e)
            avatar_img = None

    # --- Шрифты ---
    try:
        main_font = ImageFont.truetype("arialbd.ttf", 40)
        aux_font = ImageFont.truetype("arialbd.ttf", 23)
        aux_value_font = ImageFont.truetype("arialbd.ttf", 23)
    except Exception:
        main_font = aux_font = aux_value_font = ImageFont.load_default()

    # ------ ВЫРАВНИВАНИЕ A ------
    # Отступ слева для текста: если есть аватар — после картинки, иначе обычный отступ
    a_text_left = avatar_left + avatar_size + avatar_margin if avatar_img else a_left + 10
    a_cy = a_top + (a_bottom - a_top) // 2

    # Размер display_name и rang_description
    dn_bbox = draw.textbbox((0, 0), display_name, font=main_font)
    dn_height = dn_bbox[3] - dn_bbox[1]
    rd_bbox = draw.textbbox((0, 0), rang_description, font=main_font)
    rd_height = rd_bbox[3] - rd_bbox[1]

    gap = 12
    total_height = dn_height + gap + rd_height
    top_block = a_cy - total_height // 2

    # Текст: display_name и rang_description
    draw.text((a_text_left, top_block), display_name, font=main_font, fill=main_dark_color)
    draw.text((a_text_left, top_block + dn_height + gap), rang_description, font=main_font, fill=text_color)

    # ------ ВЫРАВНИВАНИЕ B ------
    b_cx = b_left + (b_right - b_left) // 2
    b_cy = b_top + (b_bottom - b_top) // 2

    lvl_text = "LEVEL"
    lvl_bbox = draw.textbbox((0, 0), lvl_text, font=aux_font)
    lvl_width = lvl_bbox[2] - lvl_bbox[0]
    lvl_height = lvl_bbox[3] - lvl_bbox[1]
    rk_text = str(rank_level)
    rk_bbox = draw.textbbox((0, 0), rk_text, font=aux_value_font)
    rk_width = rk_bbox[2] - rk_bbox[0]
    rk_height = rk_bbox[3] - rk_bbox[1]
    gap_b = 10
    total_height_b = lvl_height + gap_b + rk_height
    b_top_block = b_cy - total_height_b // 2

    draw.text((b_cx - lvl_width // 2, b_top_block), lvl_text, font=aux_font, fill=main_dark_color)
    draw.text((b_cx - rk_width // 2, b_top_block + lvl_height + gap_b), rk_text, font=aux_value_font, fill=text_color)

    # ------ ВЫРАВНИВАНИЕ C ------
    c_cx = c_left + (c_right - c_left) // 2
    c_cy = c_top + (c_bottom - c_top) // 2

    exp_bbox = draw.textbbox((0, 0), exp_title, font=aux_font)
    exp_width = exp_bbox[2] - exp_bbox[0]
    exp_height = exp_bbox[3] - exp_bbox[1]
    bar_bbox = draw.textbbox((0, 0), progress_bar, font=aux_value_font)
    bar_width = bar_bbox[2] - bar_bbox[0]
    bar_height = bar_bbox[3] - bar_bbox[1]
    gap_c = 10
    total_height_c = exp_height + gap_c + bar_height
    c_top_block = c_cy - total_height_c // 2

    draw.text((c_cx - exp_width // 2, c_top_block), exp_title, font=aux_font, fill=main_dark_color)
    draw.text((c_cx - bar_width // 2, c_top_block + exp_height + gap_c), progress_bar, font=aux_value_font, fill=text_color)

    # Собираем картинку
    background = Image.alpha_composite(background, overlay)
    img_buffer = io.BytesIO()
    background.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    return img_buffer
