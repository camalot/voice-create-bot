import inspect
import traceback
import os
import typing

from bot.cogs.lib import utils
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.mongodb.database import Database
from pymongo import MongoClient

class ChannelsDatabase(Database):
    def __init__(self) -> None:
        super().__init__()
        _method = inspect.stack()[0][3]
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__

        self.log(
            guildId=0,
            level=LogLevel.DEBUG,
            method=f"{self._module}.{self._class}.{_method}",
            message=f"Initialized {self._class}",
        )
        pass

    def get_tracked_channel_owner(self, guildId: int, voiceChannelId: int) -> typing.Optional[int]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            owner = self.connection.voice_channels.find_one(
                {"guild_id": str(guildId), "voice_channel_id": str(voiceChannelId)}, {"user_id": 1}
            )
            if owner:
                return int(owner['user_id'])
            return None
        except Exception as ex:
            self.log(
                guildId,
                LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )
            return None

    def update_tracked_channel_owner(
            self,
            guildId: int,
            voiceChannelId: typing.Optional[int],
            ownerId: typing.Optional[int],
            newOwnerId: typing.Optional[int],
        ) -> None:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            self.connection.voice_channels.update_one(
                {"guild_id": str(guildId), "voice_channel_id": str(voiceChannelId), "user_id": str(ownerId)},
                {"$set": {"user_id": str(newOwnerId)}},
            )
            self.connection.text_channels.update_one(
                {"guild_id": str(guildId), "voice_channel_id": str(voiceChannelId), "user_id": str(ownerId)},
                {"$set": {"user_id": str(newOwnerId)}},
            )
        except Exception as ex:
            self.log(
                guildId,
                LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )
            return None

    def get_channel_owner_id(self, guildId: int, channelId: typing.Optional[int]):
        _method = inspect.stack()[0][3]
        try:
            if channelId is None:
                return None
            if self.connection is None:
                self.open()
            item = self.connection.voice_channels.find_one({"guild_id": str(guildId), "voice_channel_id": channelId}, {"user_id": 1})
            if item:
                return int(item['user_id'])
            item = self.connection.text_channels.find_one({"guild_id": str(guildId), "text_channel_id": channelId}, {"user_id": 1})
            if item:
                return int(item['user_id'])
            return None
        except Exception as ex:
            self.log(
                guildId,
                LogLevel.ERROR,
                f"{self._module}.{self._class}.{_method}",
                f"{ex}",
                traceback.format_exc(),
            )
            return None

    def get_text_channel_id(self, guildId: int, voiceChannelId: int) -> typing.Optional[int]:
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            result = self.connection.text_channels.find_one({"guild_id": str(guildId), "voice_channel_id": str(voiceChannelId)})
            if result:
                return int(result['text_channel_id'])
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

    def get_tracked_voice_channel_id_by_owner(self, guildId: int, ownerId: typing.Optional[int]) -> typing.List[int]:
        try:
            if ownerId is None:
                return []
            if self.connection is None:
                self.open()
            items = self.connection.voice_channels.find(
                {"guild_id": str(guildId), "user_id": str(ownerId)}, {"voice_channel_id": 1}
            )
            channel_ids = [int(item['voice_channel_id']) for item in items]
            return channel_ids
        except Exception as ex:
            raise ex

    def get_tracked_voice_channel_ids(self, guildId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            cursor = self.connection.voice_channels.find({"guild_id": str(guildId)}, { "voice_channel_id": 1 })
            items = [int(i['voice_channel_id']) for i in cursor]
            return items
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_new_voice_channel(self, guildId: int, ownerId: int, voiceChannelId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            # c.execute("INSERT INTO voiceChannel VALUES (?, ?, ?)", (guildId, ownerId, voiceChannelId,))
            payload = {
                "guild_id": str(guildId),
                "user_id": str(ownerId),
                "voice_channel_id": str(voiceChannelId),
            }
            self.connection.voice_channels.insert_one(payload)
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

    def add_tracked_text_channel(self, guildId: int, ownerId: int, voiceChannelId: int, textChannelId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            payload = {
                "guild_id": str(guildId),
                "user_id": str(ownerId),
                "text_channel_id": str(textChannelId),
                "voice_channel_id": str(voiceChannelId),
            }
            self.connection.text_channels.insert_one(payload)
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

    def delete_tracked_text_channel(self, guildId, voiceChannelId, textChannelId):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            tracked = self.connection.text_channels.find_one({ "guild_id": guildId, "voice_channel_id": voiceChannelId, "text_channel_id": textChannelId })
            if tracked:
                payload = {
                    "guild_id": str(guildId),
                    "user_id": str(tracked['user_id']),
                    "text_channel_id": str(tracked['text_channel_id']),
                    "voice_channel_id": str(tracked['voice_channel_id']),
                    "timestamp": utils.get_timestamp(),
                }
                self.connection.tracked_channels_history.insert_one(payload)
            self.connection.text_channels.delete_one({
                "guild_id": str(guildId),
                "voice_channel_id": str(voiceChannelId),
                "text_channel_id": str(textChannelId),
            })
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )

    def track_new_channel_set(self, guildId: int, ownerId: int, voiceChannelId: int, textChannelId: int):
        _method = inspect.stack()[0][3]
        try:
            if self.connection is None:
                self.open()
            result = self.track_new_voice_channel(guildId=guildId, ownerId=ownerId, voiceChannelId=voiceChannelId)
            if result:
                result = self.add_tracked_text_channel(
                    guildId=guildId, ownerId=ownerId, voiceChannelId=voiceChannelId, textChannelId=textChannelId
                )
            return result
        except Exception as ex:
            self.log(
                guildId=guildId,
                level=LogLevel.ERROR,
                method=f"{self._module}.{self._class}.{_method}",
                message=f"{ex}",
                stackTrace=traceback.format_exc(),
            )
            return False

    def clean_tracked_channels(self, guildId: int, voiceChannelId: int, textChannelId: typing.Optional[int]):
        try:
            if self.connection is None:
                self.open()
            tracked_voice = self.connection.voice_channels.find_one(
                {"guild_id": str(guildId), "voice_channel_id": str(voiceChannelId)}
            )
            if tracked_voice:
                tracked_text = self.connection.text_channels.find_one(
                    {
                        "guild_id": str(guildId),
                        "voice_channel_id": str(voiceChannelId),
                        "text_channel_id": str(textChannelId) if textChannelId else None,
                    }
                )
                text_channel_id = None
                if tracked_text:
                    text_channel_id = str(tracked_text['text_channel_id'])
                payload = {
                    "guild_id": str(guildId),
                    "user_id": str(tracked_voice['user_id']),
                    "text_channel_id": text_channel_id,
                    "voice_channel_id": str(tracked_voice['voice_channel_id']),
                    "timestamp": utils.get_timestamp(),
                }
                self.connection.tracked_channels_history.insert_one(payload)
            self.connection.voice_channels.delete_one(
                {"guild_id": str(guildId), "voice_channel_id": str(voiceChannelId)}
            )
            self.connection.text_channels.delete_one({"guild_id": str(guildId), "text_channel_id": str(textChannelId)})
        except Exception as ex:
            print(ex)
            traceback.print_exc()
