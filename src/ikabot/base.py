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


# Setup intents, start with none and add those of the functionality we use.
intents = discord.Intents.none()
intents.bans = True
intents.emojis = True
intents.guilds = True
# intents.guild_messages = True
intents.guild_reactions = True

# Members is a priviliged intent so we _must_ set it explicitly if we want to
# use its related functionality.
intents.members = True


# Create the bot.
bot = commands.Bot(intents=intents, command_prefix="$")


# Logging.


class NoLogChannelConfigured(Exception):
    pass


@bot.command(name="set-log-channel", ignore_extra=False)
@commands.has_permissions(administrator=True)
async def set_log_channel(ctx, channel: discord.TextChannel=None):
    if channel:
        if channel.guild.id != ctx.guild.id:
            await ctx.reply("Invalid channel.")
            return
    else:
        # Set the invoked channel as the log channel.
        channel = ctx.channel

    if not channel.permissions_for(channel.guild.me).send_messages:
        logger.debug(
            "Cannot set log channel to {0} ({1}) in {2} ({3}), no write permissions)".format(
                channel, channel.id, channel.guild, channel.guild.id
            )
        )
        await ctx.reply("IkaBot does not have permission to write to the given channel")
        return

    guild = session.get(Guild, ctx.guild.id)
    try:
        guild.log_channel_snowflake = channel.id
        session.commit()
    except:
        session.rollback()
        raise

    logger.debug("{0} ({1}) set log channel to {2} ({3}) in {4} ({5})".format(
        ctx.author, ctx.author.id, channel.name, channel.id, ctx.guild, ctx.guild.id
    ))
    await channel.send("This channel has been set as the IkaBot log channel.")
    await ctx.reply("Log messages will be written to {0}.".format(channel.mention), mention_author=False)


# Error handling.


@bot.event
async def on_command_error(ctx, error):
    # if isinstance(error, commands.errors.CheckFailure):
    #     # Silently ignore checks that failed.
    #     return

    if isinstance(error, commands.errors.MissingRequiredArgument) :
        await ctx.reply("Error, missing required arguments.", mention_author=False)
        return

    if isinstance(error, commands.errors.BadArgument):
        await ctx.reply("Error, invalid arguments.", mention_author=False)
        return

    if isinstance(error, commands.errors.TooManyArguments):
        await ctx.reply("Error, too many arguments.", mention_author=False)
        return

    if isinstance(error, commands.errors.MissingPermissions):
        await ctx.reply("Error, missing required permisions to execute this command: {0} .".format(
            error.args[0]), mention_author=False
        )
        return

    # The code below is a slightly tweaked default "on_command_error" invocation.

    if bot.extra_events.get('on_command_error', None):
        return

    if hasattr(ctx.command, 'on_error'):
        return

    cog = ctx.cog
    if cog and commands.Cog._get_overridden_method(cog.cog_command_error) is not None:
        return

    # TODO; make it log to a discord channel on my own guild.
    logger.exception('ignoring exception in command {0}:'.format(ctx.command))
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


# Other.


@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    logger.info("IkaBot shutting down..")
    await ctx.reply("Shutting down...")
    await ctx.bot.logout()
    logger.info("IkaBot shut down.")
