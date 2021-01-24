import json
import logging
import os
import re

from datetime import datetime, timezone

from discord.ext import commands


logger = logging.getLogger(__name__)


class EntryBannerError(Exception):
    pass


class InvalidMatcherId(EntryBannerError):
    pass


class EntryBannerCogError(EntryBannerError):

   def __init__(self, message):
        self.message = message


class EntryBannerDataStore(object):
    """
    The 'datastore', bit silly in that we just use a simple json file and constantly
    need to flush all the data to be consistent but 'good enough for now'. At least
    this implementation separates the loading/storing of the rest of the classes and
    they just need to be able to return a proper json representation.

    TODO: replace with a proper database/ORM backend.
    """

    def __init__(self, json_path):
        self.__json_path = json_path
        self.__json = None

    def load(self):
        if self.__json:
            return self.__json

        if not os.path.exists((self.__json_path)):
            self.__json = dict()
        else:
            with open(self.__json_path) as infile:
                self.__json = json.load(infile)

    def get(self):
        if self.__json:
            return self.__json

        self.load()
        return self.__json

    def update(self, guild_entry):
        """Update the datastore with the given guild state.
        Args:
            guild_entry (GuildEntryBanner): the guild whose data just got updated
        """
        self.__json[guild_entry.guild.id] = guild_entry.json()
        self.__store()

    def __store(self):
        with open(self.__json_path, "w") as outfile:
            json.dump(self.__json, outfile, indent=4)


class MemberMatcher(object):

    def __init__(self, pattern, enabled, metadata):
        """Accepts a member and returns if it matches the conditions of this matcher.
        Args:
            pattern (re.Pattern): pattern to match the members name to.
            enabled (bool): is this matcher enabled.
            metadata (dict): dict of additional metadata.
        """
        self.__pattern = pattern
        self.__enabled = enabled
        self.__metadata = metadata or dict()

    @staticmethod
    def create_new_metadata(ctx):
        return {
            "created_by": "{0}#{1}".format(ctx.author.name, ctx.author.discriminator),
            "created_by_id": str(ctx.author.id),
            "created_at": str(datetime.now(timezone.utc)),
            "banned_ids": list(),
        }

    def json(self):
        return {
            "pattern": self.__pattern.pattern,
            "enabled": self.__enabled,
            "metadata": self.__metadata,
        }

    @property
    def enabled(self):
        return self.__enabled

    def enable(self):
        self.__enabled = True

    def disable(self):
        self.__enabled = False

    def add_ban(self, id_):
        self.__metadata["banned_ids"].append(id_)

    def __call__(self, member):
        """
        Args:
            member (discord.Member): member to match.
        Returns:
            bool: true if it matches, false if not or the matching is disabled.
        """
        if self.enabled and self.__pattern.match(member.name):
            return True
        return False

    def __str__(self):
        return str(self.__pattern.pattern)

    def __repr__(self):
        return "MemberMatcher(regex={0}, enabled={1}".format(
            self.__pattern, self.__enabled
        )


class GuildEntryBanner(object):

    def __init__(self, guild, log_channel, enabled, update_callback, matchers=None):
        """Entry banner for a specific guild.
        Args:
            guild (discord.Guild): guild this banner work for.
            log_channel (discord.TextChannel): channel to send logs to, if None the banner does not
                do anything.
            enabled (bool): is it enabled
            matchers ([MemberMatcher], optional): list of MemberMatcher's for this banner.
        """
        self.__guild = guild
        self.__log_channel = log_channel
        self.__enabled = enabled
        self.__matchers = matchers or list()
        self.__update_cb = update_callback

    def json(self):
        return {
            "guild_id": self.__guild.id,
            "log_channel_id": self.__log_channel.id if self.__log_channel else None,
            "enabled": self.__enabled,
            "patterns": [m.json() for m in self.__matchers],
        }

    @property
    def guild(self):
        return self.__guild

    @property
    def log_channel(self):
        return self.__log_channel

    def set_log_channel(self, channel):
        self.__log_channel = channel

    @property
    def enabled(self):
        return self.__enabled

    def enable(self):
        self.__enabled = True
        self.__update_cb(self)

    def disable(self):
        self.__enabled = False
        self.__update_cb(self)

    # Matchers #

    def validate_matcher_id(self, id_):
        if id_ < 0 or id_ > len(self.__matchers):
            raise InvalidMatcherId()

    def add_matcher(self, matcher):
        self.__matchers.append(matcher)
        self.__update_cb(self)
        return len(self.__matchers) - 1

    def pop_matcher(self, id_):
        self.validate_matcher_id(id_)
        self.__update_cb(self)
        return self.__matchers.pop(id_)

    def enable_matcher(self, id_):
        self.validate_matcher_id(id_)
        self.__matchers[id_].enable()
        self.__update_cb(self)

    def disable_matcher(self, id_):
        self.validate_matcher_id(id_)
        self.__matchers[id_].disable()
        self.__update_cb(self)

    def get_pretty_pattern_list(self):
        if len(self.__matchers) == 0:
            return "no patterns have been added yet."

        msg = "Current patterns:"
        for i, matcher in enumerate(self.__matchers):
            msg += "\n{0}. {1}".format(i, str(matcher))

        return msg

    def add_ban(self, member, id_):
        self.__matchers[id_].add_ban(member.id)

    # Matching #

    def validate_member(self, member):
        assert(self.__guild == member.guild)
        if self.enabled:
            return self._validate_member(member)
        return None

    def _validate_member(self, member):
        for id_, matcher in enumerate(self.__matchers):
            if matcher(member):
                return id_
        return None


