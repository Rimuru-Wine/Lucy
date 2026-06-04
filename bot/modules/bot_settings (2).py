from asyncio import (
    create_subprocess_exec,
    create_subprocess_shell,
    gather,
    sleep,
)
from pyrogram.enums import ButtonStyle
from functools import partial
from io import BytesIO
from os import getcwd
from time import time

from aiofiles import open as aiopen
from aiofiles.os import path as aiopath
from aiofiles.os import remove, rename
from aioshutil import rmtree
from pyrogram.filters import create
from pyrogram.handlers import MessageHandler

from .. import (
    LOGGER,
    aria2_options,
    drives_ids,
    drives_names,
    index_urls,
    intervals,
    jd_listener_lock,
    nzb_options,
    qbit_options,
    sabnzbd_client,
    task_dict,
    shortener_dict,
    excluded_extensions,
    auth_chats,
    sudo_users,
)
from ..helper.ext_utils.bot_utils import (
    SetInterval,
    new_task,
)
from ..core.config_manager import Config
from ..core.tg_client import TgClient
from ..core.torrent_manager import TorrentManager
from ..core.startup import update_qb_options, update_nzb_options, update_variables
from ..helper.ext_utils.db_handler import database
from ..core.jdownloader_booter import jdownloader
from ..helper.ext_utils.task_manager import start_from_queued
from ..helper.mirror_leech_utils.rclone_utils.serve import rclone_serve_booter
from ..helper.ext_utils.style import SFMLStyle
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_file,
    send_message,
    update_status_message,
)
from .rss import add_job
from .search import initiate_search_tools

start = 0
state = "view"
handler_dict = {}
THEME_VARS = [
    "START_MESSAGE",
    "ABOUT_TEXT",
    "START_PIC",
    "ABOUT_PIC",
    "SETTINGS_PIC",
    "TASK_PIC",
]
LIMIT_VARS = [
    "DIRECT_LIMIT",
    "MEGA_LIMIT",
    "TORRENT_LIMIT",
    "GD_DL_LIMIT",
    "RC_DL_LIMIT",
    "CLONE_LIMIT",
    "JD_LIMIT",
    "NZB_LIMIT",
    "YTDLP_LIMIT",
    "PLAYLIST_LIMIT",
    "LEECH_LIMIT",
    "EXTRACT_LIMIT",
    "ARCHIVE_LIMIT",
    "STORAGE_LIMIT",
    "USER_MAX_TASKS",
    "BOT_MAX_TASKS",
    "USER_TIME_INTERVAL",
    "RSS_SIZE_LIMIT",
]
VALUE_VARS = [
    "AS_DOCUMENT",
    "BOT_PM",
    "DEFAULT_UPLOAD",
    "EQUAL_SPLITS",
    "LEECH_SPLIT_SIZE",
    "MEDIA_GROUP",
    "RSS_DELAY",
    "SEARCH_LIMIT",
    "STATUS_UPDATE_INTERVAL",
    "STOP_DUPLICATE",
    "UPSTREAM_BRANCH",
    "QUEUE_ALL",
    "QUEUE_DOWNLOAD",
    "QUEUE_UPLOAD",
    "HYBRID_LEECH",
]
DEFAULT_VALUES = {
    "LEECH_SPLIT_SIZE": TgClient.MAX_SPLIT_SIZE,
    "RSS_DELAY": 600,
    "STATUS_UPDATE_INTERVAL": 15,
    "SEARCH_LIMIT": 0,
    "UPSTREAM_BRANCH": "master",
    "DEFAULT_UPLOAD": "rc",
    "BOT_MAX_TASKS": 0,
    "QUEUE_ALL": 0,
    "QUEUE_DOWNLOAD": 0,
    "QUEUE_UPLOAD": 0,
    "USER_MAX_TASKS": 0,
}


