import asyncio
from hmac import new
from pathlib import Path
import logging
from typing import Any
import aiohttp
from cloudflare import Cloudflare
from cloudflare.types.zones import Zone
from cloudflare.types.dns import ARecord
import toml

config: dict[str, Any] = {}

cf_client: Cloudflare
record_cache: dict[str, str] = {}

logging.basicConfig(
    format="{asctime} - ({levelname}) {name} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    level=logging.WARN,
)

logger = logging.getLogger("sipd")
logger.setLevel(logging.INFO)

latest_ip = ""  # the latest known IP address


def initial_setup() -> tuple[Cloudflare, Zone]:
    """
    Does initial setup tasks, like loading the config and
    ensuring they're setup correctly.
    """
    global config
    global cf_client

    # check for config.toml, and copy defaults if not present.
    if not Path("./config.toml").exists():
        logger.info("I can't find a configuration to use, trying to copy defaults!")

        try:
            Path("./config.toml").write_text(Path("./config.toml.example").read_text())
            logger.info("copied, please configure sipD, and restart.")
            exit(1)
            return
        except Exception as e:
            logger.error("failed to copy defaults!")
            logger.error(e)
            exit(2)
            return

    config = toml.load("config.toml")
    logger.info("loaded config!")

    logger.info("setting up cloudflare stuff..")
    cf_client = Cloudflare(api_token=config["cloudflare"]["token"])

    populate_record_cache()

    logger.info(
        f"finished! checking for IP changes every {config['general']['check_interval']}ms."
    )


def populate_record_cache():
    records = cf_client.dns.records.list(zone_id=config["cloudflare"]["zone_id"])

    for page in range(0, len(records.result)):
        record = records.result[page]

        if (
            isinstance(record, ARecord)
            and record.name.split(".")[0] in config["cloudflare"]["records_to_update"]
        ):
            record_cache.update({record.name.split(".")[0]: record.id})


def get_record_id(subdomain: str) -> str:
    """evil method to get cf record id"""

    return record_cache.get(subdomain, None)


async def main():
    global latest_ip

    while True:
        async with (
            aiohttp.ClientSession() as session,
            session.get("https://api.ipify.org") as res,
        ):
            new_ip = await res.text()

            if not latest_ip:  # probs just started, make sure this is set.
                latest_ip = new_ip

            if new_ip != latest_ip:
                logger.info(f"IP changed to {new_ip}. pushing updates & running hooks!")

                for record in config["cloudflare"]["records_to_update"]:
                    logger.info(f"updating DNS record for subdomain {record}.")
                    await do_zone_update(get_record_id(record), new_ip)

        await asyncio.sleep(config["general"]["check_interval"] / 1000)


async def do_zone_update(record_id: str, new_ip: str):
    if not record_id:
        logger.error("record id get failed. oops.")
        return

    cf_client.dns.records.edit(
        dns_record_id=record_id,
        zone_id=config["cloudflare"]["zone_id"],
        comment="This record is managed by sipD.",
        content=new_ip,
    )


if __name__ == "__main__":
    logger.info("starting!")
    initial_setup()

    # this is to make sure keyboard interrupts don't spit out shit tons of errors
    loop = asyncio.new_event_loop()

    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("shutting down!")