class EntryBannerCog(commands.Cog):

    COMMAND_NAME = "entrybanner"

    def __init__(self, bot, data_store):
        self.__bot =  bot
        self.__data_store = data_store
        self.__guild_mapping = dict()

    async def cog_command_error(self, ctx, error):
        """Eat all argument failures, our own exceptions and raise exceptions for everything else."""
        if isinstance(error, InvalidMatcherId):
            await ctx.reply("invalid pattern id.")
            return

        if isinstance(error, EntryBannerCogError):
            await ctx.reply(error.message)
            return

        if isinstance(error, commands.errors.MissingRequiredArgument) or isinstance(error, commands.errors.BadArgument):
            await ctx.reply("error; Missing or invalid arguments.")
            return

        if isinstance(error, commands.errors.TooManyArguments):
            await ctx.reply("error; Too many arguments.")
            return

        if isinstance(error, commands.errors.MissingPermissions):
            await ctx.reply("error; {0}".format(error.args[0]))
            return

        await ctx.reply("internal error; If this persists please contact the bot developer.")
        logger.error("Unhandled error in '{0}':\n{1}".format(self.COMMAND_NAME, error))
        raise error

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Do not make a default one if this gets invoked.
        guild_banner = self.__guild_mapping.get(member.guild.id)
        if not guild_banner:
            return
        if guild_banner.log_channel is None:
            logger.warning("{0} ({1}) does not have a log channel configured, skipping join check.".format(
                member.guild.name, member.guild.id
            ))
            return

        matcher_id = guild_banner.validate_member(member)
        if matcher_id:
            await guild_banner.log_channel.send("banning {0}#{1} ({2}) due to pattern {3}.".format(
                member.name, member.discriminator, member.id, matcher_id
            ))
            logger.info("banning {0}#{1} from {2} ({3}) / {4} due to pattern {5}".format(
                member.name, member.discriminator, member.id, member.guild.name, member.guild.id, matcher_id
            ))

            await member.ban(delete_message_days=0)
            guild_banner.add_ban(member, matcher_id)

            logger.debug("banned {0}#{1} from {2} ({3}) / {4} due to pattern {5}".format(
                member.name, member.discriminator, member.id, member.guild.name, member.guild.id, matcher_id
            ))

    @commands.has_permissions(administrator=True)
    @commands.group(name=COMMAND_NAME, invoke_without_command=True)
    async def invoke(self, ctx):
        # TODO; add help.
        await ctx.reply("entrybanner help is here!")

    def _get_guild_banner(self, guild):
        guild_banner = self.__guild_mapping.get(guild.id)
        if not guild_banner:
            guild_banner = self._init_guild_banner(guild)
            self.__guild_mapping[guild.id] = guild_banner
        return guild_banner

    def _init_guild_banner(self, guild):
        guild_entry = GuildEntryBanner(guild, None, self.__data_store.update, False)
        self.__data_store.update(guild_entry)
        return guild_entry

    # Basic #

    @invoke.command(ignore_extra=False)
    async def info(self, ctx):
        msg = "Enabled: {0}".format(self._get_guild_banner(ctx.guild).enabled)
        # TODO; add more stats.
        await ctx.reply(msg)

    @invoke.command(ignore_extra=False)
    async def enable(self, ctx):
        self._get_guild_banner(ctx.guild).enable()
        logger.info("enabled entrybanner for {0} ({1}), done by {2} ({3})".format(
            ctx.guild.name, ctx.guild.id, "{0}#{1}".format(ctx.author.name, ctx.author.discriminator), ctx.author.id
        ))
        await ctx.reply("{0} has been enabled".format(self.COMMAND_NAME))

    @invoke.command(ignore_extra=False,)
    async def disable(self, ctx):
        self._get_guild_banner(ctx.guild).disable()
        logger.info("disabled entrybanner for {0} ({1}), done by {2} ({3})".format(
            ctx.guild.name, ctx.guild.id, "{0}#{1}".format(ctx.author.name, ctx.author.discriminator), ctx.author.id
        ))
        await ctx.reply("{0} has been disabled".format(self.COMMAND_NAME))

    @invoke.command(name="set-log-channel", ignore_extra=False)
    async def set_log_channel(self, ctx, channel: int=None):
        if channel:
            # Set either the provided channel id.
            channel = ctx.guild.get_channel(channel)
            if not channel:
                await ctx.reply("invalid channel id.")
                return
        else:
            # Or set the channel the command is invoked in.
            channel = ctx.channel

        self._get_guild_banner(ctx.guild).set_log_channel(channel)
        logger.info("log channel set to {0} ({1}) in {2} ({3}), done by {4} ({5})".format(
            ctx.guild.name, ctx.guild.id,
            channel.name, channel.id,
            "{0}#{1}".format(ctx.author.name, ctx.author.discriminator), ctx.author.id
        ))
        await ctx.reply("logs will be written to {0}".format(channel.mention))

    # Matching #

    @invoke.group(name="pattern", invoke_without_command=True)
    async def pattern(self, ctx):
        # TODO; help.
        await ctx.reply("match help is here!")

    @pattern.command(name="add", ignore_extra=False)
    async def add_pattern(self, ctx, regex_str: str, enabled: bool=False):
        try:
            pattern = re.compile(regex_str)
        except Exception as err:
            msg = "error; failed to compile the provided regex:\n{0}".format(str(err))
            logger.exception("failed to compile regex '{0}'".format(regex_str))
            raise EntryBannerError(msg)

        matcher = MemberMatcher(pattern, False, MemberMatcher.create_new_metadata(ctx))
        id_ = self._get_guild_banner(ctx.guild).add_matcher(matcher)
        logger.info("added pattern {0} ({1}) in {2} ({3}), done by {4} ({5})".format(
            pattern, id_,
            ctx.guild.name, ctx.guild.id,
            "{0}#{1}".format(ctx.author.name, ctx.author.discriminator), ctx.author.id
        ))
        await ctx.reply("new pattern has been added with id {0}".format(id_))

    @pattern.command(name="remove", ignore_extra=False)
    async def remove_pattern(self, ctx, id_: int):
        gb = self._get_guild_banner(ctx.guild)
        matcher = gb.pop_matcher(id_)
        logger.info("removed pattern {0} ({1}) in {2} ({3}), done by {4} ({5})".format(
            matcher, id_,
            ctx.guild.name, ctx.guild.id,
            "{0}#{1}".format(ctx.author.name, ctx.author.discriminator), ctx.author.id
        ))
        await ctx.reply("removed pattern '{0}'".format(str(matcher)))

    @pattern.command(name="list", ignore_extra=False)
    async def list_patterns(self, ctx):
        gb = self._get_guild_banner(ctx.guild)
        await ctx.reply(gb.get_pretty_pattern_list())

    @pattern.command(name="enable", ignore_extra=False)
    async def enable_pattern(self, ctx, id_: int):
        self._get_guild_banner(ctx.guild).enable_matcher()
        logger.info("enabled pattern {0} in {1} ({2}), done by {3} ({4})".format(
            id_, ctx.guild.name, ctx.guild.id,
            "{0}#{1}".format(ctx.author.name, ctx.author.discriminator), ctx.author.id
        ))
        await ctx.reply("enabled.")

    @pattern.command(name="disable", ignore_extra=False)
    async def disable_pattern(self, ctx, id_: int):
        self._get_guild_banner(ctx.guild).disable_matcher()
        logger.info("disabled pattern {0} in {1} ({2}), done by {3} ({4})".format(
            id_, ctx.guild.name, ctx.guild.id,
            "{0}#{1}".format(ctx.author.name, ctx.author.discriminator), ctx.author.id
        ))
        await ctx.reply("disabled.")
