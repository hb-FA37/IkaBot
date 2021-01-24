import asyncio
import logging
import os
import string
import sys
import traceback

from collections import OrderedDict

import discord
from discord.ext import commands

from ikabot import REGIONAL_EMOJI_STRINGS


logger = logging.getLogger(__name__)


# Intents is needed to get the members, otherwise we cannot do any random member
# lookup except for the bot user or use the on_member_joined callback.
intents = discord.Intents.default()
intents.members = True

# Create the bot.
bot = commands.Bot(intents=intents, command_prefix="$")

# @bot.event
async def on_command_error(ctx, error):
    """Eat all check or argument failures, raise exceptions for everthing else."""
    if isinstance(error, commands.errors.CheckFailure):
        return

    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument) or isinstance(error, discord.ext.commands.errors.BadArgument):
        command = ""
        if ctx.prefix and ctx.command:
            command = " {0}{1}".format(ctx.prefix, ctx.command)

        await ctx.send("{0} invalid arguments for{1}".format(
            ctx.author.mention, command
        ))
        return

    logger.debug('ignoring exception in command {0}:'.format(ctx.command))
    # TODO; ??
    print('Ignoring exception in command {0}:'.format(ctx.command), file=sys.stderr)
    traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)


# Simple utility commands.


@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    logger.info("IkaBot shutting down..")
    await ctx.reply("shutting down..")
    await ctx.bot.logout()
    logger.info("IkaBot shut down")


@bot.command()
@commands.is_owner()
async def ping(ctx):
    await ctx.reply("pong!")


@bot.command()
@commands.is_owner()
async def pong(ctx):
    await ctx.reply("ping!")


# Mass delete reaction tools.


@bot.command("purge-user-reactions", ignore_extra=False)
@commands.is_owner()
async def purge_reactions_of_user(ctx, user: discord.User, amount: int=100):
    """
    Purges all reactions of a certain user in the called channel.
    """
    if amount < 0:
        await ctx.send(
            "{0} amount must be a positive number.".format(ctx.author.mention)
        )
        return
    if amount > 512:
        await ctx.send(
            "{0} amount must be less then 512".format(ctx.author.mention)
        )
        return

    async for msg in ctx.channel.history(limit=amount):
        for reaction in msg.reactions:
            await reaction.remove(user)


@bot.command("purge-message-reactions", ignore_extra=False)
@commands.is_owner()
async def purge_reactions_of_message(ctx, message: discord.Message):
    """
    Purges all reactions of a certain emote of a given message. This tool is mostly handy to remove
    the reaction of a banner or deleted account as that cannot be removed to the discord interface.

    It uses a fancy setup menu to select which emote to purge.
    """
    if not message.reactions:
        await ctx.reply("message has no reactions to purge.")
        return

    msg = "React to the letter for the emote to purge:\n```\n"

    alphabet = list(string.ascii_lowercase)
    reaction_mapping = OrderedDict()

    for reaction in message.reactions:
        letter = alphabet.pop(0)
        reaction_mapping[REGIONAL_EMOJI_STRINGS[letter]] = reaction

        if isinstance(reaction.emoji, str):
            # Unicode emoji.
            msg +=  letter + " - " + reaction.emoji + "\n"
        else:
            # Emoji or PartialEmoji
            msg +=  letter + " - " + reaction.emoji.name + "\n"

    msg += "```"

    menu_message = await ctx.send(msg)
    for key in reaction_mapping.keys():
        await menu_message.add_reaction(key)

    def check(reaction, user):
        return reaction.message == menu_message and user == ctx.author and \
            str(reaction.emoji) in reaction_mapping

    try:
        reaction, _ = await bot.wait_for('reaction_add', check=check, timeout=20.0)
    except asyncio.TimeoutError:
        await message.reply("Command timed out, you have 20 seconds to select which emote to remove.")
        return

    await reaction_mapping[reaction.emoji].clear()
    await menu_message.edit(
        content="cleared {0}".format(reaction.emoji if isinstance(reaction.emoji, str) else reaction.emoji.name)
    )
    await menu_message.clear_reactions()
