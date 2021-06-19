import logging
import re

from discord.ext import commands

from .base import NoLogChannelConfigured
from .database import EntryRegex, EntryRegexMeta, EntryBan, Guild, session


logger = logging.getLogger(__name__)


class EntryBannerError(Exception):

   def __init__(self, message):
        self.message = message


class EntryBannerCog(commands.Cog):

    COMMAND_NAME = "entrybanner"

    async def cog_command_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandInvokeError):
            original = error.original

            if isinstance(original, NoLogChannelConfigured):
                await ctx.reply(
                    "A log channel must be configured before this command can be invoked.", mention_author=False
                )
                return

            if isinstance(original, EntryBannerError):
                await ctx.reply(error.message, mention_author=False)
                return

        await ctx.reply("Internal error. If this persists please contact the developer.", mention_author=False)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = session.get(Guild, member.guild.id)
        if not guild or not guild.entry_banner_enabled:
            return

        log_channel = member.guild.get_channel(guild.log_channel_snowflake)
        if log_channel is None:
            logger.error("guild {0} ({1}) does not have a log channel configured, skipping member entry validation.".format(
                member.guild, member.guild.id
            ))
            return

        await self._validate_entry(member, guild, log_channel)

    async def _validate_entry(self, member, guild, log_channel):
        """Validate a members against the entry regexes and bans them if one of them matches their name.

        Args:
            member (discord.member.Member): member to validate.
            guild (ikabot.database.Guild): database guild object.
            log_channel (discord.abc.GuildChannel): channel to write message to.
        """
        entry_regex = self._validate_regexes(guild, member)
        if entry_regex is None:
            # No regex matches.
            return

        logger.info("banning {0} ({1}) from {2} ({3}) due to entry regex {4}".format(
            member, member.id, member.guild, member.guild.id, entry_regex.id,
        ))

        await member.ban(
            reason="Banned by entrybanner (id: {0})".format(entry_regex.id),
            delete_message_days=0,
        )
        await log_channel.send("Banned {0} ({1}) due to entry regex id {2}".format(
            member, member.id, entry_regex.id
        ))

        try:
            session.add(
                EntryBan(
                    regex_id=entry_regex.id,
                    user_name=str(member),
                    user_snowflake=member.id,
                )
            )
            session.commit()
        except:
            session.rollback()
            raise

        logger.info("banned {0} ({1}) from {2} ({3}) due to regex {4}".format(
            member, member.id, member.guild, member.guild.id, entry_regex.id,
        ))

    def _validate_regexes(self, guild, member):
        """Validate a member against the entry regexes and return the first one
        that matches.

        Args:
            guild (ikabot.database.Guild): database guild object.
            member (discord.member.Member): member to validate.
        """
        for entry_regex in guild.entry_regexes:
            if not entry_regex.enabled:
                continue

            name = member.name.lower() if entry_regex.lowercase else member.name
            logger.debug("matching name '{0}' to regex id {1}".format(
                member.name, entry_regex.id
            ))
            if re.match(entry_regex.regex, name):
                logger.debug("name '{0}' matched regex id {1}".format(
                    member.name, entry_regex.id
                ))
                return entry_regex

        return None

    # Commands.

    # TODO; open up access
    @commands.has_permissions(administrator=True)
    @commands.group(name=COMMAND_NAME)
    async def invoke(self, ctx):
        if ctx.invoked_subcommand is None:
            # TODO; add help.
            await ctx.reply("entrybanner help is here!", mention_author=False)
            return

        guild = session.get(Guild, ctx.guild.id)
        log_channel = ctx.guild.get_channel(guild.log_channel_snowflake)
        if not log_channel:
            raise NoLogChannelConfigured()

    # Basic #

    @invoke.command(ignore_extra=False)
    async def help(self, ctx):
        # TODO; add help.
        await ctx.reply("entrybanner help is here!", mention_author=False)

    @invoke.command(ignore_extra=False)
    async def info(self, ctx):
        guild = session.get(Guild, ctx.guild.id)
        msg = "Enabled: {0}".format(guild.entry_banner_enabled)
        # TODO; add more stats.
        await ctx.reply(msg, mention_author=False)

    @invoke.command(ignore_extra=False)
    async def enable(self, ctx):
        guild = session.get(Guild, ctx.guild.id)
        guild.entry_banner_enabled = True
        try:
            session.commit()
        except:
            session.rollback()
            raise

        logger.info("enabled entrybanner for {0} ({1}), done by {2} ({3})".format(
            ctx.guild, ctx.guild.id, ctx.author, ctx.author.id
        ))
        await ctx.reply("Entrybanner has been enabled.", mention_author=False)

    @invoke.command(ignore_extra=False,)
    async def disable(self, ctx):
        guild = session.get(Guild, ctx.guild.id)
        guild.entry_banner_enabled = False
        try:
            session.commit()
        except:
            session.rollback()
            raise

        logger.info("disabled entrybanner for {0} ({1}), done by {2} ({3})".format(
            ctx.guild, ctx.guild.id, ctx.author, ctx.author.id
        ))
        await ctx.reply("Entrybanner has been disabled.", mention_author=False)


    # Matching #

    @invoke.group(name="regex", invoke_without_command=True)
    async def regex(self, ctx):
        # TODO; add help.
        await ctx.reply("regex help is here!", mention_author=False)

    @regex.command(name="add", ignore_extra=False)
    async def add_regex(self, ctx, regex_str: str, lowercase: bool=False):
        try:
            _ = re.compile(regex_str)
        except Exception as err:
            msg = "Error, failed to compile the provided regex:\n{0}".format(str(err))
            logger.exception("failed to compile regex '{0}'".format(regex_str))
            raise EntryBannerError(msg)

        regex = EntryRegex(
            regex=regex_str, lowercase=lowercase, guild_snowflake=ctx.guild.id
        )
        metadata = EntryRegexMeta(
            regex=regex, created_name=str(ctx.author), created_snowflake=ctx.author.id,
        )

        try:
            session.add(regex)
            session.add(metadata)
            session.commit()
        except:
            session.rollback()
            raise

        await ctx.reply("New regex has been added with id {0}.".format(regex.id), mention_author=False)

    @regex.command(name="remove", ignore_extra=False)
    async def remove_regex(self, ctx, id_: int):
        regex = session.get(EntryRegex, id_)
        if regex is None:
            await ctx.reply("Regex id does not exist.", mention_author=False)
            return

        if ctx.guild.id != regex.guild_snowflake:
            await ctx.reply("Regex id is invalid.", mention_author=False)
            return

        try:
            session.delete(regex)
            session.commit()
        except:
            session.rollback()
            raise

        await ctx.reply("Removed regex with id {0}.".format(str(id_)), mention_author=False)

    @regex.command(name="list", ignore_extra=False)
    async def list_regexes(self, ctx):
        guild = session.get(Guild, ctx.guild.id)
        if len(guild.entry_regexes) == 0:
            await ctx.reply("No regexes have been added.", mention_author=False)
            return

        lines = []
        for i, regex in enumerate(guild.entry_regexes):
            options = []
            if not regex.enabled:
                options.append("disabled")
            if regex.lowercase:
                options.append("lowercases")

            lines.append(
                "{0} {1}{2}".format(
                    i, regex.regex, "    {0}".format("/".join(options) if options else "")
                )
            )

        await ctx.reply("\n".join(lines), mention_author=False)

    @regex.command(name="enable", ignore_extra=False)
    async def enable_regex(self, ctx, id_: int):
        regex = session.get(EntryRegex, id_)
        if regex is None:
            await ctx.reply("Regex id does not exist", mention_author=False)
            return

        if ctx.guild.id != regex.guild_snowflake:
            await ctx.reply("Invalid regex id.", mention_author=False)
            return

        try:
            regex.enabled = True
            session.commit()
        except:
            session.rollback()
            raise

        await ctx.reply("enabled.", mention_author=False)

    @regex.command(name="disable", ignore_extra=False)
    async def disable_regex(self, ctx, id_: int):
        regex = session.get(EntryRegex, id_)
        if regex is None:
            await ctx.reply("Regex id does not exist", mention_author=False)
            return

        if ctx.guild.id != regex.guild_snowflake:
            await ctx.reply("Invalid regex id", mention_author=False)
            return

        try:
            regex.enabled = False
            session.commit()
        except:
            session.rollback()
            raise

        await ctx.reply("disabled.", mention_author=False)
