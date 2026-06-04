import aiohttp
import urllib.parse
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from pyrogram.enums import ParseMode

from .. import LOGGER
from ..core.config_manager import Config
from ..helper.ext_utils.bot_utils import new_task

# Helper function for async API calls
async def fetch_json(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
    except Exception as e:
        LOGGER.error(f"API Fetch Error: {e}")
    return None

@new_task
async def get_poster_menu(client, message):
    tmdb_api_key = Config.TMDB_API_KEY
    if not tmdb_api_key:
        return await message.reply_text("⚠️ ᴛᴍᴅʙ_ᴀᴘɪ_ᴋᴇʏ ɪꜱ ᴍɪꜱꜱɪɴɢ!")

    if len(message.command) == 1:
        return await message.reply_text("⚠️ ᴘʟᴇᴀꜱᴇ ᴘʀᴏᴠɪᴅᴇ ᴀ ᴍᴏᴠɪᴇ ᴏʀ ᴛᴠ ꜱʜᴏᴡ ɴᴀᴍᴇ.\n\n📌 ᴇxᴀᴍᴘʟᴇ: /poster naruto")

    query = " ".join(message.command[1:])
    # Short query for callback data (max 20 chars to fit 64-byte limit)
    short_query = query[:20].replace(" ", "-").replace("_", "-")
    safe_query = urllib.parse.quote_plus(query)
    msg = await message.reply_text(f"<b>🔎 ꜱᴇᴀʀᴄʜɪɴɢ ᴛᴍᴅʙ ꜰᴏʀ</b> <code>{query}</code> <b>...</b>")

    try:
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={tmdb_api_key}&query={safe_query}"
        search_results = await fetch_json(search_url)

        if not search_results or not search_results.get("results"):
            return await msg.edit_text("<b>❌ ɴᴏ ʀᴇꜱᴜʟᴛꜱ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ ꜱᴇᴀʀᴄʜ!</b>")

        valid_results = [item for item in search_results["results"] if item["media_type"] in ["movie", "tv"]]

        if not valid_results:
             return await msg.edit_text("<b>❌ ɴᴏ ᴍᴏᴠɪᴇ ᴏʀ ᴛᴠ ꜱʜᴏᴡ ꜰᴏᴜɴᴅ!</b>")

        buttons = []
        for item in valid_results[:10]:
            tmdb_id = item["id"]
            media_type = item["media_type"]
            title = item.get("name") or item.get("title", "ᴜɴᴋɴᴏᴡɴ")

            date_key = "first_air_date" if media_type == "tv" else "release_date"
            year = item.get(date_key, "")[:4] if item.get(date_key) else "ɴ/ᴀ"

            m_icon = "📺" if media_type == "tv" else "🎬"
            m_type_str = "ᴛᴠ" if media_type == "tv" else "ᴍᴏᴠɪᴇ"
            btn_text = f"{m_icon} {title} ({year}) [{m_type_str}]"

            # Pass short_query to support the Back to Search button
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"p_menu_{media_type}_{tmdb_id}_{short_query}")])

        buttons.append([InlineKeyboardButton("❌ ᴄʟᴏꜱᴇ", callback_data="close_data")])

        await msg.edit_text(
            text=f"<b>✅ ᴍᴜʟᴛɪᴘʟᴇ ʀᴇꜱᴜʟᴛꜱ ꜰᴏᴜɴᴅ ꜰᴏʀ</b> <code>{query}</code>\n\n<b>👇 ꜱᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴍᴏᴠɪᴇ ᴏʀ ꜱᴇʀɪᴇꜱ ꜰʀᴏᴍ ʙᴇʟᴏᴡ:</b>",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as e:
        LOGGER.error(e)
        await msg.edit_text(f"<b>⚠️ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ:</b> `{e}`")

@new_task
async def handle_back_to_search(client, callback_query):
    tmdb_api_key = Config.TMDB_API_KEY
    if not tmdb_api_key:
        return await callback_query.answer("⚠️ ᴛᴍᴅʙ_ᴀᴘɪ_ᴋᴇʏ ɪꜱ ᴍɪꜱꜱɪɴɢ!", show_alert=True)

    short_query = callback_query.data.replace("p_search_", "").replace("-", " ")
    await callback_query.answer("🔎 ʟᴏᴀᴅɪɴɢ ꜱᴇᴀʀᴄʜ ʀᴇꜱᴜʟᴛꜱ...")

    try:
        safe_query = urllib.parse.quote_plus(short_query)
        search_url = f"https://api.themoviedb.org/3/search/multi?api_key={tmdb_api_key}&query={safe_query}"
        search_results = await fetch_json(search_url)

        if not search_results or not search_results.get("results"):
            return await callback_query.answer("❌ ɴᴏ ʀᴇꜱᴜʟᴛꜱ ꜰᴏᴜɴᴅ ꜰᴏʀ ʏᴏᴜʀ ꜱᴇᴀʀᴄʜ!", show_alert=True)

        valid_results = [item for item in search_results["results"] if item["media_type"] in ["movie", "tv"]]

        if not valid_results:
             return await callback_query.answer("❌ ɴᴏ ᴍᴏᴠɪᴇ ᴏʀ ᴛᴠ ꜱʜᴏᴡ ꜰᴏᴜɴᴅ!", show_alert=True)

        buttons = []
        cb_query_str = callback_query.data.replace("p_search_", "")
        for item in valid_results[:10]:
            tmdb_id = item["id"]
            media_type = item["media_type"]
            title = item.get("name") or item.get("title", "ᴜɴᴋɴᴏᴡɴ")

            date_key = "first_air_date" if media_type == "tv" else "release_date"
            year = item.get(date_key, "")[:4] if item.get(date_key) else "ɴ/ᴀ"

            m_icon = "📺" if media_type == "tv" else "🎬"
            m_type_str = "ᴛᴠ" if media_type == "tv" else "ᴍᴏᴠɪᴇ"
            btn_text = f"{m_icon} {title} ({year}) [{m_type_str}]"

            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"p_menu_{media_type}_{tmdb_id}_{cb_query_str}")])

        buttons.append([InlineKeyboardButton("❌ ᴄʟᴏꜱᴇ", callback_data="close_data")])

        text = f"<b>✅ ᴍᴜʟᴛɪᴘʟᴇ ʀᴇꜱᴜʟᴛꜱ ꜰᴏᴜɴᴅ ꜰᴏʀ</b> <code>{short_query}</code>\n\n<b>👇 ꜱᴇʟᴇᴄᴛ ʏᴏᴜʀ ᴍᴏᴠɪᴇ ᴏʀ ꜱᴇʀɪᴇꜱ ꜰʀᴏᴍ ʙᴇʟᴏᴡ:</b>"

        if callback_query.message.photo:
            await client.send_message(
                chat_id=callback_query.message.chat.id,
                text=text,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            try:
                await callback_query.message.delete()
            except:
                pass
        else:
            await callback_query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        LOGGER.error(e)
        await callback_query.answer(f"⚠️ ᴀɴ ᴇʀʀᴏʀ ᴏᴄᴄᴜʀʀᴇᴅ!", show_alert=True)

@new_task
async def show_poster_categories(client, callback_query):
    tmdb_api_key = Config.TMDB_API_KEY
    if not tmdb_api_key:
        return await callback_query.answer("⚠️ ᴛᴍᴅʙ_ᴀᴘɪ_ᴋᴇʏ ɪꜱ ᴍɪꜱꜱɪɴɢ!", show_alert=True)

    data = callback_query.data.split("_")
    media_type = data[2]
    tmdb_id = data[3]
    short_query = data[4] if len(data) > 4 else ""

    await callback_query.answer("ɢᴇɴᴇʀᴀᴛɪɴɢ ᴍᴇɴᴜ...")

    try:
        details_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={tmdb_api_key}"
        img_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/images?api_key={tmdb_api_key}"

        details = await fetch_json(details_url)
        images = await fetch_json(img_url)

        if not details or not images:
            return await callback_query.answer("⚠️ ꜰᴀɪʟᴇᴅ ᴛᴏ ꜰᴇᴛᴄʜ ᴅᴇᴛᴀɪʟꜱ!", show_alert=True)

        title = details.get("name") or details.get("title", "ᴜɴᴋɴᴏᴡɴ ᴛɪᴛʟᴇ")
        date_key = "first_air_date" if media_type == "tv" else "release_date"
        year = details.get(date_key, "")[:4] if details.get(date_key) else "ɴ/ᴀ"

        backdrops = images.get("backdrops", [])
        posters = images.get("posters", [])
        logos = images.get("logos", [])

        # Filter: Landscape (with language/text) vs Clean Landscape (No language/textless)
        # None and 'xx' indicate no specific language text
        landscape = [img for img in backdrops if img.get("iso_639_1") not in (None, "xx")]
        # Sort Landscape: English first, then alphabetical by language code
        landscape.sort(key=lambda x: (0 if x.get("iso_639_1") == 'en' else 1, x.get("iso_639_1", "")))

        clean_landscape = [img for img in backdrops if img.get("iso_639_1") in (None, "xx")]

        # Use w1280 for stable telegram loading instead of original
        main_poster_path = details.get('poster_path') or (posters[0]['file_path'] if posters else None)
        main_poster = f"https://image.tmdb.org/t/p/w1280{main_poster_path}" if main_poster_path else "https://via.placeholder.com/800x1200?text=No+Poster"

        buttons = [
            [
                InlineKeyboardButton(f"🌄 ʟᴀɴᴅꜱᴄᴀᴘᴇ ({len(landscape)})", callback_data=f"p_view_land_{media_type}_{tmdb_id}_0_{short_query}"),
                InlineKeyboardButton(f"📱 ᴘᴏʀᴛʀᴀɪᴛ ({len(posters)})", callback_data=f"p_view_port_{media_type}_{tmdb_id}_0_{short_query}")
            ],
            [
                InlineKeyboardButton(f"✨ ʟᴏɢᴏꜱ ({len(logos)})", callback_data=f"p_view_logo_{media_type}_{tmdb_id}_0_{short_query}"),
                InlineKeyboardButton(f"🌌 ᴄʟᴇᴀɴ ʟᴀɴᴅꜱᴄᴀᴘᴇ ({len(clean_landscape)})", callback_data=f"p_view_clean_{media_type}_{tmdb_id}_0_{short_query}")
            ]
        ]

        nav_close_btns = []
        if short_query:
            nav_close_btns.append(InlineKeyboardButton("🔙 ʙᴀᴄᴋ ᴛᴏ ꜱᴇᴀʀᴄʜ", callback_data=f"p_search_{short_query}"))
        nav_close_btns.append(InlineKeyboardButton("❌ ᴄʟᴏꜱᴇ", callback_data="close_data"))
        buttons.append(nav_close_btns)

        m_type_str = "ᴛᴠ ꜱᴇʀɪᴇꜱ" if media_type == "tv" else "ᴍᴏᴠɪᴇ"
        tmdb_link = f"https://www.themoviedb.org/{media_type}/{tmdb_id}"

        caption = f"""
🧿 ᴛɪᴛʟᴇ: {title} 📅 ʏᴇᴀʀ: {year} 🏷️ ᴛʏᴘᴇ: {m_type_str}

🔗 ᴛᴍᴅʙ: <a href='{tmdb_link}'>Vɪᴇᴡ ᴏɴ TMDB</a>

👇 ꜱᴇʟᴇᴄᴛ ᴘᴏꜱᴛᴇʀ ᴄᴀᴛᴇɢᴏʀʏ ʙᴇʟᴏᴡ: """

        if callback_query.message.photo:
            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=main_poster, caption=caption, parse_mode=ParseMode.HTML),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await client.send_photo(
                chat_id=callback_query.message.chat.id,
                photo=main_poster,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            # Safe delete logic
            try:
                await callback_query.message.delete()
            except:
                pass

    except Exception as e:
        LOGGER.error(f"Menu Error: {e}")
        await callback_query.answer(f"ᴇʀʀᴏʀ: ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ!", show_alert=True)

@new_task
async def handle_poster_viewer(client, callback_query):
    tmdb_api_key = Config.TMDB_API_KEY
    if not tmdb_api_key:
        return await callback_query.answer("⚠️ ᴛᴍᴅʙ_ᴀᴘɪ_ᴋᴇʏ ɪꜱ ᴍɪꜱꜱɪɴɢ!", show_alert=True)

    data = callback_query.data.split("_")
    p_type = data[2]
    media_type = data[3]
    tmdb_id = data[4]
    current_index = int(data[5])
    short_query = data[6] if len(data) > 6 else ""

    await callback_query.answer("ꜰᴇᴛᴄʜɪɴɢ ɪᴍᴀɢᴇꜱ...")

    try:
        url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/images?api_key={tmdb_api_key}"
        response = await fetch_json(url)

        if not response:
            return await callback_query.answer("⚠️ ᴀᴘɪ ᴇʀʀᴏʀ!", show_alert=True)

        backdrops = response.get("backdrops", [])
        if p_type == "land":
            images = [img for img in backdrops if img.get("iso_639_1") not in (None, "xx")]
            # Ensure English is priority in viewing as well
            images.sort(key=lambda x: (0 if x.get("iso_639_1") == 'en' else 1, x.get("iso_639_1", "")))
            type_name = "ʟᴀɴᴅꜱᴄᴀᴘᴇ (ᴛʜᴜᴍʙɴᴀɪʟ)"
        elif p_type == "port":
            images = response.get("posters", [])
            type_name = "ᴘᴏʀᴛʀᴀɪᴛ"
        elif p_type == "logo":
            images = response.get("logos", [])
            type_name = "ʟᴏɢᴏꜱ"
        elif p_type == "clean":
            images = [img for img in backdrops if img.get("iso_639_1") in (None, "xx")]
            type_name = "ᴄʟᴇᴀɴ ʟᴀɴᴅꜱᴄᴀᴘᴇ"
        else:
            images = []

        if not images:
            return await callback_query.answer(f"⚠️ ɴᴏ {p_type.upper()} ꜰᴏᴜɴᴅ ꜰᴏʀ ᴛʜɪꜱ!", show_alert=True)

        # Loop around if index is out of range
        if current_index >= len(images): current_index = 0
        if current_index < 0: current_index = len(images) - 1

        img = images[current_index]
        # Fixed: Use w1280 for stable loading on Telegram servers
        img_url = f"https://image.tmdb.org/t/p/w1280{img['file_path']}"
        original_url = f"https://image.tmdb.org/t/p/original{img['file_path']}"

        details_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}?api_key={tmdb_api_key}"
        details = await fetch_json(details_url)
        title = details.get("name") or details.get("title", "ᴜɴᴋɴᴏᴡɴ")

        lang = img.get('iso_639_1')
        lang_display = lang.upper() if lang and lang != "xx" else 'ɴᴏɴᴇ / ᴄʟᴇᴀɴ'

        caption = f"""
🧿 ᴛɪᴛʟᴇ: {title}

🎨 ᴄᴀᴛᴇɢᴏʀʏ: {type_name} 🌐 ʟᴀɴɢᴜᴀɢᴇ: {lang_display} 📏 ʀᴇꜱᴏʟᴜᴛɪᴏɴ: {img.get('width')}x{img.get('height')}

📥 ᴏʀɪɢɪɴᴀʟ ʟɪɴᴋ: <a href='{original_url}'>Dᴏᴡɴʟᴏᴀᴅ Hᴇʀᴇ</a> """

        nav_btns = []
        if len(images) > 1:
            nav_btns.append(InlineKeyboardButton("⏮️", callback_data=f"p_view_{p_type}_{media_type}_{tmdb_id}_0_{short_query}"))
            nav_btns.append(InlineKeyboardButton("◀️", callback_data=f"p_view_{p_type}_{media_type}_{tmdb_id}_{current_index - 1}_{short_query}"))

        nav_btns.append(InlineKeyboardButton(f"{current_index + 1} / {len(images)}", callback_data="none_data"))

        if len(images) > 1:
            nav_btns.append(InlineKeyboardButton("▶️", callback_data=f"p_view_{p_type}_{media_type}_{tmdb_id}_{current_index + 1}_{short_query}"))
            nav_btns.append(InlineKeyboardButton("⏭️", callback_data=f"p_view_{p_type}_{media_type}_{tmdb_id}_{len(images) - 1}_{short_query}"))

        buttons = [nav_btns]
        buttons.append([
            InlineKeyboardButton("🔙 ʙᴀᴄᴋ ᴛᴏ ᴍᴇɴᴜ", callback_data=f"p_menu_{media_type}_{tmdb_id}_{short_query}"),
            InlineKeyboardButton("❌ ᴄʟᴏꜱᴇ", callback_data="close_data")
        ])

        try:
            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=img_url, caption=caption, parse_mode=ParseMode.HTML),
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        except Exception:
            # Fallback for CURL failure: try a smaller size if 1280 also fails
            small_img_url = f"https://image.tmdb.org/t/p/w780{img['file_path']}"
            await callback_query.message.edit_media(
                media=InputMediaPhoto(media=small_img_url, caption=caption, parse_mode=ParseMode.HTML),
                reply_markup=InlineKeyboardMarkup(buttons)
            )

    except Exception as e:
        LOGGER.error(f"Viewer Error: {e}")
        await callback_query.answer(f"ᴇʀʀᴏʀ: ꜱᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ!", show_alert=True)

@new_task
async def ignore_callback(client, callback_query):
    await callback_query.answer()

@new_task
async def close_callback(client, callback_query):
    try:
        await callback_query.message.delete()
    except Exception:
        await callback_query.answer("⚠️ I don't have permission to delete this message!", show_alert=True)
