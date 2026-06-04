from html import escape
from ..helper.ext_utils.bot_utils import sync_to_async, new_task
from ..helper.ext_utils.links_utils import is_gdrive_link
from ..helper.ext_utils.status_utils import get_readable_file_size
from ..helper.ext_utils.style import SFMLStyle
from ..helper.mirror_leech_utils.gdrive_utils.count import GoogleDriveCount
from ..helper.telegram_helper.message_utils import delete_message, send_message


@new_task
async def count_node(_, message):
    args = message.text.split()
    user = message.from_user or message.sender_chat
    if username := user.username:
        tag = f"@{username}"
    else:
        tag = message.from_user.mention

    link = args[1] if len(args) > 1 else ""
    if len(link) == 0 and (reply_to := message.reply_to_message):
        link = reply_to.text.split(maxsplit=1)[0].strip()

    if is_gdrive_link(link):
        msg = await send_message(message, SFMLStyle.COUNT_MSG.format(LINK=link))
        name, mime_type, size, files, folders = await sync_to_async(
            GoogleDriveCount().count, link, user.id
        )
        if mime_type is None:
            await send_message(message, name)
            return
        await delete_message(msg)
        msg = SFMLStyle.COUNT_NAME.format(COUNT_NAME=escape(name))
        msg += SFMLStyle.COUNT_SIZE.format(COUNT_SIZE=get_readable_file_size(size))
        msg += SFMLStyle.COUNT_TYPE.format(COUNT_TYPE=mime_type)
        if mime_type == "Folder":
            msg += SFMLStyle.COUNT_SUB.format(COUNT_SUB=folders)
            msg += SFMLStyle.COUNT_FILE.format(COUNT_FILE=files)
        msg += SFMLStyle.COUNT_CC.format(COUNT_CC=tag)
    else:
        msg = (
            "Send Gdrive link along with command or by replying to the link by command"
        )

    await send_message(message, msg)
