import asyncio
from pathlib import Path
import logging
import toml

config = {} # we'll init config later

logging.basicConfig(
    format="{asctime} - ({levelname}) {name} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    level=logging.INFO
)

logger = logging.getLogger("sipd")

async def main():
    pass

def initial_setup():
    """
    Does initial setup tasks, like loading the config and
    ensuring they're setup correctly.
    """
    global config
    
    # check for config.toml, and copy defaults if not present.
    if not Path("./config.toml").exists():
        logger.info("I can't find a configuration to use, trying to copy defaults!")
        
        try:
            Path("./config.toml").write_text(Path("./config.toml.example").read_text())
            logger.info("Copied. Please configure sipD, and restart.")
            exit(1)
            return
        except Exception as e:
            logger.error("Failed to copy defaults!")
            logger.error(e)
            exit(2)
            return

    config = toml.load("config.toml")
    logger.info("Loaded config!")
    logger.info(config)

if __name__ == "__main__":
    logger.info("Starting!")
    initial_setup()
    asyncio.run(main())