"""
Simple commands.
"""

import asyncio
from collections import OrderedDict
import logging
import string

import discord
from discord.ext import commands

from ikabot import REGIONAL_EMOJI_STRINGS
from .base import bot


logger = logging.getLogger(__name__)


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
# TODO; open up access
@commands.is_owner()
async def purge_reactions_of_user(ctx, user: discord.User, amount: int=100):
    """ Purges all reactions of a certain user in the called channel.

    Args:
        ctx (discord.ext.commands.Context): context.
        user (discord.User): users who's reactions to purge.
        amount (int, optional): amount of messages to process in the invoked channel,
            defaults to 100.
    """
    if amount < 0:
        await ctx.reply(
            "Amount must be a positive number.", mention_author=False
        )
        return
    if amount > 1000:
        await ctx.reply(
            "Amount must be less then 1000", mention_author=False
        )
        return

    async for msg in ctx.channel.history(limit=amount):
        for reaction in msg.reactions:
            await reaction.remove(user)

    await ctx.reply(
        "Purged reactions of that user.", mention_author=False
    )


@bot.command("purge-message-reactions", ignore_extra=False)
# TODO; open up access
@commands.is_owner()
async def purge_reactions_of_message(ctx, message: discord.Message):
    """Purges all reactions of a certain emote of a given message.
    This tool is mostly handy to remove the reaction of a banned or deleted account
    as this cannot be done using the discord interface.


    Args:
        ctx (discord.ext.commands.Context): context.
        message (discord.Message): message from which to remove reactions from.

    """
    if not message.reactions:
        await ctx.reply("Message has no reactions to purge.", mention_author=False)
        return

    # Creates a list of emoji's their string representation to purge.
    # the invoker needs to vote which one to purge from the message.

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
            # Emoji or PartialEmoji.
            msg +=  letter + " - " + reaction.emoji.name + "\n"

    msg += "```"

    menu_message = await ctx.send(msg)
    for key in reaction_mapping.keys():
        await menu_message.add_reaction(key)

    def check(reaction, user):
        return reaction.message == menu_message and user == ctx.author and \
            str(reaction.emoji) in reaction_mapping

    try:
        reaction, _ = await bot.wait_for("reaction_add", check=check, timeout=20.0)
    except asyncio.TimeoutError:
        await message.reply("Timed out. You have 20 seconds to select which emote to remove.", mention_author=False)
        return

    await reaction_mapping[reaction.emoji].clear()
    await menu_message.edit(
        content="Removed {0} reaction.".format(reaction.emoji if isinstance(reaction.emoji, str) else reaction.emoji.name)
    )
    await menu_message.clear_reactions()
