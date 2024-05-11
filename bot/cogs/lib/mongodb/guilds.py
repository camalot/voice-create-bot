import datetime
import inspect
import os
import traceback
import typing

import discord
from bot.cogs.lib import utils
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.mongodb.database import Database
from bot.cogs.lib.models.guild_create_channels import GuildCreateChannels
from bot.cogs.lib.models.guild_category_create_channel import GuildCategoryCreateChannel



class GuildsDatabase(Database):

    def __init__(self):
        super().__init__()
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

    def get_all_guilds(self) -> typing.List[dict]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            cursor = self.connection.guilds.find()
            result = []
            for c in cursor:
                result.append(c)
            return result
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return []

    def get_use_stage_on_create(self, guildId: int, channelId: int, categoryId: int) -> bool:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            result = self.connection.create_channels.find_one(
                {"guild_id": str(guildId), "voice_category_id": str(categoryId), "voice_channel_id": str(channelId)},
                {"use_stage": 1}
            )
            if result:
                return result['use_stage']
            return False
        except Exception as ex:
            self.log(
                guildId,
                LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )
            return False

    def get_guild_create_channels(self, guildId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            # c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildId,))
            cursor = self.connection.create_channels.find({"guild_id": str(guildId)}, { "voice_channel_id": 1 })
            result = []
            for c in cursor:
                result.append(int(c['voice_channel_id']))
            return result
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def get_guild_create_channel_settings(self, guildId: int) -> typing.Optional[GuildCreateChannels]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            rows = self.connection.create_channels.find({"guild_id": str(guildId)})
            if rows:
                result = GuildCreateChannels(guildId=guildId)
                for r in rows:
                    result.channels.append(
                        GuildCategoryCreateChannel(
                            ownerId=(r['owner_id']),
                            categoryId=int(r['voice_category_id']),
                            channelId=int(r['voice_channel_id']),
                            useStage=r['use_stage'],
                        ))
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

    def delete_guild_create_channel(self, guildId: int, channelId: int, categoryId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            # c.execute("DELETE FROM guild WHERE guildID = ? AND voiceChannelID = ? AND voiceCategoryID = ?", (guildId, channelId, categoryId,))
            self.connection.create_channels.delete_many(
                {"guild_id": str(guildId), "voice_channel_id": str(channelId), "voice_category_id": str(categoryId)}
            )
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_guild(self, guild: discord.Guild):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            date = datetime.datetime.utcnow()
            timestamp = utils.to_timestamp(date)

            payload = {
                "guild_id": str(guild.id),
                "name": guild.name,
                "owner_id": str(guild.owner_id),
                "created_at": utils.to_timestamp(guild.created_at),
                "vanity_url": guild.vanity_url or None,
                "vanity_url_code": guild.vanity_url_code or None,
                "icon": guild.icon.url if guild.icon else None,
                "timestamp": timestamp
            }

            self.connection.guilds.update_one({ "guild_id": str(guild.id) }, { "$set": payload }, upsert=True)
        except Exception as ex:
            self.log(
                guildId=0,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
