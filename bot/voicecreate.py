import discord
from discord import app_commands
from discord.ext import commands
import inspect
from random import randint
import traceback
import sys
import os
import typing
import discordhealthcheck

from bot.cogs.lib import logger, settings
from bot.cogs.lib.mongodb.guilds import GuildsDatabase
from bot.cogs.lib.models.default_prefixes import DefaultPrefixes
from bot.cogs.lib.enums import loglevel


class VoiceCreate(commands.Bot):
    def __init__(self, *, intents: discord.Intents):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        super().__init__(command_prefix=self.get_prefix, intents=intents, case_insensitive=True)

        self.remove_command("help")
        self.guilds_db = GuildsDatabase()

        # A CommandTree is a special type that holds all the application command
        # state required to make it work. This is a separate class because it
        # allows all the extra state to be opt-in.
        # Whenever you want to work with application commands, your tree is used
        # to store and work with them.
        # Note: When using commands.Bot instead of discord.Client, the bot will
        # maintain its own tree instead.
        # self.tree = app_commands.CommandTree(self)

        self.settings = settings.Settings()
        log_level = loglevel.LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = loglevel.LogLevel.DEBUG
        self.log = logger.Log(minimumLogLevel=log_level)

        self.log.info(0, f"{self._module}.{self._class}.{_method}", f"APP VERSION: {self.settings.APP_VERSION}")
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Logger initialized with level {log_level.name}")
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Initialized {self._class}")

    async def setup_hook(self) -> None:
        _method = inspect.stack()[0][3]
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Setup hook called")
        # cogs that dont start with an underscore are loaded
        cogs = [
            f"bot.cogs.{os.path.splitext(f)[0]}"
            for f in os.listdir("bot/cogs")
            if f.endswith(".py") and not f.startswith("_")
        ]

        for extension in cogs:
            try:
                await self.load_extension(extension)
            except Exception as e:
                print(f"Failed to load extension {extension}.", file=sys.stderr)
                traceback.print_exc()

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Setting up bot")

        # get all guilds from the db
        guilds = [int(g['guild_id']) for g in self.guilds_db.get_all_guilds()]
        for gid in guilds:
            try:
                guild = discord.Object(id=gid)
                self.log.debug(gid, f"{self._module}.{self._class}.{_method}", f"Clearing app commands for guild {gid}")
                self.tree.clear_commands(guild=guild)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                self.log.debug(gid, f"{self._module}.{self._class}.{_method}", f"Synced app commands for guild {gid}")
            except discord.errors.Forbidden as fe:
                self.log.debug(gid, f"{self._module}.{self._class}.{_method}", f"Failed to sync app commands for guild {gid}: {fe}")

        self.log.debug(0, f"{self._module}.{self._class}.{_method}", "Starting Healthcheck Server")
        self.healthcheck_server = await discordhealthcheck.start(self)

        # _method = inspect.stack()[0][3]
        # self.log.debug(0, f"{self._module}.{_method}", "Setup hook called")
        # # cogs that dont start with an underscore are loaded
        # cogs = [
        #     f"bot.cogs.{os.path.splitext(f)[0]}"
        #     for f in os.listdir("bot/cogs")
        #     if f.endswith(".py") and not f.startswith("_")
        # ]

        # for extension in cogs:
        #     try:
        #         await self.load_extension(extension)
        #     except Exception as e:
        #         print(f"Failed to load extension {extension}.", file=sys.stderr)
        #         traceback.print_exc()

        # self.log.debug(0, f"{self._module}.{_method}", "Setting up bot")
        # self.log.debug(0, f"{self._module}.{_method}", "Starting Healthcheck Server")
        # self.healthcheck_server = await discordhealthcheck.start(self)

    def initDB(self):
        pass

    async def get_prefix(self, message) -> typing.List[str]:
        _method: str = inspect.stack()[0][3]
        # default prefixes
        default_prefixes: typing.List[str] = DefaultPrefixes.VALUE
        # sets the prefixes, you can keep it as an array of only 1 item if you need only one prefix
        prefixes: typing.List[str] =  default_prefixes
        try:
            if message:
                # get the prefix for the guild.
                if message.guild:
                    guild_id = message.guild.id
                    # get settings from db
                    prefixes = self.settings.db.get_prefixes(guild_id)
                    if prefixes is None:
                        self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"Prefixes not found for guild {guild_id}. Using default prefixes")
                        prefixes = default_prefixes

                    self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"Getting prefixes for guild {guild_id}: {prefixes}")
                # Allow users to @mention the bot instead of using a prefix when using a command. Also optional
                # Do `return prefixes` if you don't want to allow mentions instead of prefix.
                return commands.when_mentioned_or(*prefixes)(self, message)
            else:
                self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Message is None. Using default prefixes")
                return commands.when_mentioned_or(*prefixes)(self, message)
        except Exception as e:
            self.log.error(0, f"{self._module}.{self._class}.{_method}", f"Failed to get prefixes: {e}", traceback.format_exc())
            return commands.when_mentioned_or(*prefixes)(self, message)

        # self.db.open()
        # # get the prefix for the guild.
        # prefixes = ['.']    # sets the prefixes, you can keep it as an array of only 1 item if you need only one prefix
        # if message.guild:
        #     guild_settings = self.db.get_guild_settings(message.guild.id)
        #     if guild_settings:
        #         prefixes = guild_settings.prefix or "."
        # elif not message.guild:
        #     prefixes = ['.']   # Only allow '.' as a prefix when in DMs, this is optional

        # # Allow users to @mention the bot instead of using a prefix when using a command. Also optional
        # # Do `return prefixes` if you don't want to allow mentions instead of prefix.
        # return commands.when_mentioned_or(*prefixes)(self, message)
