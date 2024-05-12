import inspect
import os
import traceback
import typing

from bot.cogs.lib import utils
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.models.category_settings import GuildCategorySettings
from bot.cogs.lib.models.default_prefixes import DefaultPrefixes
from bot.cogs.lib.models.guild_settings import GuildSettings
from bot.cogs.lib.mongodb.database_base import DatabaseBase


class SettingsDatabase(DatabaseBase):
    def __init__(self):
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

    def get(self, guildId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            c = self.connection.guild_settings.find_one({"guild_id": str(guildId)})
            if c:
                return GuildSettings(
                    guildId=int(c['guild_id']),
                    prefixes=c['prefixes'],
                    defaultRole=int(c['default_role']),
                    adminRoles=[int(r) for r in c['admin_roles']],
                    language=c['language']
                )
            return None
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return None

    def set(self, settings: GuildSettings):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            payload = {
                "prefixes": settings.prefixes,
                "default_role": settings.default_role,
                "admin_roles": settings.admin_roles,
                "language": settings.language,
                "timestamp": utils.get_timestamp()
            }
            self.connection.guild_settings.update_one({"guild_id": str(settings.guild_id)}, { "$set": payload }, upsert=True)
            return True
        except Exception as ex:
            self.log(
                guildId=int(settings.guild_id) if settings else 0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def get_language(self, guildId: int) -> str:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            gs = self.connection.guild_settings.find_one({"guild_id": str(guildId)})
            if gs:
                return gs['language']
            return "en-us"
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return "en-us"

    def set_language(self, guildId: int, language: str) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            result = self.connection.guild_settings.update_one(
                {"guild_id": str(guildId)},
                {"$set": {"language": language, "timestamp": utils.get_timestamp()}},
            )
            if result.modified_count == 0:
                return False
            return True
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def set_default_role(self, guildId: int, roleId: int, categoryId: typing.Optional[int] = None, userId: typing.Optional[int] = None) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()

            if userId is not None: # check user settings
                user_settings = self.connection.user_settings.find_one({"guild_id": str(guildId), "user_id": str(userId)})
                if user_settings:
                    self.connection.user_settings.update_one(
                        {"guild_id": str(guildId), "user_id": str(userId)},
                        {"$set": {"default_role": str(roleId), "timestamp": utils.get_timestamp()}},
                        upsert=True,
                    )
                    return True

            if categoryId is not None:
                category_settings = self.connection.category_settings.find_one({"guild_id": str(guildId), "category_id": str(categoryId)})
                if category_settings:
                    self.connection.category_settings.update_one(
                        {"guild_id": str(guildId), "category_id": str(categoryId)},
                        {"$set": {"default_role": str(roleId), "timestamp": utils.get_timestamp()}},
                        upsert=True,
                    )
                    return True

            self.connection.guild_settings.update_one(
                {"guild_id": str(guildId)},
                {"$set": {"default_role": str(roleId), "timestamp": utils.get_timestamp()}},
                upsert=True,
            )
            return True
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def get_default_role(self, guildId: int, categoryId: typing.Optional[int], userId: typing.Optional[int]) -> typing.Optional[int]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()

            if userId is not None: # check user settings
                user_settings = self.connection.user_settings.find_one({"guild_id": str(guildId), "user_id": str(userId)})
                if user_settings:
                    if "default_role" in user_settings:
                        return int(user_settings['default_role'])
            if categoryId is not None:
                category_settings = self.connection.category_settings.find_one({"guild_id": str(guildId), "category_id": str(categoryId)})
                if category_settings:
                    if "default_role" in category_settings:
                        return int(category_settings['default_role'])

            guild_settings = self.connection.guild_settings.find_one({"guild_id": str(guildId)})
            if guild_settings:
                if "default_role" in guild_settings:
                    return int(guild_settings['default_role'])

            return None
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return None

    def delete_admin_role(self, guildId: int, roleId: int) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()

            result = self.connection.guild_settings.update_one(
                {"guild_id": str(guildId)},
                {"$pull": {"admin_roles": str(roleId)}, "$set": {"timestamp": utils.get_timestamp()}},
            )

            if result.modified_count == 0:
                return False

            return True
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def add_admin_role(self, guildId: int, roleId: int) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()

            result = self.connection.guild_settings.update_one(
                {"guild_id": str(guildId)},
                {"$addToSet": {"admin_roles": str(roleId)}, "$set": {"timestamp": utils.get_timestamp()}},
            )

            if result.modified_count == 0:
                return False

            return True
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def set_prefixes(self, guildId: int, prefixes: typing.List[str], append: bool = False):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            gs = self.get(guildId=guildId)
            if not gs:
                return False


            if append:
                prefixes = gs.prefixes + prefixes

            padded_prefixes = []
            for prefix in prefixes:
                padded_prefixes.append(f"{prefix.strip().lower()} ")

            payload = {
                "prefixes": padded_prefixes,
                "timestamp": utils.get_timestamp(),
            }
            result = self.connection.guild_settings.update_one({"guild_id": str(guildId)}, { "$set": payload })
            if result.modified_count == 0:
                return False
            return True
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def get_prefixes(self, guildId: int) -> typing.List[str]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            gs = self.get(guildId=guildId)
            if not gs:
                return DefaultPrefixes.VALUE
            return gs.prefixes
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return DefaultPrefixes.VALUE

    def set_setting(self, guildId: int, key: str, value: typing.Any) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            gs = self.get(guildId=guildId)
            if not gs:
                return False
            payload = {
                key: value,
                "timestamp": utils.get_timestamp(),
            }
            self.connection.guild_settings.update_one({"guild_id": str(guildId)}, { "$set": payload })
            return True
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def get_guild_category_settings(self, guildId: int, categoryId: int) -> typing.Optional[GuildCategorySettings]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            row = self.connection.category_settings.find_one({"guild_id": str(guildId), "voice_category_id": str(categoryId)})
            if row:
                result = GuildCategorySettings(
                    guildId=int(guildId),
                    categoryId=int(categoryId),
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
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return None

    def update_guild_create_channel_settings(
        self, guildId: int, createChannelId: int, categoryId: int, ownerId: int, useStage: bool
    ) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            self.connection.create_channels.find_one_and_update(
                {"guild_id": str(guildId), "voice_channel_id": str(createChannelId)},
                {
                    "$set": {
                        "owner_id": str(ownerId),
                        "voice_category_id": str(categoryId),
                        "useStage": useStage,
                    }
                }
            )
            return True
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False
