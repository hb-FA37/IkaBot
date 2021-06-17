"""
Base and global setup of the bot.
"""

import logging
import sys
import traceback

import discord
from discord.ext import commands

from .database import Guild, session


logger = logging.getLogger(__name__)


# Intents is needed to get the members, otherwise we cannot do any random member
# lookup except for the bot user or use the on_member_joined callback.
intents = discord.Intents.default()
intents.members = True

# Create the bot.
bot = commands.Bot(intents=intents, command_prefix="$")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        # Silently ignore checks that failed.
        return

    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument) or isinstance(error, discord.ext.commands.errors.BadArgument):
        command = ""
        if ctx.prefix and ctx.command:
            command = " {0}{1}".format(ctx.prefix, ctx.command)

        await ctx.reply("{0} invalid arguments for{1}".format(
            ctx.author.mention, command
        ), mention_author=False)
        return

    logger.exception('ignoring exception in command {0}:'.format(ctx.command))

    print("ignoring exception in command {0}:".format(ctx.command), file=sys.stderr)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


# Other.


@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    logger.info("IkaBot shutting down..")
    await ctx.reply("Shutting down...")
    await ctx.bot.logout()
    logger.info("IkaBot shut down.")
