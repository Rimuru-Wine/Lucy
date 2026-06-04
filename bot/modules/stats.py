from asyncio import gather, sleep, wait_for, TimeoutError
from pyrogram.enums import ButtonStyle
from platform import platform, version
from re import search as research
from time import time

from aiofiles.os import path as aiopath
from psutil import (
    Process,
    boot_time,
    cpu_count,
    cpu_freq,
    cpu_percent,
    disk_io_counters,
    disk_usage,
    getloadavg,
    net_io_counters,
    swap_memory,
    virtual_memory,
    process_iter,
    NoSuchProcess,
    AccessDenied,
)

from .. import LOGGER, bot_cache, bot_start_time, bot_loop
from ..core.config_manager import Config, BinConfig
from ..helper.ext_utils.bot_utils import cmd_exec, compare_versions, new_task
from ..helper.ext_utils.status_utils import (
    get_progress_bar_string,
    get_readable_file_size,
    get_readable_time,
)
from ..helper.ext_utils.style import SFMLStyle
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.button_build import ButtonMaker
from ..helper.telegram_helper.message_utils import (
    delete_message,
    edit_message,
    send_message,
)
from ..version import get_version

commands = {
    "aria2": ([BinConfig.ARIA2_NAME, "--version"], r"aria2 version ([\d.]+)"),
    "qBittorrent": ([BinConfig.QBIT_NAME, "--version"], r"qBittorrent v([\d.]+)"),
    "SABnzbd+": (
        [BinConfig.SABNZBD_NAME, "--version"],
        rf"{BinConfig.SABNZBD_NAME}-([\d.]+)",
    ),
    "python": (["python3", "--version"], r"Python ([\d.]+)"),
    "rclone": ([BinConfig.RCLONE_NAME, "--version"], r"rclone v([\d.]+)"),
    "yt-dlp": (["yt-dlp", "--version"], r"([\d.]+)"),
    "ffmpeg": (
        [BinConfig.FFMPEG_NAME, "-version"],
        r"ffmpeg version ([\d.]+(-\w+)?).*",
    ),
    "7z": (["7z", "i"], r"7-Zip ([\d.]+)"),
    "aiohttp": (["uv", "pip", "show", "aiohttp"], r"Version: ([\d.]+)"),
    "pyrotgfork": (["uv", "pip", "show", "pyrotgfork"], r"Version: ([\d.]+)"),
    "gapi": (["uv", "pip", "show", "google-api-python-client"], r"Version: ([\d.]+)"),
    "mega": (
        [
            "python3",
            "-c",
            "from mega import MegaApi; print(MegaApi('test').getVersion())",
        ],
        r"v?([\d.]+)",
    ),
}


