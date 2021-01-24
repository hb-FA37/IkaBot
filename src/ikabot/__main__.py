import os
import logging


def _setup_logging(logpath, print_debug=False):
    """Setup logging.
    Args:
        logpath (str): directory to dump log files in.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(levelname)s - %(name)s :: %(message)s")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG if print_debug else logging.INFO)
    logger.addHandler(handler)

    if not logpath:
        logging.info("file logging not configured")
        return

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s :: %(message)s")
    handler = logging.FileHandler(
        filename=os.path.join(logpath, "ikabot.log"),
        encoding="utf-8",
        mode="a",
    )
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)


def _fetch_bot_token():
    """Fetch the token to use from the environment
    Raises:
        RuntimeError: raised if no token can be fetched.
    Returns:
        str: discord bot token.
    """
    token = os.getenv("IKA_DISCORD_TOKEN")
    if token:
        return token
    raise RuntimeError("no IkaBot discord token configured")


def _parse_args():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--debug", action="store_true", default=False,
         help="print debug info.",
    )
    parser.add_argument(
        "--log-dir",
        help="directory to log files into, takes priority over the environment setting.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    _setup_logging(
        args.log_dir or os.getenv("IKA_LOG_PATH"),
        print_debug=args.debug,
    )

    from .base import bot
    from .entrybanner import EntryBannerCog, EntryBannerDataStore

    if not os.getenv("IKA_DATA_PATH"):
        raise RuntimeError("IKA_DATA_PATH has not been configured")

    eb_data = EntryBannerDataStore(
        os.path.join(os.getenv("IKA_DATA_PATH"), "entrybanner.json")
    )
    eb_data.load()

    @bot.event
    async def on_ready():
        logging.getLogger().info("IkaBot ready for use!")
        bot.add_cog(EntryBannerCog(bot, eb_data))

    bot.run(_fetch_bot_token())
