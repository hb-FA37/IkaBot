import argparse
import logging
from logging.handlers import RotatingFileHandler
import os

from .database import init_database, Guild, session

guild_join_message_no_log_channel = """
IkaBot has just joined! Please set up the used log channel by using '{0}set-log-channel'
to be able to fully use the bot.
"""

guild_join_message_with_log_channel = """
IkaBot has just joined! Using this channel as the default log channel, this can be changed
using the 'set-log-channel' command.
"""

def _setup_logging(logpath, print_debug=False):
    """Setup logging.
    Args:
        logpath (str): directory to dump log files in.
        print_debug (bool): print debug messages to the console/terminal, default is False.
    """

    log_format_string = "%(asctime)s - %(levelname)s - %(name)s :: %(message)s"

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(log_format_string)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(logging.DEBUG if print_debug else logging.INFO)
    logger.addHandler(handler)

    if not logpath:
        logging.warning("logpath not provided, logs are not saved!")
        return

    formatter = logging.Formatter(log_format_string)
    handler = RotatingFileHandler(
        filename=os.path.join(logpath, "ikabot.log"),
        encoding="utf-8",
        # 10 MB log files.
        maxBytes=1024*1024*10,
        backupCount=10,
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--debug", action="store_true", default=False,
         help="print debug info.",
    )
    parser.add_argument(
        "--data-dir",
        help="directory to store all data and log files, takes priority over the environment variable 'IKA_DATA_DIR'.",
        default=os.getenv("IKA_DATA_DIR"),
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if not os.path.exists(args.data_dir):
        raise RuntimeError("""
            data directory not configured, set this either using the IKA_DATA_DIR
            environment variable or the --data-dir commandline option.
        """)

    if not os.path.exists(args.data_dir):
        raise RuntimeError(
            "IkaBot root data directory {0} does not exist, please create this first.".format(args.data_dir)
        )

    db_file = os.path.join(args.data_dir, "ikabot.db")
    log_dir = os.path.join(args.data_dir, "logs")
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)

    _setup_logging(log_dir, print_debug=args.debug)
    init_database(db_file)

    from .base import bot
    from .entrybanner import EntryBannerCog

    @bot.event
    async def on_ready():
        """Invoked when the bot is ready for use."""
        logging.getLogger("ikabot").info("IkaBot ready for use!")
        bot.add_cog(EntryBannerCog())

    @bot.event
    async def on_guild_join(guild):
        """Invoked when a guild is created or joined by the bot.

        Args:
            guild (discord.Guild): guild.
        """
        guild_entry = session.get(Guild, guild.id)
        if guild_entry:
            # Guild is known to the bot.
            return

        # New guild, register it, say hi and check if there is a log channel we
        # can write to.
        guild_entry = Guild(snowflake=guild.id)
        try:
            session.add(guild_entry)
            session.commit()
        except:
            session.rollback()
            raise

        channel = guild.system_channel
        if channel and channel.permissions_for(guild.me).send_messages:
            try:
                guild_entry.log_channel_snowflake = channel.id
                session.commit()
            except:
                session.rollback()
                raise

            await channel.send(guild_join_message_with_log_channel)
        else:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    await channel.send(
                        guild_join_message_no_log_channel.format(bot.command_prefix)
                    )
                    break

    logging.getLogger("ikabot").info("starting IkaBot..")
    bot.run(_fetch_bot_token())
