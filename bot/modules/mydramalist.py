from contextlib import suppress
from aiohttp import ClientSession
from urllib.parse import quote as q
from pycountry import countries as conn
from pyrogram.enums import ButtonStyle
from pyrogram.errors import MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty

from ..core.tg_client import TgClient
from ..core.config_manager import Config
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import send_message, edit_message, delete_message
from ..helper.telegram_helper.bot_commands import BotCommands

LIST_ITEMS = 4
IMDB_GENRE_EMOJI = {"Action": "🚀", "Adult": "🔞", "Adventure": "🌋", "Animation": "🎠", "Biography": "📜", "Comedy": "🪗", "Crime": "🔪", "Documentary": "🎞", "Drama": "🎭", "Family": "👨‍👩‍👧‍👦", "Fantasy": "🫧", "Film Noir": "🎯", "Game Show": "🎮", "History": "🏛", "Horror": "🧟", "Musical": "🎻", "Music": "🎸", "Mystery": "🧳", "News": "📰", "Reality-TV": "🖥", "Romance": "🥰", "Sci-Fi": "🌠", "Short": "📝", "Sport": "⛳", "Talk-Show": "👨‍🍳", "Thriller": "🗡", "War": "⚔", "Western": "🪩"}
MDL_API = "https://my-drama-list-api-ten.vercel.app/api"

async def mydramalist_search(_, message):
    if ' ' in message.text:
        temp = await send_message(message, '<i>Searching in MyDramaList ...</i>')
        title = message.text.split(' ', 1)[1]
        user_id = message.from_user.id
        buttons = ButtonMaker()
        async with ClientSession() as sess:
            async with sess.get(f'{MDL_API}/search/q/{q(title)}') as resp:
                if resp.status != 200:
                    return await edit_message(temp, "<i>No Results Found</i>, Try Again or Use <b>MyDramaList Link</b>")
                mdl = await resp.json()
        if not mdl.get('results'):
            return await edit_message(temp, "<i>No Results Found</i>, Try Again or Use <b>MyDramaList Link</b>")
        for drama in mdl['results']:
            buttons.data_button(f"🎬 {drama.get('title')} ({drama.get('year')})", f"mdl {user_id} drama {drama.get('slug')}")
        buttons.data_button("🚫 Close 🚫", f"mdl {user_id} close", style=ButtonStyle.DANGER)
        await edit_message(temp, '<b><i>Dramas found on MyDramaList :</i></b>', buttons.build_menu(1))
    else:
        await send_message(message, f'<i>Send Movie / TV Series Name along with /{BotCommands.MyDramaListCommand} Command</i>')


async def extract_MDL(slug):
    async with ClientSession() as sess:
        async with sess.get(f'{MDL_API}/id/{slug}') as resp:
            mdl = await resp.json()
        async with sess.get(f'{MDL_API}/id/{slug}/cast') as resp:
            cast_data = await resp.json()

    casts = []
    if cast_data and 'cast' in cast_data:
        for role_type in ['Main Role', 'Support Role']:
            if role_type in cast_data['cast']:
                for person in cast_data['cast'][role_type]:
                    casts.append({'name': person.get('name'), 'link': person.get('profile_url')})

    plot = mdl.get('synopsis')
    if plot and len(plot) > 300:
        plot = f"{plot[:300]}..."
    return {
        'title': mdl.get('title'),
        'score': mdl.get('rating'),
        "aka": list_to_str(mdl.get("also_known_as")),
        'episodes': mdl.get("episodes"),
        'type': 'N/A',
        "cast": list_to_str(casts, cast=True),
        "country": list_to_hash([mdl.get("country")], True) if mdl.get("country") else "",
        'aired_date': mdl.get("aired", 'N/A'),
        'aired_on': mdl.get("aired_on"),
        'org_network': mdl.get("original_network"),
        'duration': mdl.get("duration"),
        'watchers': mdl.get("watchers"),
        'ranked': mdl.get("ranked"),
        'popularity': mdl.get("popularity"),
        'related_content': "",
        'native_title': mdl.get("native_title"),
        'director': "",
        'screenwriter': "",
        'genres': list_to_hash(mdl.get("genres"), emoji=True),
        'tags': list_to_str(mdl.get("tags")),
        'poster': mdl.get('image', '').replace('_4c.jpg', '_4f.jpg').strip(),
        'synopsis': plot,
        'rating': str(mdl.get("rating"))+" / 10",
        'content_rating': mdl.get("content_rating"),
        'url': mdl.get('url'),
    }


def list_to_str(k, cast=False):
    if not k:
        return ""
    elif len(k) == 1:
        if cast:
            return f'''<a href="{k[0].get('link')}">{k[0].get('name')}</a>'''
        return str(k[0])
    elif LIST_ITEMS:
        k = k[:int(LIST_ITEMS)]
    if cast:
        return ' '.join(f'''<a href="{elem.get('link')}">{elem.get('name')}</a>,''' for elem in k)[:-1]
    return ' '.join(f'{elem},' for elem in k)[:-1]

def list_to_hash(k, flagg=False, emoji=False):
    listing = ""
    if not k:
        return ""
    elif len(k) == 1:
        if not flagg:
            if emoji:
                return str(IMDB_GENRE_EMOJI.get(k[0], '')+" #"+k[0].replace(" ", "_").replace("-", "_"))
            return str("#"+k[0].replace(" ", "_").replace("-", "_"))
        try:
            conflag = (conn.get(name=k[0])).flag
            return str(f"{conflag} #" + k[0].replace(" ", "_").replace("-", "_"))
        except AttributeError:
            return str("#"+k[0].replace(" ", "_").replace("-", "_"))
    elif LIST_ITEMS:
        k = k[:int(LIST_ITEMS)]
        for elem in k:
            ele = elem.replace(" ", "_").replace("-", "_")
            if flagg:
                with suppress(AttributeError):
                    conflag = (conn.get(name=elem)).flag
                    listing += f'{conflag} '
            if emoji:
                listing += f"{IMDB_GENRE_EMOJI.get(elem, '')} "
            listing += f'#{ele}, '
        return f'{listing[:-2]}'
    else:
        for elem in k:
            ele = elem.replace(" ", "_").replace("-", "_")
            if flagg:
                conflag = (conn.get(name=elem)).flag
                listing += f'{conflag} '
            listing += f'#{ele}, '
        return listing[:-2]


async def mdl_callback(_, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()
    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
    elif data[2] == "drama":
        await query.answer()
        mdl = await extract_MDL(data[3])
        buttons = ButtonMaker()
        buttons.data_button("🚫 Close 🚫", f"mdl {user_id} close", style=ButtonStyle.DANGER)
        template = Config.MDL_TEMPLATE
        if mdl and template != "":
            cap = template.format(**mdl)
        else:
            cap = "<i>No Data Received</i>"
        if mdl.get('poster'):
            try:
                await TgClient.bot.send_photo(chat_id=message.reply_to_message.chat.id, photo=mdl["poster"], caption=cap, reply_markup=buttons.build_menu(1), reply_to_message_id=message.reply_to_message.id)
            except (MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty):
                poster = mdl["poster"].replace('_4f.jpg', '_4c.jpg')
                await send_message(message.reply_to_message, cap, buttons.build_menu(1), poster)
        else:
            await send_message(message.reply_to_message, cap, buttons.build_menu(1), 'https://telegra.ph/file/5af8d90a479b0d11df298.jpg')
        await delete_message(message)
    else:
        await query.answer()
        await delete_message(message, message.reply_to_message)