async def get_buttons(key=None, edit_type=None, edit_mode=False):
    buttons = ButtonMaker()
    if key is None:
        buttons.data_button(SFMLStyle.VAR_SET_BT, "botset var")
        buttons.data_button(SFMLStyle.LIMIT_SET_BT, "botset limit")
        buttons.data_button(SFMLStyle.VALUE_SET_BT, "botset value")
        buttons.data_button(SFMLStyle.PRIVATE_BT, "botset private open")
        buttons.data_button(SFMLStyle.QBIT_SET_BT, "botset qbit")
        buttons.data_button(SFMLStyle.ARIA_SET_BT, "botset aria")
        buttons.data_button(SFMLStyle.NZB_SET_BT, "botset nzb")
        buttons.data_button(SFMLStyle.SYNC_JD_BT, "botset syncjd")
        buttons.data_button(SFMLStyle.THEME_SET_BT, "botset theme")
        buttons.data_button(SFMLStyle.CLOSE_BT, "botset close", style=ButtonStyle.DANGER)
        msg = SFMLStyle.BOT_SET_BT + ":"
    elif edit_type is not None:
        if edit_type == "botvar":
            msg = ""
            if key in THEME_VARS:
                return_key = "theme"
            elif key in LIMIT_VARS:
                return_key = "limit"
            elif key in VALUE_VARS:
                return_key = "value"
            else:
                return_key = "var"
            buttons.data_button(SFMLStyle.BACK_BT, f"botset {return_key}")
            if key not in ["TELEGRAM_HASH", "TELEGRAM_API", "OWNER_ID", "BOT_TOKEN"]:
                buttons.data_button("𝖣𝖾𝖿𝖺𝗎𝗅𝗍", f"botset resetvar {key}")
            buttons.data_button(SFMLStyle.CLOSE_BT, "botset close", style=ButtonStyle.DANGER)
            if key in [
                "CMD_SUFFIX",
                "OWNER_ID",
                "USER_SESSION_STRING",
                "TELEGRAM_HASH",
                "TELEGRAM_API",
                "BOT_TOKEN",
                "TG_PROXY",
            ]:
                msg += "Restart required for this edit to take effect! You will not see the changes in bot vars, the edit will be in database only!\n\n"
            msg += f"Send a valid value for {key}. Current value is '{Config.get(key)}'. Timeout: 60 sec"
        elif edit_type == "ariavar":
            buttons.data_button("Back", "botset aria")
            if key != "newkey":
                buttons.data_button("Empty String", f"botset emptyaria {key}")
            buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
            msg = (
                "Send a key with value. Example: https-proxy-user:value. Timeout: 60 sec"
                if key == "newkey"
                else f"Send a valid value for {key}. Current value is '{aria2_options[key]}'. Timeout: 60 sec"
            )
        elif edit_type == "qbitvar":
            buttons.data_button("Back", "botset qbit")
            buttons.data_button("Empty String", f"botset emptyqbit {key}")
            buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
            msg = f"Send a valid value for {key}. Current value is '{qbit_options[key]}'. Timeout: 60 sec"
        elif edit_type == "nzbvar":
            buttons.data_button("Back", "botset nzb")
            buttons.data_button("Default", f"botset resetnzb {key}")
            buttons.data_button("Empty String", f"botset emptynzb {key}")
            buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
            msg = f"Send a valid value for {key}. Current value is '{nzb_options[key]}'.\nIf the value is list then seperate them by space or ,\nExample: .exe,info or .exe .info\nTimeout: 60 sec"
        elif edit_type.startswith("nzbsevar"):
            index = 0 if key == "newser" else int(edit_type.replace("nzbsevar", ""))
            buttons.data_button("Back", f"botset nzbser{index}")
            if key != "newser":
                buttons.data_button("Empty", f"botset emptyserkey {index} {key}")
            buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
            if key == "newser":
                msg = "Send one server as dictionary {}, like in config.py without []. Timeout: 60 sec"
            else:
                msg = f"Send a valid value for {key} in server {Config.USENET_SERVERS[index]['name']}. Current value is {Config.USENET_SERVERS[index][key]}. Timeout: 60 sec"
    elif key == "theme":
        for k in THEME_VARS:
            buttons.data_button(k, f"botset botvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit theme", style=ButtonStyle.PRIMARY)
        else:
            buttons.data_button("View", "botset view theme", style=ButtonStyle.PRIMARY)
        buttons.data_button(SFMLStyle.BACK_BT, "botset back")
        buttons.data_button(SFMLStyle.CLOSE_BT, "botset close", style=ButtonStyle.DANGER)
        msg = f"{SFMLStyle.THEME_SET_BT} | State: {state}"
    elif key == "var":
        conf_dict = {
            k: v
            for k, v in Config.get_all().items()
            if k not in LIMIT_VARS and k not in VALUE_VARS and k not in THEME_VARS
        }
        for k in list(conf_dict.keys())[start : 10 + start]:
            if k == "DATABASE_URL" and state != "view":
                continue
            buttons.data_button(k, f"botset botvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit var", style=ButtonStyle.PRIMARY)
        else:
            buttons.data_button("View", "botset view var", style=ButtonStyle.PRIMARY)
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
        for x in range(0, len(conf_dict), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start var {x}", position="footer"
            )
        msg = f"Config Variables | Page: {int(start / 10)} | State: {state}"
    elif key == "limit":
        conf_dict = {k: v for k, v in Config.get_all().items() if k in LIMIT_VARS}
        for k in list(conf_dict.keys())[start : 10 + start]:
            buttons.data_button(k, f"botset botvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit limit", style=ButtonStyle.PRIMARY)
        else:
            buttons.data_button("View", "botset view limit", style=ButtonStyle.PRIMARY)
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
        for x in range(0, len(conf_dict), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start limit {x}", position="footer"
            )
        msg = f"Limit Settings | Page: {int(start / 10)} | State: {state}"
    elif key == "value":
        conf_dict = {k: v for k, v in Config.get_all().items() if k in VALUE_VARS}
        for k in list(conf_dict.keys())[start : 10 + start]:
            buttons.data_button(k, f"botset botvar {k}")
        if state == "view":
            buttons.data_button("Edit", "botset edit value", style=ButtonStyle.PRIMARY)
        else:
            buttons.data_button("View", "botset view value", style=ButtonStyle.PRIMARY)
        buttons.data_button("Back", "botset back")
        buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
        for x in range(0, len(conf_dict), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start value {x}", position="footer"
            )
        msg = f"Values Settings | Page: {int(start / 10)} | State: {state}"
    elif key == "private":
        if edit_mode:
            buttons.data_button("𝖲𝗍𝗈𝗉 𝖨𝗇𝗏𝗈𝗄𝖾 𝖥𝗂𝗅𝖾", "botset private stop", "header")
        else:
            buttons.data_button("𝖢𝗋𝖾𝖺𝗍𝖾 𝖭𝖾𝗐 𝖥𝗂𝗅𝖾", "botset private new")
            buttons.data_button("𝖠𝖽𝖽/𝖣𝖾𝗅𝖾𝗍𝖾 𝖥𝗂𝗅𝖾", "botset private edit")
        buttons.data_button(SFMLStyle.BACK_BT, "botset back", position="footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, "botset close", position="footer", style=ButtonStyle.DANGER
        )
        txt = "\n┠ ".join(
            [
                f"<code>{fn}</code> → <b>{'𝖤𝗑𝗂𝗌𝗍𝗌' if await aiopath.isfile(fn) else '𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌'}</b>"
                for fn in [
                    "config.py",
                    "token.pickle",
                    "rclone.conf",
                    "accounts.zip",
                    "list_drives.txt",
                    "shortener.txt",
                    "cookies.txt",
                    ".netrc",
                ]
            ]
        )
        msg = SFMLStyle.PRIVATE_FILES.format(txt=txt)
        if edit_mode:
            msg += "\n\n<i>𝖲𝖾𝗇𝖽 the 𝖿𝗂𝗅𝖾 𝗇𝖺𝗆𝖾 𝗍𝗈 𝖽𝖾𝗅𝖾𝗍𝖾 𝗍𝗁𝖾 𝖿𝗂𝗅𝖾, 𝖿𝗂𝗅𝖾 𝗍𝗈 𝗌𝖺𝗏𝖾 𝗍𝗁𝖾 𝖿𝗂𝗅𝖾 & 𝖿𝗈𝗋 𝗇𝖾𝗐 𝖿𝗂𝗅𝖾 𝖼𝗋𝖾𝖺𝗍𝖾, 𝖿𝗈𝗅𝗅𝗈𝗐 𝖻𝖾𝗅𝗈𝗐 𝖿𝗈𝗋𝗆𝖺𝗍.</i> \n\n<b>𝖥𝗈𝗋𝗆𝖺𝗍:</b> \n𝖿𝗂𝗅𝖾_𝗇𝖺𝗆𝖾\n\n𝖼𝗈𝗇𝗍𝖾𝗇𝗍𝗌 𝗈𝖿 𝖿𝗂𝗅𝖾</i>\n\n<b>𝖳𝗂𝗆𝖾 𝖫𝖾𝖿𝗍 :</b> <code>60 𝗌𝖾𝖼</code>"
    elif key == "aria":
        for k in list(aria2_options.keys())[start : 10 + start]:
            if k not in ["checksum", "index-out", "out", "pause", "select-file"]:
                buttons.data_button(k, f"botset ariavar {k}")
        if state == "view":
            buttons.data_button(SFMLStyle.CHANGE_BT, "botset edit aria")
        else:
            buttons.data_button("𝖵𝗂𝖾𝗐", "botset view aria")
        buttons.data_button("𝖠𝖽𝖽 𝗇𝖾𝗐 𝗄𝖾𝗒", "botset ariavar newkey")
        buttons.data_button(SFMLStyle.BACK_BT, "botset back")
        buttons.data_button(SFMLStyle.CLOSE_BT, "botset close", style=ButtonStyle.DANGER)
        for x in range(0, len(aria2_options), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start aria {x}", position="footer"
            )
        msg = f"Aria2c Options | Page: {int(start / 10)} | State: {state}"
    elif key == "qbit":
        for k in list(qbit_options.keys())[start : 10 + start]:
            buttons.data_button(k, f"botset qbitvar {k}")
        if state == "view":
            buttons.data_button(SFMLStyle.CHANGE_BT, "botset edit qbit")
        else:
            buttons.data_button("𝖵𝗂𝖾𝗐", "botset view qbit")
        buttons.data_button("𝖲𝗒𝗇𝖼 𝖰𝖻𝗂𝗍𝗍𝗈𝗋𝗋𝖾𝗇𝗍", "botset syncqbit")
        buttons.data_button(SFMLStyle.BACK_BT, "botset back")
        buttons.data_button(SFMLStyle.CLOSE_BT, "botset close", style=ButtonStyle.DANGER)
        for x in range(0, len(qbit_options), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start qbit {x}", position="footer"
            )
        msg = f"Qbittorrent Options | Page: {int(start / 10)} | State: {state}"
    elif key == "nzb":
        for k in list(nzb_options.keys())[start : 10 + start]:
            buttons.data_button(k, f"botset nzbvar {k}")
        if state == "view":
            buttons.data_button(SFMLStyle.CHANGE_BT, "botset edit nzb")
        else:
            buttons.data_button("𝖵𝗂𝖾𝗐", "botset view nzb")
        buttons.data_button("𝖲𝖾𝗋𝗏𝖾𝗋𝗌", "botset nzbserver")
        buttons.data_button("𝖲𝗒𝗇𝖼 𝖲𝖺𝖻𝗇𝗓𝖻𝖽", "botset syncnzb")
        buttons.data_button(SFMLStyle.BACK_BT, "botset back")
        buttons.data_button(SFMLStyle.CLOSE_BT, "botset close", style=ButtonStyle.DANGER)
        for x in range(0, len(nzb_options), 10):
            buttons.data_button(
                f"{int(x / 10)}", f"botset start nzb {x}", position="footer"
            )
        msg = f"Sabnzbd Options | Page: {int(start / 10)} | State: {state}"
    elif key == "nzbserver":
        if len(Config.USENET_SERVERS) > 0:
            for index, k in enumerate(Config.USENET_SERVERS[start : 10 + start]):
                buttons.data_button(k["name"], f"botset nzbser{index}")
        buttons.data_button("𝖠𝖽𝖽 𝖭𝖾𝗐", "botset nzbsevar newser")
        buttons.data_button(SFMLStyle.BACK_BT, "botset nzb")
        buttons.data_button(SFMLStyle.CLOSE_BT, "botset close", style=ButtonStyle.DANGER)
        if len(Config.USENET_SERVERS) > 10:
            for x in range(0, len(Config.USENET_SERVERS), 10):
                buttons.data_button(
                    f"{int(x / 10)}", f"botset start nzbser {x}", position="footer"
                )
        msg = f"Usenet Servers | Page: {int(start / 10)} | State: {state}"
    elif key.startswith("nzbser"):
        index = int(key.replace("nzbser", ""))
        LOGGER.info(f"Data: {key}, {index}")
        if index >= len(Config.USENET_SERVERS):
            return await get_buttons("nzbserver")
        for k in list(Config.USENET_SERVERS[index].keys())[start : 10 + start]:
            buttons.data_button(k, f"botset nzbsevar{index} {k}")
        if state == "view":
            buttons.data_button("Edit", f"botset edit {key}")
        else:
            buttons.data_button("View", f"botset view {key}")
        buttons.data_button("Remove Server", f"botset remser {index}")
        buttons.data_button("Back", "botset nzbserver")
        buttons.data_button("Close", "botset close", style=ButtonStyle.DANGER)
        if len(Config.USENET_SERVERS[index].keys()) > 10:
            for x in range(0, len(Config.USENET_SERVERS[index]), 10):
                buttons.data_button(
                    f"{int(x / 10)}", f"botset start {key} {x}", position="footer"
                )
        msg = f"Server Keys | Page: {int(start / 10)} | State: {state}"

    return msg, buttons.build_menu(1 if key is None else 2)


