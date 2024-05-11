
import inspect
import traceback
import typing

from bot.cogs.lib import utils
from bot.cogs.lib.models.category_settings import GuildCategorySettings
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.mongodb.database import Database


class CategorySettingsDatabase(Database):
    def __init__(self):
        super().__init__()
        pass

    def set_guild_category_settings(
        self,
        guildId: int,
        categoryId: int,
        channelLimit: int,
        channelLocked: bool,
        bitrate: int,
        defaultRole: typing.Union[int,str],
        autoGame: typing.Optional[bool] = None,
        allowSoundboard: typing.Optional[bool] = None,
        autoName: typing.Optional[bool] = None,
    ):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            payload = {
                "guild_id": str(guildId),
                "voice_category_id": str(categoryId),
                "channel_limit": channelLimit,
                "channel_locked": channelLocked,
                "bitrate": bitrate,
                "default_role": defaultRole,
                "auto_game": autoGame,
                "allow_soundboard": allowSoundboard,
                "auto_name": autoName,
                "timestamp": utils.get_timestamp()
            }
            self.connection.category_settings.update_one(
                {"guild_id": str(guildId), "voice_category_id": str(categoryId)},
                { "$set": payload },
                upsert=True
            )
            return True
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to set guild category settings: {ex}",
                stackTrace=traceback.format_exc()
            )
            return False

    def get_guild_category_settings(self, guildId: int, categoryId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            row = self.connection.category_settings.find_one(
                { "guild_id": str(guildId), "voice_category_id": str(categoryId)}
            )
            if row:
                result = GuildCategorySettings(
                    guildId=guildId,
                    categoryId=categoryId,
                    channelLimit=row['channel_limit'],
                    channelLocked=row['channel_locked'],
                    bitrate=row['bitrate'],
                    defaultRole=row['default_role'],
                    autoGame=row['auto_game'],
                    allowSoundboard=row['allow_soundboard'],
                    autoName=row['auto_name'],
                )
                return result
            return None
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"Failed to get guild category settings: {ex}",
                stackTrace=traceback.format_exc()
            )
