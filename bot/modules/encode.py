from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.modules.mirror_leech import Mirror
from bot import bot_loop

async def encode_360p(client, message):
    ffmpeg_cmds = ["-i mltb.video -preset veryfast -c:v libx264 -crf 32 -vf \"scale=640:360\" -c:a libopus -b:a 48k -map 0 -y mltb.mkv -del"]
    bot_loop.create_task(Mirror(client, message, is_leech=True, ffmpeg_cmds=ffmpeg_cmds).new_event())

async def encode_480p(client, message):
    ffmpeg_cmds = ["-i mltb.video -preset veryfast -c:v libx264 -crf 30 -vf \"scale=854:480\" -c:a libopus -b:a 64k -map 0 -y mltb.mkv -del"]
    bot_loop.create_task(Mirror(client, message, is_leech=True, ffmpeg_cmds=ffmpeg_cmds).new_event())

async def encode_720p(client, message):
    ffmpeg_cmds = ["-i mltb.video -preset veryfast -c:v libx264 -crf 28 -vf \"scale=1280:720\" -c:a libopus -b:a 96k -map 0 -y mltb.mkv -del"]
    bot_loop.create_task(Mirror(client, message, is_leech=True, ffmpeg_cmds=ffmpeg_cmds).new_event())

async def encode_1080p(client, message):
    ffmpeg_cmds = ["-i mltb.video -preset veryfast -c:v libx264 -crf 26 -vf \"scale=1920:1080\" -c:a libopus -b:a 128k -map 0 -y mltb.mkv -del"]
    bot_loop.create_task(Mirror(client, message, is_leech=True, ffmpeg_cmds=ffmpeg_cmds).new_event())