async def get_stats(event, key="home"):
    user_id = event.from_user.id
    btns = ButtonMaker()
    if key == "home":
        btns = ButtonMaker()
        btns.data_button("𝖡𝗈𝗍 𝖲𝗍𝖺𝗍𝗌", f"stats {user_id} stbot")
        btns.data_button("𝖮𝖲 𝖲𝗍𝖺𝗍𝗌", f"stats {user_id} stsys")
        btns.data_button("𝖱𝖾𝗉𝗈 𝖲𝗍𝖺𝗍𝗌", f"stats {user_id} strepo")
        btns.data_button("𝖯𝗄𝗀𝗌 𝖲𝗍𝖺𝗍𝗌", f"stats {user_id} stpkgs")
        btns.data_button("𝖳𝖺𝗌𝗄 𝖫𝗂𝗆𝗂𝗍𝗌", f"stats {user_id} tlimits")
        btns.data_button("𝖲𝗒𝗌 𝖳𝖺𝗌𝗄𝗌", f"stats {user_id} systasks")
        msg = "⌬ <b><i>𝖡𝗈𝗍 & 𝖮𝖲 𝖲𝗍𝖺𝗍𝗂𝗌𝗍𝗂𝖼𝗌!</i></b>"
    elif key == "stbot":
        total, used, free, disk = disk_usage("/")
        swap = swap_memory()
        memory = virtual_memory()
        disk_io = disk_io_counters()
        msg = SFMLStyle.BOT_STATS.format(
            bot_uptime=get_readable_time(time() - bot_start_time),
            ram_bar=get_progress_bar_string(memory.percent),
            ram=memory.percent,
            ram_u=get_readable_file_size(memory.used),
            ram_f=get_readable_file_size(memory.available),
            ram_t=get_readable_file_size(memory.total),
            swap_bar=get_progress_bar_string(swap.percent),
            swap=swap.percent,
            swap_u=get_readable_file_size(swap.used),
            swap_f=get_readable_file_size(swap.free),
            swap_t=get_readable_file_size(swap.total),
            disk_bar=get_progress_bar_string(disk),
            disk=disk,
            disk_read=f"{get_readable_file_size(disk_io.read_bytes)} ({get_readable_time(disk_io.read_time / 1000)})" if disk_io else "𝖠𝖼𝖼𝖾𝗌𝗌 𝖣𝖾𝗇𝗂𝖾𝖽",
            disk_write=f"{get_readable_file_size(disk_io.write_bytes)} ({get_readable_time(disk_io.write_time / 1000)})" if disk_io else "𝖠𝖼𝖼𝖾𝗌𝗌 𝖣𝖾𝗇𝗂𝖾𝖽",
            disk_u=get_readable_file_size(used),
            disk_f=get_readable_file_size(free),
            disk_t=get_readable_file_size(total),
        )
    elif key == "stsys":
        cpu_usage = cpu_percent(interval=0.5)
        msg = SFMLStyle.SYS_STATS.format(
            os_uptime=get_readable_time(time() - boot_time()),
            os_version=version(),
            os_arch=platform(),
            up_data=get_readable_file_size(net_io_counters().bytes_sent),
            dl_data=get_readable_file_size(net_io_counters().bytes_recv),
            pkt_sent=str(net_io_counters().packets_sent)[:-3],
            pkt_recv=str(net_io_counters().packets_recv)[:-3],
            tl_data=get_readable_file_size(net_io_counters().bytes_recv + net_io_counters().bytes_sent),
            cpu_bar=get_progress_bar_string(cpu_usage),
            cpu=cpu_usage,
            cpu_freq=f"{cpu_freq().current / 1000:.2f} 𝖦𝖧𝗓" if cpu_freq() else "𝖠𝖼𝖼𝖾𝗌𝗌 𝖣𝖾𝗇𝗂𝖾𝖽",
            sys_load="%, ".join(str(round((x / cpu_count() * 100), 2)) for x in getloadavg()) + "%, (1𝗆, 5𝗆, 15𝗆)",
            p_core=cpu_count(logical=False),
            v_core=cpu_count(logical=True) - cpu_count(logical=False),
            total_core=cpu_count(logical=True),
            cpu_use=len(Process().cpu_affinity()),
        )
    elif key == "strepo":
        last_commit, changelog = "𝖭𝗈 𝖣𝖺𝗍𝖺", "𝖭/𝖠"
        if await aiopath.exists(".git"):
            last_commit = (
                await cmd_exec(
                    "git log -1 --pretty='%cd ( %cr )' --date=format-local:'%d/%m/%Y'",
                    True,
                )
            )[0]
            changelog = (
                await cmd_exec(
                    "git log -1 --pretty=format:'<code>%s</code> <b>𝖡𝗒</b> %an'", True
                )
            )[0]
        official_v = (
            await cmd_exec(
                f"curl -o latestversion.py https://raw.githubusercontent.com/SilentDemonSD/WZML-X/{Config.UPSTREAM_BRANCH}/bot/version.py -s && python3 latestversion.py && rm latestversion.py",
                True,
            )
        )[0]
        msg = SFMLStyle.REPO_STATS.format(
            last_commit=last_commit,
            bot_version=get_version(),
            lat_version=official_v,
            commit_details=changelog,
            remarks=compare_versions(get_version(), official_v),
        )
    elif key == "stpkgs":
        ver = bot_cache.get("eng_versions", {})
        msg = SFMLStyle.PKGS_STATS.format(
            python=ver.get("python", "𝖭/𝖠"),
            aria2=ver.get("aria2", "𝖭/𝖠"),
            qbit=ver.get("qBittorrent", "𝖭/𝖠"),
            sabnzbd=ver.get("SABnzbd+", "𝖭/𝖠"),
            rclone=ver.get("rclone", "𝖭/𝖠"),
            ytdlp=ver.get("yt-dlp", "𝖭/𝖠"),
            ffmpeg=ver.get("ffmpeg", "𝖭/𝖠"),
            sevenz=ver.get("7z", "𝖭/𝖠"),
            aiohttp=ver.get("aiohttp", "𝖭/𝖠"),
            pyrotgfork=ver.get("pyrotgfork", "𝖭/𝖠"),
            gapi=ver.get("gapi", "𝖭/𝖠"),
            mega=ver.get("mega", "𝖭/𝖠"),
        )
    elif key == "tlimits":
        msg = SFMLStyle.BOT_LIMITS.format(
            DL=Config.DIRECT_LIMIT or "∞",
            TL=Config.TORRENT_LIMIT or "∞",
            GL=Config.GD_DL_LIMIT or "∞",
            YL=Config.YTDLP_LIMIT or "∞",
            PL=Config.PLAYLIST_LIMIT or "∞",
            ML=Config.MEGA_LIMIT or "∞",
            CL=Config.CLONE_LIMIT or "∞",
            LL=Config.LEECH_LIMIT or "∞",
            TV=get_readable_time(Config.VERIFY_TIMEOUT) if Config.VERIFY_TIMEOUT else "𝖣𝗂𝗌𝖺𝖻𝗅𝖾𝖽",
            UTI=Config.USER_TIME_INTERVAL or "0",
            UT=Config.USER_MAX_TASKS or "∞",
            BT=Config.BOT_MAX_TASKS or "∞",
        )

    elif key == "systasks":
        try:
            processes = []
            for proc in process_iter(
                ["pid", "name", "cpu_percent", "memory_percent", "username"]
            ):
                try:
                    info = proc.info
                    if (
                        info.get("cpu_percent", 0) > 1.0
                        or info.get("memory_percent", 0) > 1.0
                    ):
                        processes.append(info)
                except (NoSuchProcess, AccessDenied):
                    continue
            processes.sort(
                key=lambda x: x.get("cpu_percent", 0) + x.get("memory_percent", 0),
                reverse=True,
            )
            processes = processes[:15]
        except Exception:
            processes = []

        msg = SFMLStyle.SYS_TASKS

        if processes:
            for i, proc in enumerate(processes, 1):
                name = proc.get("name", "Unknown")[:20]
                cpu = proc.get("cpu_percent", 0)
                mem = proc.get("memory_percent", 0)
                user = proc.get("username", "Unknown")[:10]
                msg += f"┠ <b>{i:2d}.</b> <code>{name}</code>\n┃    🔹 <b>𝖢𝖯𝖴:</b> {cpu:.1f}% | <b>𝖬𝖤𝖬:</b> {mem:.1f}%\n┃    👤 <b>𝖴𝗌𝖾𝗋:</b> {user} | <b>𝖯𝖨𝖣:</b> {proc['pid']}\n"
                btns.data_button(f"{i}", f"stats {user_id} killproc {proc['pid']}")
            msg += SFMLStyle.SYS_TASKS_FOOTER
        else:
            msg += SFMLStyle.SYS_TASKS_NOT_FOUND

        btns.data_button("🔄 𝖱𝖾𝖿𝗋𝖾𝗌𝗁", f"stats {user_id} systasks", "header")

    btns.data_button(SFMLStyle.BACK_BT, f"stats {user_id} home", "footer")
    btns.data_button(
        SFMLStyle.CLOSE_BT, f"stats {user_id} close", "footer", style=ButtonStyle.DANGER
    )
    return msg, btns.build_menu(8 if key == "systasks" else 2)


