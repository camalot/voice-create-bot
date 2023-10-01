import traceback
import os
import inspect

from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.logger import Log
from bot.cogs.lib.mongodb.users import UsersMongoDatabase
from bot.cogs.lib.settings import Settings
from discord.ext import commands
class UserTrackingCog(commands.Cog):
    def __init__(self, bot) -> None:
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.bot = bot
        self.settings = Settings()
        self.db = UsersMongoDatabase()
        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG

        self.log = Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Initialized {self._class}")

    # on events, get the user id and username and store it in the database
    @commands.Cog.listener()
    async def on_member_join(self, member) -> None:
        _method = inspect.stack()[0][3]
        try:
            if member is None or member.guild is None:
                return
            self.log.debug(member.guild.id, f"{self._module}.{self._class}.{_method}", f"User {member.id} joined guild {member.guild.id}")
            self.db.track_user(member)
        except Exception as e:
            self.log.error(member.guild.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_member_update(self, before, after) -> None:
        _method = inspect.stack()[0][3]
        try:
            if after is None or after.guild is None:
                return
            self.log.debug(after.guild.id, f"{self._module}.{self._class}.{_method}", f"User {after.id} updated in guild {after.guild.id}")
            self.db.track_user(after)
        except Exception as e:
            self.log.error(after.guild.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        _method = inspect.stack()[0][3]
        try:
            if member is None or member.guild is None:
                return

            # ignore if both before and after are None
            if before.channel is None and after.channel is None:
                return

            self.log.debug(member.guild.id, f"{self._module}.{self._class}.{_method}", f"User {member.id} updated in guild {member.guild.id}")
            self.db.track_user(member)
        except Exception as e:
            self.log.error(member.guild.id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())


async def setup(bot):
    await bot.add_cog(UserTrackingCog(bot))
