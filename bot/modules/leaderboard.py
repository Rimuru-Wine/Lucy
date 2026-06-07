from .. import user_data
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import send_message
from ..helper.ext_utils.bot_utils import new_task

@new_task
async def profile(_, message):
    user_id = (message.from_user or message.sender_chat).id
    user_dict = user_data.get(user_id, {})

    total_tasks = user_dict.get("TOTAL_TASKS", 0)
    total_mirror = user_dict.get("TOTAL_MIRROR", 0)
    total_leech = user_dict.get("TOTAL_LEECH", 0)

    name = (message.from_user.first_name if message.from_user else message.sender_chat.title)

    msg = f"<b>Profile for {name}</b>\n"
    msg += f"<b>Total Tasks:</b> {total_tasks}\n"
    msg += f"<b>Total Mirror:</b> {total_mirror}\n"
    msg += f"<b>Total Leech:</b> {total_leech}\n"

    await send_message(message, msg)

@new_task
async def leaderboard(_, message):
    if not user_data:
        await send_message(message, "<b>No data found!</b>")
        return

    users = []
    for uid, data in user_data.items():
        if "TOTAL_TASKS" in data:
            users.append({
                "name": data.get("NAME", f"User {uid}"),
                "total": data["TOTAL_TASKS"],
                "mirror": data.get("TOTAL_MIRROR", 0),
                "leech": data.get("TOTAL_LEECH", 0)
            })

    if not users:
        await send_message(message, "<b>No tasks completed yet!</b>")
        return

    users.sort(key=lambda x: x["total"], reverse=True)

    msg = "<b>🏆 Top 10 Users Leaderboard 🏆</b>\n\n"
    for i, user in enumerate(users[:10], 1):
        msg += f"{i}. <b>{user['name']}</b>: {user['total']} tasks (M: {user['mirror']}, L: {user['leech']})\n"

    await send_message(message, msg)