async def update_buttons(message, key=None, edit_type=None, edit_mode=False):
    msg, button = await get_buttons(key, edit_type, edit_mode)
    if not key and not edit_type and not edit_mode:
        await edit_message(message, msg, button, photo=Config.SETTINGS_PIC)
    else:
        await edit_message(message, msg, button)


@new_task
async def edit_variable(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
        if key == "INCOMPLETE_TASK_NOTIFIER" and Config.DATABASE_URL:
            await database.trunc_table("tasks")
    elif key == "STATUS_UPDATE_INTERVAL":
        value = int(value)
        if len(task_dict) != 0 and (st := intervals["status"]):
            for cid, intvl in list(st.items()):
                intvl.cancel()
                intervals["status"][cid] = SetInterval(
                    value, update_status_message, cid
                )
    elif key == "TORRENT_TIMEOUT":
        await TorrentManager.change_aria2_option("bt-stop-timeout", value)
        value = int(value)
    elif key == "LEECH_SPLIT_SIZE":
        value = min(int(value), TgClient.MAX_SPLIT_SIZE)
    elif key == "BASE_URL_PORT":
        value = int(value)
        if Config.BASE_URL:
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
            await create_subprocess_shell(
                f"gunicorn -k uvicorn.workers.UvicornWorker -w 1 web.wserver:app --bind 0.0.0.0:{value}"
            )
    elif key == "EXCLUDED_EXTENSIONS":
        fx = value.split()
        excluded_extensions.clear()
        excluded_extensions.extend(["aria2", "!qB"])
        for x in fx:
            x = x.lstrip(".")
            excluded_extensions.append(x.strip().lower())
    elif key == "GDRIVE_ID":
        if drives_names and drives_names[0] == "Main":
            drives_ids[0] = value
        else:
            drives_ids.insert(0, value)
    elif key == "INDEX_URL":
        if drives_names and drives_names[0] == "Main":
            index_urls[0] = value
        else:
            index_urls.insert(0, value)
    elif key == "LINKS_LOG_ID":
        if value.strip():
            try:
                value = int(value.strip())
            except ValueError:
                await send_message(
                    message,
                    "Invalid value! LINKS_LOG_ID must be a valid integer chat ID.",
                )
                return await update_buttons(pre_message, "var")
    elif key == "MIRROR_LOG_ID":
        if value.strip():
            try:
                value = int(value.strip())
            except ValueError:
                await send_message(
                    message,
                    "Invalid value! MIRROR_LOG_ID must be a valid integer chat ID.",
                )
                return await update_buttons(pre_message, "var")
    elif key == "AUTHORIZED_CHATS":
        aid = value.split()
        auth_chats.clear()
        for id_ in aid:
            chat_id, *thread_ids = id_.split("|")
            chat_id = int(chat_id.strip())
            if thread_ids:
                thread_ids = list(map(lambda x: int(x.strip()), thread_ids))
                auth_chats[chat_id] = thread_ids
            else:
                auth_chats[chat_id] = []
    elif key == "SUDO_USERS":
        sudo_users.clear()
        aid = value.split()
        for id_ in aid:
            sudo_users.append(int(id_.strip()))
    elif key == "LOGIN_PASS":
        value = str(value)
    elif key == "DEBRID_LINK_API":
        value = str(value)
    elif value.isdigit():
        value = int(value)
    elif value.startswith("[") and value.endswith("]"):
        value = eval(value)
    elif value.startswith("{") and value.endswith("}"):
        value = eval(value)
    Config.set(key, value)
    if key in THEME_VARS:
        return_key = "theme"
    elif key in LIMIT_VARS:
        return_key = "limit"
    elif key in VALUE_VARS:
        return_key = "value"
    else:
        return_key = "var"
    await update_buttons(pre_message, return_key)
    await delete_message(message)
    await database.update_config({key: value})
    if key in ["SEARCH_PLUGINS", "SEARCH_API_LINK"]:
        await initiate_search_tools()
    elif key in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
        await start_from_queued()
    elif key in [
        "RCLONE_SERVE_URL",
        "RCLONE_SERVE_PORT",
        "RCLONE_SERVE_USER",
        "RCLONE_SERVE_PASS",
    ]:
        await rclone_serve_booter()
    elif key in ["JD_EMAIL", "JD_PASS"]:
        await jdownloader.boot()
    elif key == "RSS_DELAY":
        add_job()
    elif key == "USENET_SERVERS":
        for s in value:
            await sabnzbd_client.set_special_config("servers", s)


@new_task
async def edit_aria(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == "newkey":
        key, value = [x.strip() for x in value.split(":", 1)]
    elif value.lower() == "true":
        value = "true"
    elif value.lower() == "false":
        value = "false"
    await TorrentManager.change_aria2_option(key, value)
    await update_buttons(pre_message, "aria")
    await delete_message(message)
    await database.update_aria2(key, value)


@new_task
async def edit_qbit(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    elif key == "max_ratio":
        value = float(value)
    elif value.isdigit():
        value = int(value)
    await TorrentManager.qbittorrent.app.set_preferences({key: value})
    qbit_options[key] = value
    await update_buttons(pre_message, "qbit")
    await delete_message(message)
    await database.update_qbittorrent(key, value)


@new_task
async def edit_nzb(_, message, pre_message, key):
    handler_dict[message.chat.id] = False
    value = message.text
    if value.isdigit():
        value = int(value)
    elif value.startswith("[") and value.endswith("]"):
        try:
            value = ",".join(eval(value))
        except Exception as e:
            LOGGER.error(e)
            await update_buttons(pre_message, "nzb")
            return
    res = await sabnzbd_client.set_config("misc", key, value)
    nzb_options[key] = res["config"]["misc"][key]
    await update_buttons(pre_message, "nzb")
    await delete_message(message)
    await database.update_nzb_config()


@new_task
async def edit_nzb_server(_, message, pre_message, key, index=0):
    handler_dict[message.chat.id] = False
    value = message.text
    if key == "newser":
        if value.startswith("{") and value.endswith("}"):
            try:
                value = eval(value)
            except Exception:
                await send_message(message, "Invalid dict format!")
                await update_buttons(pre_message, "nzbserver")
                return
            res = await sabnzbd_client.add_server(value)
            if not res["config"]["servers"][0]["host"]:
                await send_message(message, "Invalid server!")
                await update_buttons(pre_message, "nzbserver")
                return
            Config.USENET_SERVERS.append(value)
            await update_buttons(pre_message, "nzbserver")
        else:
            await send_message(message, "Invalid dict format!")
            await update_buttons(pre_message, "nzbserver")
            return
    else:
        if value.isdigit():
            value = int(value)
        res = await sabnzbd_client.add_server(
            {"name": Config.USENET_SERVERS[index]["name"], key: value}
        )
        if res["config"]["servers"][0][key] == "":
            await send_message(message, "Invalid value")
            return
        Config.USENET_SERVERS[index][key] = value
        await update_buttons(pre_message, f"nzbser{index}")
    await delete_message(message)
    await database.update_config({"USENET_SERVERS": Config.USENET_SERVERS})


async def sync_jdownloader():
    async with jd_listener_lock:
        if not Config.DATABASE_URL or not jdownloader.is_connected:
            return
        await jdownloader.device.system.exit_jd()
    if await aiopath.exists("cfg.zip"):
        await remove("cfg.zip")
    await (
        await create_subprocess_exec("7z", "a", "cfg.zip", "/JDownloader/cfg")
    ).wait()
    await database.update_private_file("cfg.zip")


@new_task
async def update_private_file(_, message, pre_message, key, new_file=False):
    handler_dict[message.chat.id] = False
    if not message.media and (file_name := message.text):
        if new_file:
            file_name, content = file_name.split("\n", 1)
            file_name = file_name.strip()
            async with aiopen(file_name, "w") as f:
                await f.write(content.strip())
        else:
            if await aiopath.isfile(file_name) and file_name != "config.py":
                await remove(file_name)
            if file_name == "accounts.zip":
                if await aiopath.exists("accounts"):
                    await rmtree("accounts", ignore_errors=True)
                if await aiopath.exists("rclone_sa"):
                    await rmtree("rclone_sa", ignore_errors=True)
                Config.USE_SERVICE_ACCOUNTS = False
                await database.update_config({"USE_SERVICE_ACCOUNTS": False})
            elif file_name in [".netrc", "netrc"]:
                await (await create_subprocess_exec("touch", ".netrc")).wait()
                await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
                await (
                    await create_subprocess_exec("cp", ".netrc", "/root/.netrc")
                ).wait()
        await delete_message(message)
    elif doc := message.document:
        file_name = doc.file_name
        fpath = f"{getcwd()}/{file_name}"
        if await aiopath.exists(fpath):
            await remove(fpath)
        await message.download(file_name=fpath)
        if file_name == "accounts.zip":
            if await aiopath.exists("accounts"):
                await rmtree("accounts", ignore_errors=True)
            if await aiopath.exists("rclone_sa"):
                await rmtree("rclone_sa", ignore_errors=True)
            await (
                await create_subprocess_exec(
                    "7z", "x", "-o.", "-aoa", "accounts.zip", "accounts/*.json"
                )
            ).wait()
            await (
                await create_subprocess_exec("chmod", "-R", "777", "accounts")
            ).wait()
        elif file_name in [".netrc", "netrc"]:
            if file_name == "netrc":
                await rename("netrc", ".netrc")
                file_name = ".netrc"
            await (await create_subprocess_exec("chmod", "600", ".netrc")).wait()
            await (await create_subprocess_exec("cp", ".netrc", "/root/.netrc")).wait()
        elif file_name == "config.py":
            await load_config()
        if "@github.com" in Config.UPSTREAM_REPO:
            buttons = ButtonMaker()
            msg = "Push to UPSTREAM_REPO ?"
            buttons.data_button("Yes!", f"botset push {file_name}")
            buttons.data_button("No", "botset close", style=ButtonStyle.DANGER)
            await send_message(message, msg, buttons.build_menu(2))
        else:
            await delete_message(message)
    if file_name == "rclone.conf":
        await rclone_serve_booter()
    elif file_name == "list_drives.txt" and await aiopath.exists("list_drives.txt"):
        drives_ids.clear()
        drives_names.clear()
        index_urls.clear()
        if Config.GDRIVE_ID:
            drives_names.append("Main")
            drives_ids.append(Config.GDRIVE_ID)
            index_urls.append(Config.INDEX_URL)
        async with aiopen("list_drives.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                drives_ids.append(temp[1])
                drives_names.append(temp[0].replace("_", " "))
                if len(temp) > 2:
                    index_urls.append(temp[2])
                else:
                    index_urls.append("")
    elif file_name == "shortener.txt" and await aiopath.exists("shortener.txt"):
        async with aiopen("shortener.txt", "r+") as f:
            lines = await f.readlines()
            for line in lines:
                temp = line.strip().split()
                if len(temp) == 2:
                    shortener_dict[temp[0]] = temp[1]
    await update_buttons(pre_message, key)
    await database.update_private_file(file_name)


async def event_handler(client, query, pfunc, rfunc, document=False):
    chat_id = query.message.chat.id
    handler_dict[chat_id] = True
    start_time = update_time = time()

    async def event_filter(_, __, event):
        user = event.from_user or event.sender_chat
        return bool(
            user.id == query.from_user.id
            and event.chat.id == chat_id
            and (event.text or event.document and document)
        )

    handler = client.add_handler(
        MessageHandler(pfunc, filters=create(event_filter)), group=-1
    )
    while handler_dict[chat_id]:
        await sleep(0.5)

        if time() - start_time > 60:
            handler_dict[chat_id] = False
            await rfunc()
        elif document:
            if time() - update_time > 6 and handler_dict[chat_id]:
                update_time = time()
                msg = await client.get_messages(chat_id, query.message.id)
                text = msg.text.split("\n")
                text[-1] = (
                    f"<b>Time Left :</b> <code>{round(60 - (time() - start_time), 2)} sec</code>"
                )
                await edit_message(msg, "\n".join(text), msg.reply_markup)
    client.remove_handler(*handler)


@new_task
async def edit_bot_settings(client, query):
    data = query.data.split()
    message = query.message
    handler_dict[message.chat.id] = False
    if data[1] == "close":
        await query.answer()
        await delete_message(message.reply_to_message)
        await delete_message(message)
    elif data[1] == "back":
        await query.answer()
        globals()["start"] = 0
        await update_buttons(message, None)
    elif data[1] == "syncjd":
        if not Config.JD_EMAIL or not Config.JD_PASS:
            await query.answer(
                "No Email or Password provided!",
                show_alert=True,
            )
            return
        await query.answer(
            "Syncronization Started. JDownloader will get restarted. It takes up to 10 sec!",
            show_alert=True,
        )
        await sync_jdownloader()
    elif (
        data[1] in ["var", "limit", "value", "theme", "aria", "qbit", "nzb", "nzbserver"]
        or data[1].startswith("nzbser")
    ):
        if data[1] == "nzbserver":
            globals()["start"] = 0
        await query.answer()
        await update_buttons(message, data[1])
    elif data[1] == "resetvar":
        await query.answer()
        value = ""
        if data[2] in DEFAULT_VALUES:
            value = DEFAULT_VALUES[data[2]]
            if (
                data[2] == "STATUS_UPDATE_INTERVAL"
                and len(task_dict) != 0
                and (st := intervals["status"])
            ):
                for key, intvl in list(st.items()):
                    intvl.cancel()
                    intervals["status"][key] = SetInterval(
                        value, update_status_message, key
                    )
        elif data[2] == "RSS_SIZE_LIMIT":
            value = 0
        elif data[2] == "EXCLUDED_EXTENSIONS":
            excluded_extensions.clear()
            excluded_extensions.extend(["aria2", "!qB"])
        elif data[2] == "TORRENT_TIMEOUT":
            await TorrentManager.change_aria2_option("bt-stop-timeout", "0")
            await database.update_aria2("bt-stop-timeout", "0")
        elif data[2] == "BASE_URL":
            await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
        elif data[2] == "BASE_URL_PORT":
            value = 80
            if Config.BASE_URL:
                await (
                    await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")
                ).wait()
                await create_subprocess_shell(
                    f"gunicorn -k uvicorn.workers.UvicornWorker -w 1 web.wserver:app --bind 0.0.0.0:{value}"
                )
        elif data[2] == "GDRIVE_ID":
            if drives_names and drives_names[0] == "Main":
                drives_names.pop(0)
                drives_ids.pop(0)
                index_urls.pop(0)
        elif data[2] == "INDEX_URL":
            if drives_names and drives_names[0] == "Main":
                index_urls[0] = ""
        elif data[2] == "INCOMPLETE_TASK_NOTIFIER":
            await database.trunc_table("tasks")
        elif data[2] in ["JD_EMAIL", "JD_PASS"]:
            await create_subprocess_exec("pkill", "-9", "-f", "java")
        elif data[2] == "USENET_SERVERS":
            for s in Config.USENET_SERVERS:
                await sabnzbd_client.delete_config("servers", s["name"])
        elif data[2] == "AUTHORIZED_CHATS":
            auth_chats.clear()
        elif data[2] == "SUDO_USERS":
            sudo_users.clear()
        Config.set(data[2], value)
        if data[2] in THEME_VARS:
            return_key = "theme"
        elif data[2] in LIMIT_VARS:
            return_key = "limit"
        elif data[2] in VALUE_VARS:
            return_key = "value"
        else:
            return_key = "var"
        await update_buttons(message, return_key)
        if data[2] == "DATABASE_URL":
            await database.disconnect()
        await database.update_config({data[2]: value})
        if data[2] in ["SEARCH_PLUGINS", "SEARCH_API_LINK"]:
            await initiate_search_tools()
        elif data[2] in ["QUEUE_ALL", "QUEUE_DOWNLOAD", "QUEUE_UPLOAD"]:
            await start_from_queued()
        elif data[2] in [
            "RCLONE_SERVE_URL",
            "RCLONE_SERVE_PORT",
            "RCLONE_SERVE_USER",
            "RCLONE_SERVE_PASS",
        ]:
            await rclone_serve_booter()
    elif data[1] == "resetnzb":
        await query.answer()
        res = await sabnzbd_client.set_config_default(data[2])
        nzb_options[data[2]] = res["config"]["misc"][data[2]]
        await update_buttons(message, "nzb")
        await database.update_nzb_config()
    elif data[1] == "syncnzb":
        if not Config.USENET_SERVERS:
            return await query.answer(
                "Syncronization Paused. No USENET_SERVERS is provided !"
            )
        await query.answer(
            "Syncronization Started. It takes up to 2 sec!", show_alert=True
        )
        nzb_options.clear()
        await update_nzb_options()
        await database.update_nzb_config()
    elif data[1] == "syncqbit":
        await query.answer(
            "Syncronization Started. It takes up to 2 sec!", show_alert=True
        )
        qbit_options.clear()
        await update_qb_options()
        await database.save_qbit_settings()
    elif data[1] == "emptyaria":
        await query.answer()
        aria2_options[data[2]] = ""
        await update_buttons(message, "aria")
        await TorrentManager.change_aria2_option(data[2], "")
        await database.update_aria2(data[2], "")
    elif data[1] == "emptyqbit":
        await query.answer()
        await TorrentManager.qbittorrent.app.set_preferences({data[2]: value})
        qbit_options[data[2]] = ""
        await update_buttons(message, "qbit")
        await database.update_qbittorrent(data[2], "")
    elif data[1] == "emptynzb":
        await query.answer()
        res = await sabnzbd_client.set_config("misc", data[2], "")
        nzb_options[data[2]] = res["config"]["misc"][data[2]]
        await update_buttons(message, "nzb")
        await database.update_nzb_config()
    elif data[1] == "remser":
        index = int(data[2])
        await sabnzbd_client.delete_config(
            "servers", Config.USENET_SERVERS[index]["name"]
        )
        del Config.USENET_SERVERS[index]
        await update_buttons(message, "nzbserver")
        await database.update_config({"USENET_SERVERS": Config.USENET_SERVERS})
    elif data[1] == "private":
        await query.answer()
        if data[2] in ("open", "stop"):
            await update_buttons(message, data[1])
        elif data[2] in ("edit", "new"):
            await update_buttons(message, data[1], edit_mode=True)
            pfunc = partial(
                update_private_file,
                pre_message=message,
                key=data[1],
                new_file=data[2] == "new",
            )
            rfunc = partial(update_buttons, message, data[1])
            await event_handler(client, query, pfunc, rfunc, True)
    elif data[1] == "botvar" and state == "edit":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_variable, pre_message=message, key=data[2])
        if data[2] in THEME_VARS:
            return_key = "theme"
        elif data[2] in LIMIT_VARS:
            return_key = "limit"
        elif data[2] in VALUE_VARS:
            return_key = "value"
        else:
            return_key = "var"
        rfunc = partial(update_buttons, message, return_key)
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "botvar" and state == "view":
        value = f"{Config.get(data[2])}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "ariavar" and (state == "edit" or data[2] == "newkey"):
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_aria, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "aria")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "ariavar" and state == "view":
        value = f"{aria2_options[data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "qbitvar" and state == "edit":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_qbit, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "qbit")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "qbitvar" and state == "view":
        value = f"{qbit_options[data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "nzbvar" and state == "edit":
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_nzb, pre_message=message, key=data[2])
        rfunc = partial(update_buttons, message, "nzb")
        await event_handler(client, query, pfunc, rfunc)
    elif data[1] == "nzbvar" and state == "view":
        value = f"{nzb_options[data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "emptyserkey":
        await query.answer()
        await update_buttons(message, f"nzbser{data[2]}")
        index = int(data[2])
        res = await sabnzbd_client.add_server(
            {"name": Config.USENET_SERVERS[index]["name"], data[3]: ""}
        )
        Config.USENET_SERVERS[index][data[3]] = res["config"]["servers"][0][data[3]]
        await database.update_config({"USENET_SERVERS": Config.USENET_SERVERS})
    elif data[1].startswith("nzbsevar") and (state == "edit" or data[2] == "newser"):
        index = 0 if data[2] == "newser" else int(data[1].replace("nzbsevar", ""))
        await query.answer()
        await update_buttons(message, data[2], data[1])
        pfunc = partial(edit_nzb_server, pre_message=message, key=data[2], index=index)
        LOGGER.info(f"Query Data: {data[1]}")
        rfunc = partial(update_buttons, message, data[1])
        await event_handler(client, query, pfunc, rfunc)
    elif data[1].startswith("nzbsevar") and state == "view":
        index = int(data[1].replace("nzbsevar", ""))
        value = f"{Config.USENET_SERVERS[index][data[2]]}"
        if len(value) > 200:
            await query.answer()
            with BytesIO(str.encode(value)) as out_file:
                out_file.name = f"{data[2]}.txt"
                await send_file(message, out_file)
            return
        elif value == "":
            value = None
        await query.answer(f"{value}", show_alert=True)
    elif data[1] == "edit":
        await query.answer()
        globals()["state"] = "edit"
        await update_buttons(message, data[2])
    elif data[1] == "view":
        await query.answer()
        globals()["state"] = "view"
        await update_buttons(message, data[2])
    elif data[1] == "start":
        await query.answer()
        if start != int(data[3]):
            globals()["start"] = int(data[3])
            await update_buttons(message, data[2])
    elif data[1] == "push":
        await query.answer()
        filename = data[2].rsplit(".zip", 1)[0]
        if await aiopath.exists(filename):
            await (await create_subprocess_shell(f"git add -f {filename} \
                    && git commit -sm botsettings -q \
                    && git push origin {Config.UPSTREAM_BRANCH} -qf")).wait()
        else:
            await (await create_subprocess_shell(f"git rm -r --cached {filename} \
                    && git commit -sm botsettings -q \
                    && git push origin {Config.UPSTREAM_BRANCH} -qf")).wait()
        await delete_message(message.reply_to_message)
        await delete_message(message)


@new_task
async def send_bot_settings(_, message):
    handler_dict[message.chat.id] = False
    msg, button = await get_buttons()
    globals()["start"] = 0
    await send_message(message, msg, button, photo=Config.SETTINGS_PIC)


async def load_config():
    Config.load()
    drives_ids.clear()
    drives_names.clear()
    index_urls.clear()
    await update_variables()

    if not await aiopath.exists("accounts"):
        Config.USE_SERVICE_ACCOUNTS = False

    if len(task_dict) != 0 and (st := intervals["status"]):
        for key, intvl in list(st.items()):
            intvl.cancel()
            intervals["status"][key] = SetInterval(
                Config.STATUS_UPDATE_INTERVAL, update_status_message, key
            )

    if Config.TORRENT_TIMEOUT:
        await TorrentManager.change_aria2_option(
            "bt-stop-timeout", f"{Config.TORRENT_TIMEOUT}"
        )
        await database.update_aria2("bt-stop-timeout", f"{Config.TORRENT_TIMEOUT}")

    if not Config.INCOMPLETE_TASK_NOTIFIER:
        await database.trunc_table("tasks")

    await (await create_subprocess_exec("pkill", "-9", "-f", "gunicorn")).wait()
    if Config.BASE_URL:
        await create_subprocess_shell(
            f"gunicorn -k uvicorn.workers.UvicornWorker -w 1 web.wserver:app --bind 0.0.0.0:{Config.BASE_URL_PORT}"
        )

    if Config.DATABASE_URL:
        await database.connect()
        config_dict = Config.get_all()
        await database.update_config(config_dict)
    else:
        await database.disconnect()
    await gather(initiate_search_tools(), start_from_queued(), rclone_serve_booter())
    add_job()
