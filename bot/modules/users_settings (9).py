from asyncio import sleep
from pyrogram.enums import ButtonStyle
from functools import partial
from html import escape
from io import BytesIO
from os import getcwd
from re import sub
from time import time

from aiofiles.os import makedirs, remove
from aiofiles.os import path as aiopath
from langcodes import Language
from pyrogram.filters import create
from pyrogram.handlers import MessageHandler

from bot.helper.ext_utils.status_utils import get_readable_file_size

from .. import auth_chats, excluded_extensions, sudo_users, user_data
from ..core.config_manager import Config
from ..core.tg_client import TgClient
from ..helper.ext_utils.bot_utils import (
    get_size_bytes,
    new_task,
    update_user_ldata,
)
from ..helper.ext_utils.db_handler import database
from ..helper.ext_utils.media_utils import create_thumb
from ..helper.ext_utils.style import SFMLStyle
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_file,
    send_message,
)

handler_dict = {}

leech_options = [
    "THUMBNAIL",
    "LEECH_SPLIT_SIZE",
    "LEECH_DUMP_CHAT",
    "LEECH_PREFIX",
    "LEECH_SUFFIX",
    "LEECH_CAPTION",
    "THUMBNAIL_LAYOUT",
    "AUTORENAME",
    "NAME_SWAP",
]
metadata_options = [
    "METADATA_TITLE",
    "METADATA_AUTHOR",
    "METADATA_ARTIST",
    "METADATA_AUDIO",
    "METADATA_SUBTITLE",
    "METADATA_VIDEO",
    "METADATA_ENCODED_BY",
    "METADATA_CUSTOM_TAG",
    "METADATA_COMMENT",
    "METADATA_DUBBED_BY",
    "METADATA_CHANNEL",
    "METADATA_WEBSITE",
    "METADATA_COPYRIGHT",
    "METADATA_PUBLISHER",
    "METADATA_ENCODER",
    "METADATA_SOURCE",
    "METADATA_STUDIO",
]
uphoster_options = [
    "GOFILE_TOKEN",
    "GOFILE_FOLDER_ID",
    "BUZZHEAVIER_TOKEN",
    "BUZZHEAVIER_FOLDER_ID",
    "PIXELDRAIN_KEY",
    "DEVUPLOADS_KEY",
    "DEVUPLOADS_FOLDER",
    "VIKINGFILE_HASH",
    "VIKINGFILE_FOLDER",
]
rclone_options = ["RCLONE_CONFIG", "RCLONE_PATH", "RCLONE_FLAGS"]
gdrive_options = ["TOKEN_PICKLE", "GDRIVE_ID", "INDEX_URL"]
advanced_options = [
    "EXCLUDED_EXTENSIONS",
    "YT_DLP_OPTIONS",
    "UPLOAD_PATHS",
    "USER_COOKIE_FILE",
]
yt_options = ["YT_DESP", "YT_TAGS", "YT_CATEGORY_ID", "YT_PRIVACY_STATUS"]