@new_task
async def bot_stats(_, message):
    msg, btns = await get_stats(message)
    await send_message(message, msg, btns)


@new_task
async def stats_pages(_, query):
    data = query.data.split()
    message = query.message
    user_id = query.from_user.id
    if user_id != int(data[1]):
        await query.answer("Not Yours!", show_alert=True)
    elif data[2] == "close":
        await query.answer()
        await delete_message(message, message.reply_to_message)
    elif data[2] == "killproc":
        if not await CustomFilters.owner(_, query):
            await query.answer("Sorry! You cannot Kill System Tasks!", show_alert=True)
            return
        pid = int(data[3])
        try:
            process = Process(pid)
            proc_name = process.name()
            process.terminate()
            await sleep(2)
            if process.is_running():
                process.kill()
                status = "🔥 Force killed"
            else:
                status = "✅ Terminated"
            await query.answer(f"{status}: {proc_name} (PID: {pid})", show_alert=True)
        except NoSuchProcess:
            await query.answer(
                "❌ Process not found or already terminated!", show_alert=True
            )
        except AccessDenied:
            await query.answer(
                "❌ Access denied! Cannot kill this process.", show_alert=True
            )
        except Exception as e:
            await query.answer(f"❌ Error: {str(e)}", show_alert=True)

        msg, btns = await get_stats(query, "systasks")
        await edit_message(message, msg, btns)
    else:
        if data[2] == "systasks" and not await CustomFilters.sudo(_, query):
            await query.answer("Sorry! You cannot open System Tasks!", show_alert=True)
            return
        await query.answer()
        msg, btns = await get_stats(query, data[2])
        await edit_message(message, msg, btns)


async def get_version_async(command, regex, timeout=5):
    try:
        out, err, code = await wait_for(cmd_exec(command), timeout=timeout)
        if code != 0:
            return f"Error: {err}"
        match = research(regex, out)
        return match.group(1) if match else "-"
    except TimeoutError:
        return "Timeout"
    except Exception as e:
        return f"Exception: {str(e)}"


async def retry_mega_version():
    await sleep(60)
    command, regex = commands["mega"]
    version = await get_version_async(command, regex, timeout=10)
    if version != "Timeout" and not version.startswith("Exception"):
        bot_cache["eng_versions"]["mega"] = version
        LOGGER.info(f"MegaSDK Version Fetched: {version}")
    else:
        LOGGER.warning(f"Failed to fetch MegaSDK Version: {version}")


@new_task
async def get_packages_version():
    tasks = [get_version_async(command, regex) for command, regex in commands.values()]
    versions = await gather(*tasks)
    bot_cache["eng_versions"] = {}
    for tool, ver in zip(commands.keys(), versions):
        bot_cache["eng_versions"][tool] = ver
    if await aiopath.exists(".git"):
        last_commit = await cmd_exec(
            "git log -1 --date=short --pretty=format:'%cd <b>From</b> %cr'", True
        )
        last_commit = last_commit[0]
    else:
        last_commit = "No UPSTREAM_REPO"
    bot_cache["commit"] = last_commit

    if bot_cache["eng_versions"]["mega"] in ["Timeout", "N/A"] or bot_cache[
        "eng_versions"
    ]["mega"].startswith("Exception"):
        bot_loop.create_task(retry_mega_version())

    LOGGER.info("Fetched Package Versions!")
