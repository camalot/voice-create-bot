import discord
from discord.ext import commands
import asyncio
import json
import traceback
import sys
import os
import glob
import typing
import math
import datetime

import inspect

from bot.cogs.lib.settings import Settings
from .lib import logger
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib import utils
from bot.cogs.lib.mongodb.guilds import GuildsDatabase

class GuildTrackCog(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.bot = bot
        self.settings = Settings()
        self.guild_db = GuildsDatabase()
        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Initialized {self._class}")

    @commands.Cog.listener()
    async def on_guild_available(self, guild) -> None:
        _method = inspect.stack()[0][3]
        try:
            if guild is None:
                return

            self.log.debug(guild.id, f"{self._module}.{self._class}.{_method}", f"Guild ({guild.id}) is available")
            self.guild_db.track_guild(guild=guild)
        except Exception as e:
            self.log.error(guild.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_guild_update(self, before, after) -> None:
        _method = inspect.stack()[0][3]
        try:
            if after is None:
                return

            self.log.debug(before.id, f"{self._module}.{self._class}.{_method}", f"Guild ({before.id}) is updated")
            self.guild_db.track_guild(guild=after)
        except Exception as e:
            self.log.error(before.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

async def setup(bot):
    await bot.add_cog(GuildTrackCog(bot))