user_settings_text = {
    "THUMBNAIL": (
        "Photo or Doc",
        "Custom Thumbnail is used as the thumbnail for the files you upload to telegram in media or document mode.",
        "<i>Send a photo to save it as custom thumbnail.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "RCLONE_CONFIG": (
        "",
        "",
        "<i>Send your <code>rclone.conf</code> file to use as your Upload Dest to RClone.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "TOKEN_PICKLE": (
        "",
        "",
        "<i>Send your <code>token.pickle</code> to use as your Upload Dest to GDrive</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "LEECH_SPLIT_SIZE": (
        "",
        "",
        f"Send Leech split size in bytes or use gb or mb. Example: 40000000 or 2.5gb or 1000mb. PREMIUM_USER: {TgClient.IS_PREMIUM_USER}.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "LEECH_DUMP_CHAT": (
        "",
        "",
        """Send leech destination ID/USERNAME/PM. 
* b:id/@username/pm (b: means leech by bot) (id or username of the chat or write pm means private message so bot will send the files in private to you) when you should use b:(leech by bot)? When your default settings is leech by user and you want to leech by bot for specific task.
* u:id/@username(u: means leech by user) This incase OWNER added USER_STRING_SESSION.
* h:id/@username(hybrid leech) h: to upload files by bot and user based on file size.
* id/@username|topic_id(leech in specific chat and topic) add | without space and write topic id after chat id or username.
┖ <b>Time Left :</b> <code>60 sec</code>""",
    ),
    "LEECH_PREFIX": (
        "",
        "",
        "Send Leech Filename Prefix. You can add HTML tags. Example: <code>@mychannel</code>.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "LEECH_SUFFIX": (
        "",
        "",
        "Send Leech Filename Suffix. You can add HTML tags. Example: <code>@mychannel</code>.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "LEECH_CAPTION": (
        "",
        "",
        "Send Leech Caption. You can add HTML tags. Example: <code>@mychannel</code>.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "THUMBNAIL_LAYOUT": (
        "",
        "",
        "Send thumbnail layout (widthxheight, 2x2, 3x3, 2x4, 4x4, ...). Example: 3x3.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "RCLONE_PATH": (
        "",
        "",
        "Send Rclone Path. If you want to use your rclone config edit using owner/user config from usetting or add mrcc: before rclone path. Example mrcc:remote:folder. </i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "RCLONE_FLAGS": (
        "",
        "",
        "key:value|key|key|key:value . Check here all <a href='https://rclone.org/flags/'>RcloneFlags</a>\nEx: --buffer-size:8M|--drive-starred-only",
    ),
    "GDRIVE_ID": (
        "",
        "",
        "Send Gdrive ID. If you want to use your token.pickle edit using owner/user token from usetting or add mtp: before the id. Example: mtp:F435RGGRDXXXXXX . </i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "INDEX_URL": (
        "",
        "",
        "Send Index URL for your gdrive option. </i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "UPLOAD_PATHS": (
        "",
        "",
        "Send Dict of keys that have path values. Example: {'path 1': 'remote:rclonefolder', 'path 2': 'gdrive1 id', 'path 3': 'tg chat id', 'path 4': 'mrcc:remote:', 'path 5': b:@username} . </i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "EXCLUDED_EXTENSIONS": (
        "",
        "",
        "Send exluded extenions seperated by space without dot at beginning. </i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "NAME_SWAP": (
        "",
        "",
        """<i>Send your Name Swap. You can add pattern instead of normal text according to the format.</i>
<b>Full Documentation Guide</b> <a href="https://t.me/WZML_X/77">Click Here</a>
┖ <b>Time Left :</b> <code>60 sec</code>
""",
    ),
    "AUTORENAME": (
        "",
        "",
        """<i>Send your Autorename Format. You can use dynamic variables.</i>
<b>Dynamic Variables:</b>
• <code>{quality}</code> - Video quality
• <code>{audio}</code> - Audio language
• <code>{Season}</code> - Season number
• <code>{episode}</code> - Episode number
• <code>{filename}</code> - Original name

<b>Example:</b> <code>{filename} - {quality} - {audio} - S{Season}E{episode}</code>
┖ <b>Time Left :</b> <code>60 sec</code>""",
    ),
    "YT_DLP_OPTIONS": (
        "",
        "",
        """Format: {key: value, key: value, key: value}.
Example: {"format": "bv*+mergeall[vcodec=none]", "nocheckcertificate": True, "playliststart": 10, "fragment_retries": float("inf"), "matchtitle": "S13", "writesubtitles": True, "live_from_start": True, "postprocessor_args": {"ffmpeg": ["-threads", "4"]}, "wait_for_video": (5, 100), "download_ranges": [{"start_time": 0, "end_time": 10}]}
Check all yt-dlp api options from this <a href='https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/YoutubeDL.py#L184'>FILE</a> or use this <a href='https://t.me/mltb_official_channel/177'>script</a> to convert cli arguments to api options.

<i>Send dict of YT-DLP Options according to format.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>""",
    ),
    "FFMPEG_CMDS": (
        "",
        "",
        """Dict of list values of ffmpeg commands. You can set multiple ffmpeg commands for all files before upload. Don't write ffmpeg at beginning, start directly with the arguments.
Examples: {"subtitle": ["-i mltb.mkv -c copy -c:s srt mltb.mkv", "-i mltb.video -c copy -c:s srt mltb"], "convert": ["-i mltb.m4a -c:a libmp3lame -q:a 2 mltb.mp3", "-i mltb.audio -c:a libmp3lame -q:a 2 mltb.mp3"], extract: ["-i mltb -map 0:a -c copy mltb.mka -map 0:s -c copy mltb.srt"]}
Notes:
- Add `-del` to the list which you want from the bot to delete the original files after command run complete!
- To execute one of those lists in bot for example, you must use -ff subtitle (list key) or -ff convert (list key)
Here I will explain how to use mltb.* which is reference to files you want to work on.
1. First cmd: the input is mltb.mkv so this cmd will work only on mkv videos and the output is mltb.mkv also so all outputs is mkv. -del will delete the original media after complete run of the cmd.
2. Second cmd: the input is mltb.video so this cmd will work on all videos and the output is only mltb so the extenstion is same as input files.
3. Third cmd: the input in mltb.m4a so this cmd will work only on m4a audios and the output is mltb.mp3 so the output extension is mp3.
4. Fourth cmd: the input is mltb.audio so this cmd will work on all audios and the output is mltb.mp3 so the output extension is mp3.

<i>Send dict of FFMPEG_CMDS Options according to format.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>
""",
    ),
    "METADATA_CMDS": (
        "",
        "",
        """<i>Send your Meta data. You can according to the format title="Join @WZML_X".</i>
<b>Full Documentation Guide</b> <a href="https://t.me/WZML_X/">Click Here</a>
┖ <b>Time Left :</b> <code>60 sec</code>
""",
    ),
    "METADATA": (
        "🏷 Global Metadata (key=value|key=value)",
        "Apply metadata to all media files with dynamic variables.",
        """<i>📝 Send metadata as</i> <code>key=value|key2=value2</code>

<b>🔧 Dynamic Variables:</b>
• <code>{filename}</code> - Original filename
• <code>{basename}</code> - Name without extension
• <code>{audiolang}</code> - Audio language (English/Hindi etc.)
• <code>{year}</code> - Year from filename

<b>📋 Example:</b>
<code>title={basename}|artist={audiolang} Version|year={year}</code>

⏱ <b>Time Left:</b> <code>60 sec</code>""",
    ),
    "AUDIO_METADATA": (
        "🎵 Audio Stream Metadata",
        "Metadata applied to each audio track separately.",
        """<i>🎧 Audio stream metadata with per-track language support</i>

<b>📋 Example:</b>
<code>language={audiolang}|title=Audio - {audiolang}</code>

⏱ <b>Time Left:</b> <code>60 sec</code>""",
    ),
    "VIDEO_METADATA": (
        "🎥 Video Stream Metadata",
        "Metadata applied to video streams.",
        """<i>📹 Video stream metadata for visual tracks</i>

<b>📋 Example:</b>
<code>title={basename}|comment=HD Video</code>

⏱ <b>Time Left:</b> <code>60 sec</code>""",
    ),
    "SUBTITLE_METADATA": (
        "💬 Subtitle Stream Metadata",
        "Metadata applied to each subtitle track separately.",
        """<i>📄 Subtitle stream metadata with per-track language support</i>

<b>📋 Example:</b>
<code>language={sublang}|title=Subtitles - {sublang}</code>

⏱ <b>Time Left:</b> <code>60 sec</code>""",
    ),
    "YT_DESP": (
        "String",
        "Custom description for YouTube uploads. Default is used if not set.",
        "<i>Send your custom YouTube description.</i> \nTime Left : <code>60 sec</code>",
    ),
    "YT_TAGS": (
        "Comma-separated strings",
        "Custom tags for YouTube uploads (e.g., tag1,tag2,tag3). Default is used if not set.",
        "<i>Send your custom YouTube tags as a comma-separated list.</i> \nTime Left : <code>60 sec</code>",
    ),
    "YT_CATEGORY_ID": (
        "Number",
        "Custom category ID for YouTube uploads. Default is used if not set.",
        "<i>Send your custom YouTube category ID (e.g., 22).</i> \nTime Left : <code>60 sec</code>",
    ),
    "YT_PRIVACY_STATUS": (
        "public, private, or unlisted",
        "Custom privacy status for YouTube uploads. Default is used if not set.",
        "<i>Send your custom YouTube privacy status (public, private, or unlisted).</i> \nTime Left : <code>60 sec</code>",
    ),
    "USER_COOKIE_FILE": (
        "File",
        "User's YT-DLP Cookie File to authenticate access to websites and youtube.",
        "<i>Send your cookie file (e.g., cookies.txt or abc.txt).</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "GOFILE_TOKEN": (
        "String",
        "Gofile API Token",
        "<i>Send your Gofile API Token.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "GOFILE_FOLDER_ID": (
        "String",
        "Gofile Folder ID",
        "<i>Send your Gofile Folder ID. If empty, uploads to Root.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "BUZZHEAVIER_TOKEN": (
        "String",
        "BuzzHeavier API Token",
        "<i>Send your BuzzHeavier API Token (Account ID).</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "BUZZHEAVIER_FOLDER_ID": (
        "String",
        "BuzzHeavier Folder ID",
        "<i>Send your BuzzHeavier Folder ID.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "PIXELDRAIN_KEY": (
        "String",
        "PixelDrain API Key",
        "<i>Send your PixelDrain API Key.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "DEVUPLOADS_KEY": (
        "String",
        "DevUploads API Key",
        "<i>Send your DevUploads API Key.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "DEVUPLOADS_FOLDER": (
        "String",
        "DevUploads Folder ID",
        "<i>Send your DevUploads Folder ID. Leave empty to upload to root.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "VIKINGFILE_HASH": (
        "String",
        "VikingFile Hash",
        "<i>Send your VikingFile User Hash.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "VIKINGFILE_FOLDER": (
        "String",
        "VikingFile Folder Name",
        "<i>Send your VikingFile folder name/path. Leave empty to upload to root.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_TITLE": (
        "String",
        "Metadata Title",
        "<i>Send your Metadata Title.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_AUTHOR": (
        "String",
        "Metadata Author",
        "<i>Send your Metadata Author.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_ARTIST": (
        "String",
        "Metadata Artist",
        "<i>Send your Metadata Artist.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_AUDIO": (
        "String",
        "Metadata Audio Name. Example: Hindi",
        "<i>Send your Metadata Audio Name.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_SUBTITLE": (
        "String",
        "Metadata Subtitle Name. Example: English",
        "<i>Send your Metadata Subtitle Name.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_VIDEO": (
        "String",
        "Metadata Video Name.",
        "<i>Send your Metadata Video Name.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_ENCODED_BY": (
        "String",
        "Metadata Encoded By.",
        "<i>Send your Metadata Encoded By.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_CUSTOM_TAG": (
        "String",
        "Metadata Custom Tag.",
        "<i>Send your Metadata Custom Tag.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_COMMENT": (
        "String",
        "Metadata Comment.",
        "<i>Send your Metadata Comment.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_DUBBED_BY": (
        "String",
        "Metadata Dubbed By.",
        "<i>Send your Metadata Dubbed By.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_CHANNEL": (
        "String",
        "Metadata Channel.",
        "<i>Send your Metadata Channel.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_WEBSITE": (
        "String",
        "Metadata Website.",
        "<i>Send your Metadata Website.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_COPYRIGHT": (
        "String",
        "Metadata Copyright. Example: By Rare Bots Bot",
        "<i>Send your Metadata Copyright.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_PUBLISHER": (
        "String",
        "Metadata Publisher.",
        "<i>Send your Metadata Publisher.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_ENCODER": (
        "String",
        "Metadata Encoder.",
        "<i>Send your Metadata Encoder.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_SOURCE": (
        "String",
        "Metadata Source.",
        "<i>Send your Metadata Source.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_STUDIO": (
        "String",
        "Metadata Studio.",
        "<i>Send your Metadata Studio.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
    "METADATA_ALL": (
        "String",
        "Set all Metadata values at once.",
        "<i>Send a value to set for all metadata fields.</i> \n┖ <b>Time Left :</b> <code>60 sec</code>",
    ),
}


async def get_user_settings(from_user, stype="main"):
    user_id = from_user.id
    user_name = from_user.mention(style="html")
    buttons = ButtonMaker()
    rclone_conf = f"rclone/{user_id}.conf"
    token_pickle = f"tokens/{user_id}.pickle"
    user_dict = user_data.get(user_id, {})

    if stype == "main":
        buttons.data_button(
            SFMLStyle.GEN_SET_BT, f"userset {user_id} general", position="header"
        )
        buttons.data_button(SFMLStyle.MIR_SET_BT, f"userset {user_id} mirror")
        buttons.data_button(SFMLStyle.LEE_SET_BT, f"userset {user_id} leech")

        if user_dict and any(
            key in user_dict
            for key in list(user_settings_text.keys())
            + [
                "USER_TOKENS",
                "AS_DOCUMENT",
                "EQUAL_SPLITS",
                "MEDIA_GROUP",
                "USER_TRANSMISSION",
                "HYBRID_LEECH",
                "STOP_DUPLICATE",
                "DEFAULT_UPLOAD",
            ]
        ):
            buttons.data_button(
                SFMLStyle.RES_ALL_BT, f"userset {user_id} confirm_reset_all", position="footer"
            )
        buttons.data_button(
            SFMLStyle.CLOSE_BT,
            f"userset {user_id} close",
            position="footer",
            style=ButtonStyle.DANGER,
        )

        text = SFMLStyle.USER_SETTING.format(
            NAME=user_name,
            ID=user_id,
            USERNAME=f"@{from_user.username}",
            DC=from_user.dc_id,
            LANG=Language.get(lc).display_name() if (lc := from_user.language_code) else "𝖭/𝖠",
            DT=user_dict.get("DAILY_TASKS", "𝖨𝗇𝖿𝗂𝗇𝗂𝗍𝖾"),
            LAST_USED=user_dict.get("LAST_USED", "𝖭𝖾𝗏𝖾𝗋"),
        )

        btns = buttons.build_menu(2)

    elif stype == "general":
        buttons.data_button(SFMLStyle.EX_EXT_BT, f"userset {user_id} menu EXCLUDED_EXTENSIONS")
        if user_dict.get("DEFAULT_UPLOAD", ""):
            default_upload = user_dict["DEFAULT_UPLOAD"]
        elif "DEFAULT_UPLOAD" not in user_dict:
            default_upload = Config.DEFAULT_UPLOAD
        du = SFMLStyle.GDRIVE_API_BT if default_upload == "gd" else SFMLStyle.RCLONE_API_BT
        dur = SFMLStyle.GDRIVE_API_BT if default_upload != "gd" else SFMLStyle.RCLONE_API_BT
        buttons.data_button(
            SFMLStyle.SW_MODE_BT.format(dur=dur), f"userset {user_id} {default_upload}"
        )

        user_tokens = user_dict.get("USER_TOKENS", False)
        tr = "𝖴𝖲𝖤𝖱" if user_tokens else "𝖮𝖶𝖭𝖤𝖱"
        trr = "𝖮𝖶𝖭𝖤𝖱" if user_tokens else "𝖴𝖲𝖤𝖱"
        buttons.data_button(
            SFMLStyle.SW_TOK_BT.format(trr=trr),
            f"userset {user_id} tog USER_TOKENS {'f' if user_tokens else 't'}",
        )

        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )

        def_cookies = user_dict.get("USE_DEFAULT_COOKIE", False)
        cookie_mode = "𝖮𝖶𝖭𝖤𝖱" if def_cookies else "𝖴𝖲𝖤𝖱"
        buttons.data_button(
            SFMLStyle.SW_COOK_BT.format(cookie_mode=f"{'𝖮𝖶𝖭𝖤𝖱' if not def_cookies else '𝖴𝖲𝖤𝖱'}'𝗌"),
            f"userset {user_id} tog USE_DEFAULT_COOKIE {'f' if def_cookies else 't'}",
        )
        btns = buttons.build_menu(1)

        text = SFMLStyle.GS_TEXT + f"\n┟ <b>𝖭𝖺𝗆𝖾</b> → {user_name}\n┃\n┠ <b>𝖣𝖾𝖿𝖺𝗎𝗅𝗍 𝖴𝗉𝗅𝗈𝖺𝖽 𝖯𝖺𝖼𝗄𝖺𝗀𝖾</b> → <b>{du}</b>\n┠ <b>𝖣𝖾𝖿𝖺𝗎𝗅𝗍 𝖴𝗌𝖺𝗀𝖾 𝖬𝗈𝖽𝖾</b> → <b>{tr}'𝗌</b> 𝗍𝗈𝗄𝖾𝗇/𝖼𝗈𝗇𝖿𝗂𝗀\n┖ <b>𝗒𝗍 𝖢𝗈𝗈𝗄𝗂𝖾𝗌 𝖬𝗈𝖽𝖾</b> → <b>{cookie_mode}'𝗌 𝖢𝗈𝗈𝗄𝗂𝖾</b>\n"

    elif stype == "leech":
        thumbpath = f"thumbnails/{user_id}.jpg"
        buttons.data_button(SFMLStyle.THUMB_BT, f"userset {user_id} menu THUMBNAIL")
        thumbmsg = "𝖤𝗑𝗂𝗌𝗍𝗌" if await aiopath.exists(thumbpath) else "𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌"
        buttons.data_button(
            SFMLStyle.SPLIT_BT, f"userset {user_id} menu LEECH_SPLIT_SIZE"
        )
        if user_dict.get("LEECH_SPLIT_SIZE", False):
            split_size = user_dict["LEECH_SPLIT_SIZE"]
        else:
            split_size = Config.LEECH_SPLIT_SIZE
        buttons.data_button(
            SFMLStyle.DEST_BT, f"userset {user_id} menu LEECH_DUMP_CHAT"
        )
        if user_dict.get("LEECH_DUMP_CHAT", False):
            leech_dest = user_dict["LEECH_DUMP_CHAT"]
        elif "LEECH_DUMP_CHAT" not in user_dict and Config.LEECH_DUMP_CHAT:
            leech_dest = Config.LEECH_DUMP_CHAT
        else:
            leech_dest = "𝖭𝗈𝗇𝖾"
        buttons.data_button(SFMLStyle.PREFIX_BT, f"userset {user_id} menu LEECH_PREFIX")
        if user_dict.get("LEECH_PREFIX", False):
            lprefix = user_dict["LEECH_PREFIX"]
        elif "LEECH_PREFIX" not in user_dict and Config.LEECH_PREFIX:
            lprefix = Config.LEECH_PREFIX
        else:
            lprefix = "𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌"
        buttons.data_button(SFMLStyle.SUFFIX_BT, f"userset {user_id} menu LEECH_SUFFIX")
        if user_dict.get("LEECH_SUFFIX", False):
            lsuffix = user_dict["LEECH_SUFFIX"]
        elif "LEECH_SUFFIX" not in user_dict and Config.LEECH_SUFFIX:
            lsuffix = Config.LEECH_SUFFIX
        else:
            lsuffix = "𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌"

        buttons.data_button(SFMLStyle.CAPTION_BT, f"userset {user_id} menu LEECH_CAPTION")
        if user_dict.get("LEECH_CAPTION", False):
            lcap = user_dict["LEECH_CAPTION"]
        elif "LEECH_CAPTION" not in user_dict and Config.LEECH_CAPTION:
            lcap = Config.LEECH_CAPTION
        else:
            lcap = "𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌"

        if (
            user_dict.get("AS_DOCUMENT", False)
            or "AS_DOCUMENT" not in user_dict
            and Config.AS_DOCUMENT
        ):
            ltype = SFMLStyle.DOC_BT
            buttons.data_button(SFMLStyle.MEDIA_BT, f"userset {user_id} tog AS_DOCUMENT f")
        else:
            ltype = SFMLStyle.MEDIA_BT
            buttons.data_button(
                SFMLStyle.DOC_BT, f"userset {user_id} tog AS_DOCUMENT t"
            )
        if (
            user_dict.get("EQUAL_SPLITS", False)
            or "EQUAL_SPLITS" not in user_dict
            and Config.EQUAL_SPLITS
        ):
            buttons.data_button(
                SFMLStyle.DISABLE_ES_BT, f"userset {user_id} tog EQUAL_SPLITS f"
            )
            equal_splits = "𝖤𝗇𝖺𝖻𝗅𝖾𝖽"
        else:
            buttons.data_button(
                SFMLStyle.ENABLE_ES_BT, f"userset {user_id} tog EQUAL_SPLITS t"
            )
            equal_splits = "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽"
        if (
            user_dict.get("MEDIA_GROUP", False)
            or "MEDIA_GROUP" not in user_dict
            and Config.MEDIA_GROUP
        ):
            buttons.data_button(
                SFMLStyle.DISABLE_MG_BT, f"userset {user_id} tog MEDIA_GROUP f"
            )
            media_group = "𝖤𝗇𝖺𝖻𝗅𝖾𝖽"
        else:
            buttons.data_button(
                SFMLStyle.ENABLE_MG_BT, f"userset {user_id} tog MEDIA_GROUP t"
            )
            media_group = "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽"
        if (
            TgClient.IS_PREMIUM_USER
            and user_dict.get("USER_TRANSMISSION", False)
            or "USER_TRANSMISSION" not in user_dict
            and Config.USER_TRANSMISSION
        ):
            buttons.data_button(
                SFMLStyle.LEECH_BY_BOT_BT, f"userset {user_id} tog USER_TRANSMISSION f"
            )
            leech_method = "𝗎𝗌𝖾𝗋"
        elif TgClient.IS_PREMIUM_USER:
            leech_method = "𝖻𝗈𝗍"
            buttons.data_button(
                SFMLStyle.LEECH_BY_USER_BT, f"userset {user_id} tog USER_TRANSMISSION t"
            )
        else:
            leech_method = "𝖻𝗈𝗍"

        if (
            TgClient.IS_PREMIUM_USER
            and user_dict.get("HYBRID_LEECH", False)
            or "HYBRID_LEECH" not in user_dict
            and Config.HYBRID_LEECH
        ):
            hybrid_leech = "𝖤𝗇𝖺𝖻𝗅𝖾𝖽"
            buttons.data_button(
                SFMLStyle.DISABLE_HL_BT, f"userset {user_id} tog HYBRID_LEECH f"
            )
        elif TgClient.IS_PREMIUM_USER:
            hybrid_leech = "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽"
            buttons.data_button(
                SFMLStyle.ENABLE_HL_BT, f"userset {user_id} tog HYBRID_LEECH t"
            )
        else:
            hybrid_leech = "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽"

        buttons.data_button(
            SFMLStyle.T_LAYOUT_BT, f"userset {user_id} menu THUMBNAIL_LAYOUT"
        )
        if user_dict.get("THUMBNAIL_LAYOUT", False):
            thumb_layout = user_dict["THUMBNAIL_LAYOUT"]
        elif "THUMBNAIL_LAYOUT" not in user_dict and Config.THUMBNAIL_LAYOUT:
            thumb_layout = Config.THUMBNAIL_LAYOUT
        else:
            thumb_layout = "𝖭𝗈𝗇𝖾"

        buttons.data_button(SFMLStyle.RENAME_BT, f"userset {user_id} menu AUTORENAME")
        if user_dict.get("AUTORENAME", False):
            ar_msg = user_dict["AUTORENAME"]
        elif "AUTORENAME" not in user_dict and Config.AUTORENAME:
            ar_msg = Config.AUTORENAME
        else:
            ar_msg = "𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌"

        ns_msg = (
            f"<code>{swap}</code>"
            if (swap := user_dict.get("NAME_SWAP", False))
            else "<b>𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌</b>"
        )
        buttons.data_button(SFMLStyle.N_SWAP_BT, f"userset {user_id} menu NAME_SWAP")

        buttons.data_button(SFMLStyle.METADATA_BT, f"userset {user_id} metadata")

        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        btns = buttons.build_menu(2)

        metadata_mode = (
            "𝖤𝗇𝖺𝖻𝗅𝖾𝖽"
            if user_dict.get("LEECH_METADATA", False)
            or "LEECH_METADATA" not in user_dict
            and Config.LEECH_METADATA
            else "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽"
        )

        text = SFMLStyle.LEECH.format(
            NAME=user_name,
            DL=user_dict.get("DAILY_LEECH", "𝖨𝗇𝖿𝗂𝗇𝗂𝗍𝖾"),
            LTYPE=ltype,
            THUMB=thumbmsg,
            SPLIT_SIZE=get_readable_file_size(split_size),
            EQUAL_SPLIT=equal_splits,
            MEDIA_GROUP=media_group,
            MIXED_LEECH=hybrid_leech,
            LAUTO_RENAME=escape(str(ar_msg)),
            NAME_SWAP=ns_msg,
            LCAPTION=escape(lcap),
            LPREFIX=escape(lprefix),
            LSUFFIX=escape(lsuffix),
            LREMNAME=user_dict.get("LEECH_REMNAME", "𝖭𝗈𝗇𝖾"),
            LDUMP=leech_dest,
            ATTACHMENT="𝖤𝗇𝖺𝖻𝗅𝖾𝖽" if user_dict.get("LEECH_ATTACHMENT") else "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽",
            MEDIAINFO=user_dict.get("MEDIAINFO_MODE", "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽"),
            SAVE_MODE="𝖤𝗇𝖺𝖻𝗅𝖾𝖽" if user_dict.get("SAVE_MODE") else "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽",
            BOT_PM=leech_method,
            METADATA=metadata_mode,
        )

    elif stype == "metadata":
        if (
            user_dict.get("LEECH_METADATA", False)
            or "LEECH_METADATA" not in user_dict
            and Config.LEECH_METADATA
        ):
            buttons.data_button(
                SFMLStyle.DISABLE_META_BT, f"userset {user_id} tog LEECH_METADATA f"
            )
            metadata_mode = "𝖤𝗇𝖺𝖻𝗅𝖾𝖽"
        else:
            buttons.data_button(
                SFMLStyle.ENABLE_META_BT, f"userset {user_id} tog LEECH_METADATA t"
            )
            metadata_mode = "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽"

        buttons.data_button("𝖳𝗂𝗍𝗅𝖾", f"userset {user_id} menu METADATA_TITLE")
        buttons.data_button("Author", f"userset {user_id} menu METADATA_AUTHOR")
        buttons.data_button("Artist", f"userset {user_id} menu METADATA_ARTIST")
        buttons.data_button("Audio", f"userset {user_id} menu METADATA_AUDIO")
        buttons.data_button("Subtitle", f"userset {user_id} menu METADATA_SUBTITLE")
        buttons.data_button("Video", f"userset {user_id} menu METADATA_VIDEO")
        buttons.data_button(
            "Encoded By", f"userset {user_id} menu METADATA_ENCODED_BY"
        )
        buttons.data_button(
            "Custom Tag", f"userset {user_id} menu METADATA_CUSTOM_TAG"
        )
        buttons.data_button("Comment", f"userset {user_id} menu METADATA_COMMENT")
        buttons.data_button("Dubbed By", f"userset {user_id} menu METADATA_DUBBED_BY")
        buttons.data_button("Channel", f"userset {user_id} menu METADATA_CHANNEL")
        buttons.data_button("Website", f"userset {user_id} menu METADATA_WEBSITE")
        buttons.data_button("Copyright", f"userset {user_id} menu METADATA_COPYRIGHT")
        buttons.data_button("Publisher", f"userset {user_id} menu METADATA_PUBLISHER")
        buttons.data_button("Encoder", f"userset {user_id} menu METADATA_ENCODER")
        buttons.data_button("Source", f"userset {user_id} menu METADATA_SOURCE")
        buttons.data_button("Studio", f"userset {user_id} menu METADATA_STUDIO")
        buttons.data_button("Set All", f"userset {user_id} set METADATA_ALL")

        buttons.data_button("Back", f"userset {user_id} back leech", "footer")
        buttons.data_button(
            "Close", f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        btns = buttons.build_menu(2)

        m_title = (
            user_dict.get("METADATA_TITLE") or Config.METADATA_TITLE or "Not Exists"
        )
        m_author = (
            user_dict.get("METADATA_AUTHOR") or Config.METADATA_AUTHOR or "Not Exists"
        )
        m_artist = (
            user_dict.get("METADATA_ARTIST") or Config.METADATA_ARTIST or "Not Exists"
        )
        m_audio = (
            user_dict.get("METADATA_AUDIO") or Config.METADATA_AUDIO or "Not Exists"
        )
        m_subtitle = (
            user_dict.get("METADATA_SUBTITLE")
            or Config.METADATA_SUBTITLE
            or "Not Exists"
        )
        m_video = (
            user_dict.get("METADATA_VIDEO") or Config.METADATA_VIDEO or "Not Exists"
        )
        m_encoded = (
            user_dict.get("METADATA_ENCODED_BY")
            or Config.METADATA_ENCODED_BY
            or "Not Exists"
        )
        m_tag = (
            user_dict.get("METADATA_CUSTOM_TAG")
            or Config.METADATA_CUSTOM_TAG
            or "Not Exists"
        )
        m_comment = (
            user_dict.get("METADATA_COMMENT") or Config.METADATA_COMMENT or "Not Exists"
        )
        m_dubbed = (
            user_dict.get("METADATA_DUBBED_BY")
            or Config.METADATA_DUBBED_BY
            or "Not Exists"
        )
        m_channel = (
            user_dict.get("METADATA_CHANNEL") or Config.METADATA_CHANNEL or "Not Exists"
        )
        m_website = (
            user_dict.get("METADATA_WEBSITE") or Config.METADATA_WEBSITE or "Not Exists"
        )
        m_copyright = (
            user_dict.get("METADATA_COPYRIGHT")
            or Config.METADATA_COPYRIGHT
            or "Not Exists"
        )
        m_publisher = (
            user_dict.get("METADATA_PUBLISHER")
            or Config.METADATA_PUBLISHER
            or "Not Exists"
        )
        m_encoder = (
            user_dict.get("METADATA_ENCODER") or Config.METADATA_ENCODER or "Not Exists"
        )
        m_source = (
            user_dict.get("METADATA_SOURCE") or Config.METADATA_SOURCE or "Not Exists"
        )
        m_studio = (
            user_dict.get("METADATA_STUDIO") or Config.METADATA_STUDIO or "Not Exists"
        )

        text = f"""⌬ <b>Leech Metadata Settings :</b>
┟ <b>Name</b> → {user_name}
┃
┠ Metadata → <b>{metadata_mode}</b>
┠ Title → <code>{escape(str(m_title))}</code>
┠ Author → <code>{escape(str(m_author))}</code>
┠ Artist → <code>{escape(str(m_artist))}</code>
┠ Audio → <code>{escape(str(m_audio))}</code>
┠ Subtitle → <code>{escape(str(m_subtitle))}</code>
┠ Video → <code>{escape(str(m_video))}</code>
┠ Encoded By → <code>{escape(str(m_encoded))}</code>
┠ Custom Tag → <code>{escape(str(m_tag))}</code>
┠ Comment → <code>{escape(str(m_comment))}</code>
┠ Dubbed By → <code>{escape(str(m_dubbed))}</code>
┠ Channel → <code>{escape(str(m_channel))}</code>
┠ Website → <code>{escape(str(m_website))}</code>
┠ Copyright → <code>{escape(str(m_copyright))}</code>
┠ Publisher → <code>{escape(str(m_publisher))}</code>
┠ Encoder → <code>{escape(str(m_encoder))}</code>
┠ Source → <code>{escape(str(m_source))}</code>
┖ Studio → <code>{escape(str(m_studio))}</code>
"""

    elif stype == "uphoster":
        uphoster_service = user_dict.get("UPHOSTER_SERVICE", "gofile")
        buttons.data_button(
            SFMLStyle.SET_DEST_BT,
            f"userset {user_id} uphoster_destinations",
        )
        buttons.data_button(SFMLStyle.GO_BT, f"userset {user_id} gofile")
        buttons.data_button(SFMLStyle.BZ_BT, f"userset {user_id} buzzheavier")
        buttons.data_button(SFMLStyle.PD_BT, f"userset {user_id} pixeldrain")
        buttons.data_button(SFMLStyle.DU_BT, f"userset {user_id} devuploads")
        buttons.data_button(SFMLStyle.VF_BT, f"userset {user_id} vikingfile")
        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back mirror", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        btns = buttons.build_menu(1)

        destinations = [s.capitalize() for s in uphoster_service.split(",")]
        text = SFMLStyle.UHS_TEXT + f"\n┟ <b>𝖭𝖺𝗆𝖾</b> → {user_name}\n┃\n┖ <b>𝖢𝗎𝗋𝗋𝖾𝗇𝗍 𝖣𝖾𝗌𝗍𝗂𝗇𝖺𝗍𝗂𝗈𝗇</b> → {', '.join(destinations)}"

    elif stype == "pixeldrain":
        buttons.data_button("𝖯𝗂𝗑𝖾𝗅𝖣𝗋𝖺𝗂𝗇 𝖪𝖾𝗒", f"userset {user_id} menu PIXELDRAIN_KEY")
        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back uphoster", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        btns = buttons.build_menu(1)

        if user_dict.get("PIXELDRAIN_KEY", False):
            pdtoken = user_dict["PIXELDRAIN_KEY"]
        elif Config.PIXELDRAIN_KEY:
            pdtoken = Config.PIXELDRAIN_KEY
        else:
            pdtoken = "𝖭𝗈𝗇𝖾"

        text = SFMLStyle.PDS_TEXT + f"\n┟ <b>𝖭𝖺𝗆𝖾</b> → {user_name}\n┃\n┖ <b>𝖯𝗂𝗑𝖾𝗅𝖣𝗋𝖺𝗂𝗇 𝖪𝖾𝗒</b> → <code>{pdtoken}</code>"

    elif stype == "buzzheavier":
        buttons.data_button(
            "𝖡𝗎𝗓𝗓𝖧𝖾𝖺𝗏𝗂𝖾𝗋 𝳀𝗈𝗄𝖾𝗇", f"userset {user_id} menu BUZZHEAVIER_TOKEN"
        )
        buttons.data_button(
            "𝖡𝗎𝗓𝗓𝖧𝖾𝖺𝗏𝗂𝖾𝗋 𝖥𝗈𝗅𝖽𝖾𝗋 𝖨𝖣", f"userset {user_id} menu BUZZHEAVIER_FOLDER_ID"
        )
        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back uphoster", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        btns = buttons.build_menu(1)

        if user_dict.get("BUZZHEAVIER_TOKEN", False):
            bztoken = user_dict["BUZZHEAVIER_TOKEN"]
        elif Config.BUZZHEAVIER_API:
            bztoken = Config.BUZZHEAVIER_API
        else:
            bztoken = "𝖭𝗈𝗇𝖾"

        if user_dict.get("BUZZHEAVIER_FOLDER_ID", False):
            bzfolder = user_dict["BUZZHEAVIER_FOLDER_ID"]
        else:
            bzfolder = "𝖭𝗈𝗇𝖾"

        text = SFMLStyle.BHS_TEXT + f"\n┟ <b>𝖭𝖺𝗆𝖾</b> → {user_name}\n┃\n┠ <b>𝖡𝗎𝗓𝗓𝖧𝖾𝖺𝗏𝗂𝖾𝗋 𝖳𝗈𝗄𝖾𝗇</b> → <code>{bztoken}</code>\n┖ <b>𝖡𝗎𝗓𝗓𝖧𝖾𝖺𝗏𝗂𝖾𝗋 𝖥𝗈𝗅𝖽𝖾𝗋 𝖨𝖣</b> → <code>{bzfolder}</code>"

    elif stype == "devuploads":
        buttons.data_button(
            "𝖣𝖾𝗏𝖴𝗉𝗅𝗈𝖺𝖽𝗌 𝖠𝖯𝖨 𝖪𝖾𝗒", f"userset {user_id} menu DEVUPLOADS_KEY"
        )
        buttons.data_button(
            "𝖣𝖾𝗏𝖴𝗉𝗅𝗈𝖺𝖽𝗌 𝖥𝗈𝗅𝖽𝖾𝗋 𝖨𝖣", f"userset {user_id} menu DEVUPLOADS_FOLDER"
        )
        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back uphoster", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        btns = buttons.build_menu(1)

        dukey = user_dict.get("DEVUPLOADS_KEY") or Config.DEVUPLOADS_KEY or "𝖭𝗈𝗇𝖾"
        dufolder = (
            user_dict.get("DEVUPLOADS_FOLDER")
            or Config.DEVUPLOADS_FOLDER
            or "𝖭𝗈𝗇𝖾 (𝖱𝗈𝗈𝗍)"
        )
        text = SFMLStyle.DUS_TEXT + f"\n┟ <b>𝖭𝖺𝗆𝖾</b> → {user_name}\n┃\n┠ <b>𝖣𝖾𝗏𝖴𝗉𝗅𝗈𝖺𝖽𝗌 𝖪𝖾𝗒</b> → <code>{dukey}</code>\n┖ <b>𝖣𝖾𝗏𝖴𝗉𝗅𝗈𝖺𝖽𝗌 𝖥𝗈𝗅𝖽𝖾𝗋 𝖨𝖣</b> → <code>{dufolder}</code>"

    elif stype == "vikingfile":
        buttons.data_button(
            "𝖵𝗂𝗄𝗂𝗇𝗀𝖥𝗂𝗅𝖾 𝖧𝖺𝗌𝗁", f"userset {user_id} menu VIKINGFILE_HASH"
        )
        buttons.data_button(
            "𝖵𝗂𝗄𝗂𝗇𝗀𝖥𝗂𝗅𝖾 𝖥𝗈𝗅𝖽𝖾𝗋", f"userset {user_id} menu VIKINGFILE_FOLDER"
        )
        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back uphoster", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        btns = buttons.build_menu(1)

        vfkey = user_dict.get("VIKINGFILE_HASH") or Config.VIKINGFILE_HASH or "𝖭𝗈𝗇𝖾"
        vffolder = (
            user_dict.get("VIKINGFILE_FOLDER")
            or Config.VIKINGFILE_FOLDER
            or "𝖭𝗈𝗇𝖾 (𝖱𝗈𝗈𝗍)"
        )
        text = SFMLStyle.VFS_TEXT + f"\n┟ <b>𝖭𝖺𝗆𝖾</b> → {user_name}\n┃\n┠ <b>𝖵𝗂𝗄𝗂𝗇𝗀𝖥𝗂𝗅𝖾 𝖧𝖺𝗌𝗁</b> → <code>{vfkey}</code>\n┖ <b>𝖵𝗂𝗄𝗂𝗇𝗀𝖥𝗂𝗅𝖾 𝖥𝗈𝗅𝖽𝖾𝗋</b> → <code>{vffolder}</code>"

    elif stype == "gofile":
        buttons.data_button("𝖦𝗈𝖿𝗂𝗅𝖾 𝖳𝗈𝗄𝖾𝗇", f"userset {user_id} menu GOFILE_TOKEN")
        buttons.data_button(
            "𝖦𝗈𝖿𝗂𝗅𝖾 𝖥𝗈𝗅𝖽𝖾𝗋 𝖨𝖣", f"userset {user_id} menu GOFILE_FOLDER_ID"
        )
        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back uphoster", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        btns = buttons.build_menu(1)

        if user_dict.get("GOFILE_TOKEN", False):
            gftoken = user_dict["GOFILE_TOKEN"]
        elif Config.GOFILE_API:
            gftoken = Config.GOFILE_API
        else:
            gftoken = "𝖭𝗈𝗇𝖾"

        if user_dict.get("GOFILE_FOLDER_ID", False):
            gffolder = user_dict["GOFILE_FOLDER_ID"]
        elif Config.GOFILE_FOLDER_ID:
            gffolder = Config.GOFILE_FOLDER_ID
        else:
            gffolder = "𝖭𝗈𝗇𝖾 (𝖴𝗉𝗅𝗈𝖺𝖽𝗌 𝗍𝗈 𝖱𝗈𝗈𝗍)"

        text = SFMLStyle.GOS_TEXT + f"\n┟ <b>𝖭𝖺𝗆𝖾</b> → {user_name}\n┃\n┠ <b>𝖦𝗈𝖿𝗂𝗅𝖾 𝖳𝗈𝗄𝖾𝗇</b> → <code>{gftoken}</code>\n┖ <b>𝖦𝗈𝖿𝗂𝗅𝖾 𝖥𝗈𝗅𝖽𝖾𝗋 𝖨𝖣</b> → <code>{gffolder}</code>"

    elif stype == "rclone":
        buttons.data_button("𝖱𝖼𝗅𝗈𝗇𝖾 𝖢𝗈𝗇𝖿𝗂𝗀", f"userset {user_id} menu RCLONE_CONFIG")
        buttons.data_button(
            "𝖣𝖾𝖿𝖺𝗎𝗅𝗍 𝖱𝖼𝗅𝗈𝗇𝖾 𝖯𝖺𝗍𝗁", f"userset {user_id} menu RCLONE_PATH"
        )
        buttons.data_button("𝖱𝖼𝗅𝗈𝗇𝖾 𝖥𝗅𝖺𝗀𝗌", f"userset {user_id} menu RCLONE_FLAGS")

        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back mirror", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )

        rccmsg = "𝖤𝗑𝗂𝗌𝗍𝗌" if await aiopath.exists(rclone_conf) else "𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌"
        if user_dict.get("RCLONE_PATH", False):
            rccpath = user_dict["RCLONE_PATH"]
        elif Config.RCLONE_PATH:
            rccpath = Config.RCLONE_PATH
        else:
            rccpath = "𝖭𝗈𝗇𝖾"
        btns = buttons.build_menu(1)

        if user_dict.get("RCLONE_FLAGS", False):
            rcflags = user_dict["RCLONE_FLAGS"]
        elif "RCLONE_FLAGS" not in user_dict and Config.RCLONE_FLAGS:
            rcflags = Config.RCLONE_FLAGS
        else:
            rcflags = "𝖭𝗈𝗇𝖾"

        text = SFMLStyle.RCS_TEXT + f"\n┟ <b>𝖭𝖺𝗆𝖾</b> → {user_name}\n┃\n┠ <b>𝖱𝖼𝗅𝗈𝗇𝖾 𝖢𝗈𝗇𝖿𝗂𝗀</b> → <b>{rccmsg}</b>\n┠ <b>𝖱𝖼𝗅𝗈𝗇𝖾 𝖥𝗅𝖺𝗀𝗌</b> → <code>{rcflags}</code>\n┖ <b>𝖱𝖼𝗅𝗈𝗇𝖾 𝖯𝖺𝗍𝗁</b> → <code>{rccpath}</code>"

    elif stype == "gdrive":
        buttons.data_button("𝗍𝗈𝗄𝖾𝗇.𝗉𝗂𝖼𝗄𝗅𝖾", f"userset {user_id} menu TOKEN_PICKLE")
        buttons.data_button("𝖣𝖾𝖿𝖺𝗎𝗅𝗍 𝖦𝖽𝗋𝗂𝗏𝖾 𝖨𝖣", f"userset {user_id} menu GDRIVE_ID")
        buttons.data_button("𝖨𝗇𝖽𝖾𝗑 𝖴𝖱𝖫", f"userset {user_id} menu INDEX_URL")
        if (
            user_dict.get("STOP_DUPLICATE", False)
            or "STOP_DUPLICATE" not in user_dict
            and Config.STOP_DUPLICATE
        ):
            buttons.data_button(
                SFMLStyle.DISABLE_SD_BT, f"userset {user_id} tog STOP_DUPLICATE f"
            )
            sd_msg = "𝖤𝗇𝖺𝖻𝗅𝖾𝖽"
        else:
            buttons.data_button(
                SFMLStyle.ENABLE_SD_BT,
                f"userset {user_id} tog STOP_DUPLICATE t",
                "l_body",
            )
            sd_msg = "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽"
        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back mirror", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )

        tokenmsg = "𝖤𝗑𝗂𝗌𝗍𝗌" if await aiopath.exists(token_pickle) else "𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌"
        if user_dict.get("GDRIVE_ID", False):
            gdrive_id = user_dict["GDRIVE_ID"]
        elif GDID := Config.GDRIVE_ID:
            gdrive_id = GDID
        else:
            gdrive_id = "𝖭𝗈𝗇𝖾"
        index = user_dict["INDEX_URL"] if user_dict.get("INDEX_URL", False) else "𝖭𝗈𝗇𝖾"
        btns = buttons.build_menu(2)

        text = SFMLStyle.GDS_TEXT + f"\n┟ <b>𝖭𝖺𝗆𝖾</b> → {user_name}\n┃\n┠ <b>𝖦𝖽𝗋𝗂𝗏𝖾 𝖳𝗈𝗄𝖾𝗇</b> → <b>{tokenmsg}</b>\n┠ <b>𝖦𝖽𝗋𝗂𝗏𝖾 𝖨𝖣</b> → <code>{gdrive_id}</code>\n┠ <b>𝖨𝗇𝖽𝖾𝗑 𝖴𝖱𝖫</b> → <code>{index}</code>\n┖ <b>𝖲𝗍𝗈𝗉 𝖣𝗎𝗉𝗅𝗂𝖼𝖺𝗍𝖾</b> → <b>{sd_msg}</b>"
    elif stype == "mirror":
        buttons.data_button(SFMLStyle.RCLONE_BT, f"userset {user_id} rclone")
        buttons.data_button(SFMLStyle.GDRIVE_BT, f"userset {user_id} gdrive")
        buttons.data_button(SFMLStyle.SET_DEST_BT, f"userset {user_id} uphoster_destinations")
        buttons.data_button(SFMLStyle.UP_PATH_BT, f"userset {user_id} menu UPLOAD_PATHS")
        buttons.data_button(SFMLStyle.GO_BT, f"userset {user_id} gofile")
        buttons.data_button(SFMLStyle.BZ_BT, f"userset {user_id} buzzheavier")
        buttons.data_button(SFMLStyle.PD_BT, f"userset {user_id} pixeldrain")
        buttons.data_button(SFMLStyle.DU_BT, f"userset {user_id} devuploads")
        buttons.data_button(SFMLStyle.VF_BT, f"userset {user_id} vikingfile")

        rccmsg = "𝖤𝗑𝗂𝗌𝗍𝗌" if await aiopath.exists(rclone_conf) else "𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌"
        if user_dict.get("RCLONE_PATH", False):
            rccpath = user_dict["RCLONE_PATH"]
        elif RP := Config.RCLONE_PATH:
            rccpath = RP
        else:
            rccpath = "𝖭𝗈𝗇𝖾"

        tokenmsg = "𝖤𝗑𝗂𝗌𝗍𝗌" if await aiopath.exists(token_pickle) else "𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌"
        if user_dict.get("GDRIVE_ID", False):
            gdrive_id = user_dict["GDRIVE_ID"]
        elif GI := Config.GDRIVE_ID:
            gdrive_id = GI
        else:
            gdrive_id = "𝖭𝗈𝗇𝖾"

        index = user_dict["INDEX_URL"] if user_dict.get("INDEX_URL", False) else "𝖭𝗈𝗇𝖾"
        if (
            user_dict.get("STOP_DUPLICATE", False)
            or "STOP_DUPLICATE" not in user_dict
            and Config.STOP_DUPLICATE
        ):
            sd_msg = "𝖤𝗇𝖺𝖻𝗅𝖾𝖽"
        else:
            sd_msg = "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽"

        buttons.data_button(SFMLStyle.YT_UP_BT, f"userset {user_id} yttools")
        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        btns = buttons.build_menu(1)

        text = SFMLStyle.MIRROR.format(
            NAME=user_name,
            RCLONE=rccmsg,
            RCLONE_PATH=rccpath, # Wait, format in style.py used {RCLONE} and then headers.
            # Re-checking SFMLStyle.MIRROR format...
            TPICK=tokenmsg,
            GDRIVE_ID=gdrive_id,
            MPREFIX=user_dict.get("MPREFIX", "𝖭𝗈𝗇𝖾"),
            MSUFFIX=user_dict.get("MSUFFIX", "𝖭𝗈𝗇𝖾"),
            MREMNAME=user_dict.get("MREMNAME", "𝖭𝗈𝗇𝖾"),
            DDL_SERVER=user_dict.get("UPHOSTER_SERVICE", "𝖦𝗈𝖿𝗂𝗅𝖾"),
            TMODE=user_dict.get("USER_TD_MODE", "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽"),
            USERTD=user_dict.get("USER_TD_COUNT", 0),
            UP_PATHS=user_dict.get("UPLOAD_PATHS", "𝖭𝗈𝗇𝖾"),
            USESS="𝖤𝗇𝖺𝖻𝗅𝖾𝖽" if user_dict.get("USER_SESSION") else "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽",
            DM=user_dict.get("DAILY_MIRROR", "𝖨𝗇𝖿𝗂𝗇𝗂𝗍𝖾")
        )

    elif stype == "yttools":
        buttons.data_button(SFMLStyle.YT_OPT_BT, f"userset {user_id} menu YT_DLP_OPTIONS")
        buttons.data_button(SFMLStyle.YT_COOK_BT, f"userset {user_id} menu USER_COOKIE_FILE")
        buttons.data_button(SFMLStyle.YT_DES_BT, f"userset {user_id} menu YT_DESP")
        yt_desp_val = user_dict.get(
            "YT_DESP",
            Config.YT_DESP if hasattr(Config, "YT_DESP") else "𝖭𝗈𝗍 𝖲𝖾𝗍 (𝖴𝗌𝖾𝗌 𝖣𝖾𝖿𝖺𝗎𝗅𝗍)",
        )

        buttons.data_button(SFMLStyle.YT_TAG_BT, f"userset {user_id} menu YT_TAGS")
        yt_tags_val = user_dict.get(
            "YT_TAGS",
            Config.YT_TAGS if hasattr(Config, "YT_TAGS") else "𝖭𝗈𝗍 𝖲𝖾𝗍 (𝖴𝗌𝖾𝗌 𝖣𝖾𝖿𝖺𝗎𝗅𝗍)",
        )
        if isinstance(yt_tags_val, list):
            yt_tags_val = ",".join(yt_tags_val)

        buttons.data_button(SFMLStyle.YT_CAT_BT, f"userset {user_id} menu YT_CATEGORY_ID")
        yt_cat_id_val = user_dict.get(
            "YT_CATEGORY_ID",
            (
                Config.YT_CATEGORY_ID
                if hasattr(Config, "YT_CATEGORY_ID")
                else "𝖭𝗈𝗍 𝖲𝖾𝗍 (𝖴𝗌𝖾𝗌 𝖣𝖾𝖿𝖺𝗎𝗅𝗍)"
            ),
        )

        buttons.data_button(
            SFMLStyle.YT_PRI_BT, f"userset {user_id} menu YT_PRIVACY_STATUS"
        )
        yt_privacy_val = user_dict.get(
            "YT_PRIVACY_STATUS",
            (
                Config.YT_PRIVACY_STATUS
                if hasattr(Config, "YT_PRIVACY_STATUS")
                else "𝖭𝗈𝗍 𝖲𝖾𝗍 (𝖴𝗌𝖾𝗌 𝖣𝖾𝖿𝖺𝗎𝗅𝗍)"
            ),
        )

        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back mirror", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        btns = buttons.build_menu(2)

        ytopt = user_dict.get("YT_DLP_OPTIONS") or Config.YT_DLP_OPTIONS or "𝖭𝗈𝗇𝖾"
        yt_cookie_path = f"cookies/{user_id}/cookies.txt"
        user_cookie_msg = "𝖤𝗑𝗂𝗌𝗍𝗌" if await aiopath.exists(yt_cookie_path) else "𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌"
        text = SFMLStyle.YTS_TEXT + f"\n┟ <b>𝖭𝖺𝗆𝖾</b> → {user_name}\n┃\n┠ <b>𝗒𝗍-𝖽𝗅𝗉 𝖮𝗉𝗍𝗂𝗈𝗇𝗌</b> → <code>{ytopt}</code>\n┠ <b>𝗒𝗍 𝖴𝗌𝖾𝗋 𝖢𝗈𝗈𝗄𝗂𝖾 𝖥𝗂𝗅𝖾</b> → <b>{user_cookie_msg}</b>\n┠ <b>𝗒𝗍 𝖣𝖾𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇</b> → <code>{escape(str(yt_desp_val))}</code>\n┠ <b>𝗒𝗍 𝖳𝖺𝗀𝗌</b> → <code>{escape(str(yt_tags_val))}</code>\n┠ <b>𝗒𝗍 𝖢𝖺𝗍𝖾𝗀𝗈𝗋𝗒 𝖨𝖣</b> → <code>{escape(str(yt_cat_id_val))}</code>\n┖ <b>𝗒𝗍 𝖯𝗋𝗂𝗏𝖺𝖼𝗒 𝖲𝗍𝖺𝗍𝗎𝗌</b> → <code>{escape(str(yt_privacy_val))}</code>"

    return text, btns


async def update_user_settings(query, stype="main"):
    handler_dict[query.from_user.id] = False
    msg, button = await get_user_settings(query.from_user, stype)
    await edit_message(query.message, msg, button, photo=Config.SETTINGS_PIC)


@new_task
async def set_title(_, message):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value = message.text.split(maxsplit=1)
    if len(value) > 1:
        value = value[1]
        update_user_ldata(user_id, "TITLE", value)
        await database.update_user_data(user_id)
        await send_message(message, f"<b>Custom Title Set:</b> <code>{value}</code>")
    else:
        await send_message(message, "<b>Send Title with Command!</b>")


@new_task
async def set_thumb(_, message):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    reply_to = message.reply_to_message
    if reply_to and (reply_to.photo or reply_to.document):
        thumb_path = await create_thumb(reply_to, user_id)
        update_user_ldata(user_id, "THUMBNAIL", thumb_path)
        await database.update_user_doc(user_id, "THUMBNAIL", thumb_path)
        await send_message(message, "<b>Custom Thumbnail Set!</b>")
    else:
        await send_message(
            message, "<b>Reply to a photo or document to set it as Thumbnail!</b>"
        )


@new_task
async def send_user_settings(_, message):
    from_user = message.from_user
    handler_dict[from_user.id] = False
    msg, button = await get_user_settings(from_user)
    await send_message(message, msg, button, photo=Config.SETTINGS_PIC)


@new_task
async def add_file(_, message, ftype, rfunc):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    if ftype == "THUMBNAIL":
        des_dir = await create_thumb(message, user_id)
    elif ftype == "RCLONE_CONFIG":
        rpath = f"{getcwd()}/rclone/"
        await makedirs(rpath, exist_ok=True)
        des_dir = f"{rpath}{user_id}.conf"
        await message.download(file_name=des_dir)
    elif ftype == "TOKEN_PICKLE":
        tpath = f"{getcwd()}/tokens/"
        await makedirs(tpath, exist_ok=True)
        des_dir = f"{tpath}{user_id}.pickle"
        await message.download(file_name=des_dir)
    elif ftype == "USER_COOKIE_FILE":
        cpath = f"{getcwd()}/cookies/{user_id}"
        await makedirs(cpath, exist_ok=True)
        des_dir = f"{cpath}/cookies.txt"
        await message.download(file_name=des_dir)
    await delete_message(message)
    update_user_ldata(user_id, ftype, des_dir)
    await rfunc()
    await database.update_user_doc(user_id, ftype, des_dir)


@new_task
async def add_one(_, message, option, rfunc):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    user_dict = user_data.get(user_id, {})
    value = message.text
    if value and value.startswith("{") and value.endswith("}"):
        try:
            value = eval(value)
            if user_dict[option]:
                user_dict[option].update(value)
            else:
                update_user_ldata(user_id, option, value)
        except Exception as e:
            await send_message(message, str(e))
            return
    else:
        await send_message(message, "It must be Dict!")
        return
    await delete_message(message)
    await rfunc()
    await database.update_user_data(user_id)


@new_task
async def remove_one(_, message, option, rfunc):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    user_dict = user_data.get(user_id, {})
    names = message.text.split("/")
    for name in names:
        if name in user_dict[option]:
            del user_dict[option][name]
    await delete_message(message)
    await rfunc()
    await database.update_user_data(user_id)


@new_task
async def set_option(_, message, option, rfunc):
    user_id = message.from_user.id
    handler_dict[user_id] = False
    value = message.text
    if not value:
        await send_message(message, "Value cannot be empty!")
        return
    if option == "LEECH_SPLIT_SIZE":
        if not value.isdigit():
            value = get_size_bytes(value)
        value = min(int(value), TgClient.MAX_SPLIT_SIZE)
    # elif option == "LEECH_DUMP_CHAT": # TODO: Add
    elif option == "EXCLUDED_EXTENSIONS":
        fx = value.split()
        value = ["aria2", "!qB"]
        for x in fx:
            x = x.lstrip(".")
            value.append(x.strip().lower())
    elif option == "YT_TAGS":
        if isinstance(value, str):
            value = [tag.strip() for tag in value.split(",") if tag.strip()]
        elif not isinstance(value, list):
            await send_message(message, "YT Tags must be a comma-separated string.")
            return
    elif option == "YT_CATEGORY_ID":
        if isinstance(value, str) and value.isdigit():
            value = int(value)
        elif not isinstance(value, int):
            await send_message(message, "YT Category ID must be a whole number.")
            return
    elif option == "YT_PRIVACY_STATUS":
        allowed_statuses = ["public", "private", "unlisted"]
        if not isinstance(value, str) or value.lower() not in allowed_statuses:
            await send_message(
                message,
                f"YT Privacy Status must be one of: {', '.join(allowed_statuses)}.",
            )
            return
        value = value.lower()
    elif option in [
        "METADATA",
        "AUDIO_METADATA",
        "VIDEO_METADATA",
        "SUBTITLE_METADATA",
    ]:
        parsed_metadata_dict = {}
        if value and isinstance(value, str):
            if value.strip() == "":
                value = {}
            else:
                parts = []
                current = ""
                i = 0
                while i < len(value):
                    if value[i] == "\\" and i + 1 < len(value) and value[i + 1] == "|":
                        current += "|"
                        i += 2
                    elif value[i] == "|":
                        parts.append(current)
                        current = ""
                        i += 1
                    else:
                        current += value[i]
                        i += 1
                if current:
                    parts.append(current)

                for part in parts:
                    if "=" in part:
                        key, val_str = part.split("=", 1)
                        parsed_metadata_dict[key.strip()] = val_str.strip()
                if not parsed_metadata_dict and value.strip() != "":
                    await send_message(
                        message,
                        "Malformed metadata string. Format: key1=value1|key2=value2. Use \\| to escape pipe characters.",
                    )
                    return
                value = parsed_metadata_dict
        else:
            value = {}

    elif option == "METADATA_ALL":
        for key in metadata_options:
            update_user_ldata(user_id, key, value)
        await delete_message(message)
        await rfunc()
        await database.update_user_data(user_id)
        return
    elif option in ["UPLOAD_PATHS", "FFMPEG_CMDS", "YT_DLP_OPTIONS"]:
        if value and value.startswith("{") and value.endswith("}"):
            try:
                value = eval(sub(r"\s+", " ", value))
            except Exception as e:
                await send_message(message, str(e))
                return
        else:
            await send_message(message, "It must be dict!")
            return
    update_user_ldata(user_id, option, value)
    await delete_message(message)
    await rfunc()
    await database.update_user_data(user_id)


async def get_menu(option, message, user_id):
    handler_dict[user_id] = False
    user_dict = user_data.get(user_id, {})

    file_dict = {
        "THUMBNAIL": f"thumbnails/{user_id}.jpg",
        "RCLONE_CONFIG": f"rclone/{user_id}.conf",
        "TOKEN_PICKLE": f"tokens/{user_id}.pickle",
        "USER_COOKIE_FILE": f"cookies/{user_id}/cookies.txt",
    }

    buttons = ButtonMaker()
    if option in ["THUMBNAIL", "RCLONE_CONFIG", "TOKEN_PICKLE", "USER_COOKIE_FILE"]:
        key = "file"
    else:
        key = "set"
    buttons.data_button(
        SFMLStyle.CHANGE_BT if user_dict.get(option, False) else SFMLStyle.SET_BT,
        f"userset {user_id} {key} {option}",
    )
    if user_dict.get(option, False):
        if option == "THUMBNAIL":
            buttons.data_button(
                SFMLStyle.V_THUMB_BT, f"userset {user_id} view THUMBNAIL", "header"
            )
        elif option in ["YT_DLP_OPTIONS", "FFMPEG_CMDS", "UPLOAD_PATHS"]:
            buttons.data_button(
                SFMLStyle.A_ONE_BT, f"userset {user_id} addone {option}", "header"
            )
            buttons.data_button(
                SFMLStyle.R_ONE_BT, f"userset {user_id} rmone {option}", "header"
            )

        if key != "file":  # TODO: option default val check
            buttons.data_button(SFMLStyle.RESET_BT, f"userset {user_id} reset {option}")
        elif await aiopath.exists(file_dict[option]):
            buttons.data_button(SFMLStyle.REMOVE_BT, f"userset {user_id} remove {option}")
    if option in leech_options:
        back_to = "leech"
    elif option in metadata_options:
        back_to = "metadata"
    elif option in rclone_options:
        back_to = "rclone"
    elif option in gdrive_options:
        back_to = "gdrive"
    elif option in yt_options:
        back_to = "yttools"
    else:
        back_to = "back"
    buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} {back_to}", "footer")
    buttons.data_button(
        SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
    )
    val = user_dict.get(option)
    if option in file_dict and await aiopath.exists(file_dict[option]):
        val = "<b>𝖤𝗑𝗂𝗌𝗍𝗌</b>"
    elif option == "LEECH_SPLIT_SIZE":
        val = get_readable_file_size(val)
    elif option == "METADATA":
        current_meta_val = user_dict.get(option)
        if isinstance(current_meta_val, dict) and current_meta_val:
            val = ", ".join(
                f"{k}={escape(str(v))}" for k, v in current_meta_val.items()
            )
            val = f"<code>{val}</code>"
        elif isinstance(current_meta_val, str) and current_meta_val:
            val = (
                f"<code>{escape(current_meta_val)}</code> [<i>𝖫𝖾𝗀𝖺𝖼𝗒, 𝗇𝖾𝖾𝖽𝗌 𝗋𝖾-𝗌𝖾𝗍</i>]"
            )
        elif not current_meta_val:
            val = "<b>𝖭𝗈𝗍 𝖲𝖾𝗍</b>"

        if val is None:
            val = "<b>𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌</b>"

    if option == "METADATA":
        text = SFMLStyle.MS_TEXT + f"""\n│\n┟ <b>𝖮𝗉𝗍𝗂𝗈𝗇</b> → {option}\n┃\n┠ <b>𝖮𝗉𝗍𝗂𝗈𝗇'𝗌 𝖵𝖺𝗅𝗎𝖾</b> → {val if val else "<b>𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌</b>"}\n┃\n┠ <b>𝖣𝖾𝖿𝖺𝗎𝗅𝗍 𝖨𝗇𝗉𝗎𝗍 𝖳𝗒𝗉𝖾</b> → {user_settings_text[option][0]}\n┠ <b>𝖣𝖾𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇</b> → {user_settings_text[option][1]}\n┃\n┠ <b>𝖣𝗒𝗇𝖺𝗆𝗂𝖼 𝖵𝖺𝗋𝗂𝖺𝖻𝗅𝖾𝗌:</b>\n┠ • <code>{{filename}}</code> - 𝖥𝗎𝗅𝗅 𝖿𝗂𝗅𝖾𝗇𝖺𝗆𝖾\n┠ • <code>{{basename}}</code> - 𝖥𝗂𝗅𝖾𝗇𝖺𝗆𝖾 𝗐𝗂𝗍𝗁𝗈𝗎𝗍 𝖾𝗑𝗍𝖾𝗇𝗌𝗂𝗈𝗇  \n┠ • <code>{{extension}}</code> - 𝖥𝗂𝗅𝖾 𝖾𝗑𝗍𝖾𝗇𝗌𝗂𝗈𝗇\n┃\n┠ • <code>{{audiolang}}</code> - 𝖠𝗎𝖽𝗂𝗈 𝗅𝖺𝗇𝗀𝗎𝖺𝗀𝖾\n┖ • <code>{{sublang}}</code> - 𝖲𝗎𝖻𝗍𝗂𝗍𝗅𝖾 𝗅𝖺𝗇𝗀𝗎𝖺𝗀𝖾\n"""
    else:
        text = SFMLStyle.MS_TEXT + f"""\n│\n┟ <b>𝖮𝗉𝗍𝗂𝗈𝗇</b> → {option}\n┃\n┠ <b>𝖮𝗉𝗍𝗂𝗈𝗇'𝗌 𝖵𝖺𝗅𝗎𝖾</b> → {val if val else "<b>𝖭𝗈𝗍 𝖤𝗑𝗂𝗌𝗍𝗌</b>"}\n┃\n┠ <b>𝖣𝖾𝖿𝖺𝗎𝗅𝗍 𝖨𝗇𝗉𝗎𝗍 𝖳𝗒𝗉𝖾</b> → {user_settings_text[option][0]}\n┖ <b>𝖣𝖾𝗌𝖼𝗋𝗂𝗉𝗍𝗂𝗈𝗇</b> → {user_settings_text[option][1]}\n"""
    await edit_message(message, text, buttons.build_menu(2))


async def event_handler(client, query, pfunc, rfunc, photo=False, document=False):
    user_id = query.from_user.id
    handler_dict[user_id] = True
    start_time = update_time = time()

    async def event_filter(_, __, event):
        if photo:
            mtype = event.photo or event.document
        elif document:
            mtype = event.document
        else:
            mtype = event.text
        user = event.from_user or event.sender_chat
        return bool(
            user.id == user_id and event.chat.id == query.message.chat.id and mtype
        )

    handler = client.add_handler(
        MessageHandler(pfunc, filters=create(event_filter)), group=-1
    )

    while handler_dict[user_id]:
        await sleep(0.5)
        if time() - start_time > 60:
            handler_dict[user_id] = False
            await rfunc()
        elif time() - update_time > 8 and handler_dict[user_id]:
            update_time = time()
            msg = await client.get_messages(query.message.chat.id, query.message.id)
            text = (msg.text or msg.caption).split("\n")
            text[-1] = (
                f"┖ <b>Time Left :</b> <code>{round(60 - (time() - start_time), 2)} sec</code>"
            )
            await edit_message(msg, "\n".join(text), msg.reply_markup)
    client.remove_handler(*handler)


@new_task
async def edit_user_settings(client, query):
    from_user = query.from_user
    user_id = from_user.id
    name = from_user.mention
    message = query.message
    data = query.data.split()

    handler_dict[user_id] = False
    thumb_path = f"thumbnails/{user_id}.jpg"
    rclone_conf = f"rclone/{user_id}.conf"
    token_pickle = f"tokens/{user_id}.pickle"
    yt_cookie_path = f"cookies/{user_id}/cookies.txt"

    user_dict = user_data.get(user_id, {})
    if user_id != int(data[1]):
        return await query.answer("Not Yours!", show_alert=True)
    elif data[2] == "setevent":
        await query.answer()
    elif data[2] in [
        "general",
        "mirror",
        "leech",
        "uphoster",
        "gofile",
        "buzzheavier",
        "pixeldrain",
        "devuploads",
        "vikingfile",
        "metadata",
        "gdrive",
        "rclone",
    ]:
        await query.answer()
        await update_user_settings(query, data[2])
    elif data[2] == "yttools":
        await query.answer()
        await update_user_settings(query, data[2])
    elif data[2] == "uphoster_destinations":
        await query.answer()
        user_dict = user_data.get(user_id, {})
        uphoster_service = user_dict.get("UPHOSTER_SERVICE", "gofile")
        selected_services = uphoster_service.split(",") if uphoster_service else []

        if len(data) > 3:
            service = data[3]
            if service in selected_services:
                if len(selected_services) > 1:
                    selected_services.remove(service)
                else:
                    await query.answer(
                        "At least one destination must be selected!", show_alert=True
                    )
            else:
                selected_services.append(service)
            new_services = ",".join(selected_services)
            update_user_ldata(user_id, "UPHOSTER_SERVICE", new_services)
            await database.update_user_data(user_id)
            selected_services = new_services.split(",")
        else:
            selected_services = (
                uphoster_service.split(",") if uphoster_service else ["gofile"]
            )

        buttons = ButtonMaker()
        for service in [
            "gofile",
            "buzzheavier",
            "pixeldrain",
            "devuploads",
            "vikingfile",
        ]:
            state = "✓" if service in selected_services else ""
            buttons.data_button(
                f"{service.capitalize()} {state}",
                f"userset {user_id} uphoster_destinations {service}",
            )

        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} back uphoster", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )

        text = SFMLStyle.SUS_TEXT
        await edit_message(message, text, buttons.build_menu(1))
    elif data[2] == "menu":
        await query.answer()
        await get_menu(data[3], message, user_id)
    elif data[2] == "tog":
        await query.answer()
        update_user_ldata(user_id, data[3], data[4] == "t")
        if data[3] == "STOP_DUPLICATE":
            back_to = "gdrive"
        elif data[3] in ["USER_TOKENS", "USE_DEFAULT_COOKIE", "EXCLUDED_EXTENSIONS"]:
            back_to = "general"
        elif data[3] == "LEECH_METADATA":
            back_to = "metadata"
        else:
            back_to = "leech"
        await update_user_settings(query, stype=back_to)
        await database.update_user_data(user_id)
    elif data[2] == "file":
        await query.answer()
        buttons = ButtonMaker()
        text = user_settings_text[data[3]][2]
        buttons.data_button(SFMLStyle.STOP_BT, f"userset {user_id} menu {data[3]} stop")
        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} menu {data[3]}", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        prompt_title = data[3].replace("_", " ").title()
        new_message_text = SFMLStyle.SET_TEXT.format(prompt_title=prompt_title) + f"\n\n{text}"
        await edit_message(message, new_message_text, buttons.build_menu(1))
        rfunc = partial(get_menu, data[3], message, user_id)
        pfunc = partial(add_file, ftype=data[3], rfunc=rfunc)
        await event_handler(
            client,
            query,
            pfunc,
            rfunc,
            photo=data[3] == "THUMBNAIL",
            document=data[3] != "THUMBNAIL",
        )
    elif data[2] in ["set", "addone", "rmone"]:
        await query.answer()
        buttons = ButtonMaker()
        if data[2] == "set":
            text = user_settings_text[data[3]][2]
            func = set_option
        elif data[2] == "addone":
            text = SFMLStyle.ADD_ONE_MSG.format(option=data[3])
            func = add_one
        elif data[2] == "rmone":
            text = SFMLStyle.RM_ONE_MSG.format(option=data[3])
            func = remove_one
        buttons.data_button(SFMLStyle.STOP_BT, f"userset {user_id} menu {data[3]} stop")
        buttons.data_button(SFMLStyle.BACK_BT, f"userset {user_id} menu {data[3]}", "footer")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        await edit_message(
            message,
            (message.text or message.caption).html + "\n\n" + text,
            buttons.build_menu(1),
        )
        rfunc = partial(get_menu, data[3], message, user_id)
        pfunc = partial(func, option=data[3], rfunc=rfunc)
        await event_handler(client, query, pfunc, rfunc)
    elif data[2] == "remove":
        await query.answer("Removed!", show_alert=True)
        if data[3] in [
            "THUMBNAIL",
            "RCLONE_CONFIG",
            "TOKEN_PICKLE",
            "USER_COOKIE_FILE",
        ]:
            if data[3] == "THUMBNAIL":
                fpath = thumb_path
            elif data[3] == "RCLONE_CONFIG":
                fpath = rclone_conf
            elif data[3] == "USER_COOKIE_FILE":
                fpath = yt_cookie_path
            else:
                fpath = token_pickle
            if await aiopath.exists(fpath):
                await remove(fpath)
            del user_dict[data[3]]
            await database.update_user_doc(user_id, data[3])
        else:
            update_user_ldata(user_id, data[3], "")
            await database.update_user_data(user_id)
        await get_menu(data[3], message, user_id)
    elif data[2] == "reset":
        await query.answer("Reset Done!", show_alert=True)
        user_dict.pop(data[3], None)
        await database.update_user_data(user_id)
        await get_menu(data[3], message, user_id)
    elif data[2] == "confirm_reset_all":
        await query.answer()
        buttons = ButtonMaker()
        buttons.data_button(SFMLStyle.YES_BT, f"userset {user_id} do_reset_all yes")
        buttons.data_button(SFMLStyle.NO_BT, f"userset {user_id} do_reset_all no")
        buttons.data_button(
            SFMLStyle.CLOSE_BT, f"userset {user_id} close", "footer", style=ButtonStyle.DANGER
        )
        text = SFMLStyle.CONFIRM_RESET_MSG
        await edit_message(query.message, text, buttons.build_menu(2))
    elif data[2] == "do_reset_all":
        if data[3] == "yes":
            await query.answer("Reset Done!", show_alert=True)
            user_dict = user_data.get(user_id, {})
            for k in list(user_dict.keys()):
                if k not in ("SUDO", "AUTH", "VERIFY_TOKEN", "VERIFY_TIME"):
                    del user_dict[k]
            for fpath in [thumb_path, rclone_conf, token_pickle, yt_cookie_path]:
                if await aiopath.exists(fpath):
                    await remove(fpath)
            await update_user_settings(query)
            await database.update_user_data(user_id)
        else:
            await query.answer("Reset Cancelled.", show_alert=True)
            await update_user_settings(query)
    elif data[2] == "view":
        await query.answer()
        await send_file(message, thumb_path, name)
    elif data[2] in ["gd", "rc"]:
        await query.answer()
        du = "rc" if data[2] == "gd" else "gd"
        update_user_ldata(user_id, "DEFAULT_UPLOAD", du)
        await update_user_settings(query, stype="general")
        await database.update_user_data(user_id)
    elif data[2] == "back":
        await query.answer()
        stype = data[3] if len(data) == 4 else "main"
        await update_user_settings(query, stype)
    else:
        await query.answer()
        await delete_message(message, message.reply_to_message)


@new_task
async def get_users_settings(_, message):
    msg = ""
    if auth_chats:
        msg += f"AUTHORIZED_CHATS: {auth_chats}\n"
    if sudo_users:
        msg += f"SUDO_USERS: {sudo_users}\n\n"
    if user_data:
        for u, d in user_data.items():
            kmsg = f"\n<b>{u}:</b>\n"
            if vmsg := "".join(
                f"{k}: <code>{v or None}</code>\n" for k, v in d.items()
            ):
                msg += kmsg + vmsg
        if not msg:
            await send_message(message, "No users data!")
            return
        msg_ecd = msg.encode()
        if len(msg_ecd) > 4000:
            with BytesIO(msg_ecd) as ofile:
                ofile.name = "users_settings.txt"
                await send_file(message, ofile)
        else:
            await send_message(message, msg)
    else:
        await send_message(message, "No users data!")
