from speedtest import Speedtest, ConfigRetrievalError

from .. import LOGGER
from ..helper.telegram_helper.message_utils import (
    send_message,
    edit_message,
    delete_message,
)
from ..helper.ext_utils.bot_utils import new_task, sync_to_async
from ..helper.ext_utils.status_utils import get_readable_file_size
from ..helper.ext_utils.style import SFMLStyle


@new_task
async def speedtest(_, message):
    speed = await send_message(message, "<i>Initiating Speedtest...</i>")
    try:
        speed_results = await sync_to_async(Speedtest)
        await sync_to_async(speed_results.get_best_server)
        await sync_to_async(speed_results.download)
        await sync_to_async(speed_results.upload)
    except ConfigRetrievalError:
        await edit_message(
            speed,
            "<b>ERROR:</b> <i>Can't connect to Server at the Moment, Try Again Later !</i>",
        )
        return
    speed_results.results.share()
    result = speed_results.results.dict()
    string_speed = SFMLStyle.SPEEDTEST_RESULT.format(
        upload=get_readable_file_size(result['upload'] / 8),
        download=get_readable_file_size(result['download'] / 8),
        ping=result['ping'],
        time=result['timestamp'],
        sent=get_readable_file_size(int(result['bytes_sent'])),
        received=get_readable_file_size(int(result['bytes_received'])),
        name=result['server']['name'],
        country=result['server']['country'],
        cc=result['server']['cc'],
        sponsor=result['server']['sponsor'],
        latency=result['server']['latency'],
        lat=result['server']['lat'],
        lon=result['server']['lon']
    )
    try:
        await send_message(message, string_speed, photo=result["share"])
        await delete_message(speed)
    except Exception as e:
        LOGGER.error(str(e))
        await edit_message(speed, string_speed)
