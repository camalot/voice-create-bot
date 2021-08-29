import sqlite3
import traceback
import json
from . import database
from . import settings
class SqliteDatabase(database.Database):
    def __init__(self):
        self.settings = settings.Settings()
        pass
    def open(self):
        self.connection = sqlite3.connect(self.settings.db_path)
        pass
    def close(self):
        try:
            if self.connection:
                self.connection.commit()
                self.connection.close()
        except Exception as ex:
            print(ex)
            traceback.print_exc(ex)
        finally:
            self.connection = None
        pass
    def get_tracked_voice_channel_ids(self, guildId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT voiceID FROM voiceChannel WHERE guildID = ?", (guildId,))
            items = c.fetchall()
            return items
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_guild_create_channels(self, guildId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT voiceChannelID FROM guild WHERE guildID = ?", (guildId,))
            channel_ids = [item for clist in c.fetchall() for item in clist]
            return channel_ids
        except Exception as ex:
            print(ex)
            traceback.print_exc(ex)

    def get_text_channel_id(self, guildId, voiceChannelId):
        # SELECT channelID FROM textChannel WHERE guildID = ? and voiceId = ?
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT channelID FROM textChannel WHERE guildID = ? and voiceId = ?", (guildId, voiceChannelId))
            item = c.fetchone()
            if item:
                return item[0]
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_voice_channel_id_from_text_channel(self, guildId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT voiceID FROM textChannel WHERE guildID = ? and channelID = ?", (guildId, textChannelId))
            item = c.fetchone()
            if item:
                return item[0]
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def clean_tracked_channels(self, guildId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute('DELETE FROM voiceChannel WHERE guildID = ? and voiceId = ?', (guildId, voiceChannelId,))
            c.execute('DELETE FROM textChannel WHERE guildID = ? and channelID = ?', (guildId, textChannelId,))
            self.connection.commit()
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        pass

    def get_channel_owner_id(self, guildId, channelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT userID FROM voiceChannel WHERE guildID = ? AND voiceID = ?", (guildId, channelId,))
            item = c.fetchone()
            if item:
                return int(item[0])
            c.execute("SELECT userID FROM textChannel WHERE guildID = ? AND channelID = ?", (guildId, channelId,))
            item = c.fetchone()
            if item:
                return int(item[0])

            return None

        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_user_settings(self, guildId, userId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT channelName, channelLimit, bitrate, defaultRole FROM userSettings WHERE userID = ? AND guildID = ?", (userId, guildId,))
            row = c.fetchone()
            if row:
                result = settings.UserSettings(guildId=guildId, userId=userId, channelName=row[0], channelLimit=int(row[1]), bitrate=int(row[2]), defaultRole=row[3])
                return result
            print("NO USER SETTINGS FOUND")
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()

    def get_guild_settings(self, guildId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT ownerID, voiceChannelID, voiceCategoryID, useStage FROM guild WHERE guildID = ?", (guildId,))
            rows = c.fetchall()
            if rows:
                result = settings.GuildSettings(guildId=guildId)
                for r in rows:
                    result.channels.append(settings.GuildCategoryChannel(ownerId=int(r[0]), categoryId=r[2], channelId=r[1], useStage=int(r[3])))
                return result
            print("NO GUILD SETTINGS FOUND")
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
    def get_use_stage_on_create(self, guildId, channelId, categoryId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT useStage FROM guild WHERE guildID = ? AND voiceCategoryID = ? AND voiceChannelID = ?", (guildId, categoryId, channelId))
            create_channel = c.fetchone()
            if create_channel:
                return create_channel[0]
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc(ex)

    def get_guild_category_settings(self, guildId, categoryId):
        try:
            print(f"category: {categoryId}")
            print(f"guild: {guildId}")
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT channelLimit, channelLocked, bitrate, defaultRole FROM guildCategorySettings WHERE guildID = ? and voiceCategoryID = ?", (guildId, categoryId,))
            row = c.fetchone()
            if row:
                result = settings.GuildCategorySettings(guildId=guildId, categoryId=categoryId, channelLimit=int(row[0]), channelLocked=int(row[1]), bitrate=row[2], defaultRole=row[3])
                return result
            print("NO GUILD CATEGORY SETTINGS FOUND")
            return None
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        pass

    def update_user_channel_name(self, guildId, userId, channelName):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("UPDATE userSettings SET channelName = ? WHERE userID = ? AND guildID = ?", (channelName, userId, guildId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
        pass
    def insert_user_settings(self, guildId, userId, channelName, channelLimit, bitrate, defaultRole):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("INSERT INTO userSettings VALUES (?, ?, ?, ?, ?, ?)", (guildId, userId, channelName, channelLimit, bitrate, defaultRole))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
        pass
    def track_new_channel_set(self, guildId, ownerId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("INSERT INTO voiceChannel VALUES (?, ?, ?)", (guildId, ownerId, voiceChannelId,))
            c.execute("INSERT INTO textChannel VALUES (?, ?, ?, ?)", (guildId, ownerId, textChannelId, voiceChannelId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()

    def add_tracked_text_channel(self, guildId, ownerId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("INSERT INTO textChannel VALUES (?, ?, ?, ?)", (guildId, ownerId, textChannelId, voiceChannelId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
    def delete_tracked_text_channel(self, guildId, voiceChannelId, textChannelId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("DELETE FROM textChannel WHERE guildID = ? AND voiceID = ? AND channelID = ?", (guildId, voiceChannelId, textChannelId,))
        except Exception as ex:
            print(ex)
            traceback.print_exc()
        finally:
            if self.connection:
                self.connection.commit()
    def get_tracked_channels_for_guild(self, guildId):
        try:
            if self.connection is None:
                self.open()
            c = self.connection.cursor()
            c.execute("SELECT voiceID, userID FROM voiceChannel WHERE guildID = ?", (guildId,))
            voiceSets = c.fetchall()
            voice_channels = []
            for item in voiceSets:
                voice_channels.append(settings.TrackedVoiceChannel(guildId=guildId, ownerId=item[1], voiceChannelId=item[0]))
            c.execute("SELECT voiceID, channelID, userID FROM textChannel WHERE guildID = ?", (guildId,))
            textSets = c.fetchall()
            text_channels = []
            for item in textSets:
                text_channels.append(settings.TrackedTextChannel(guildId=guildId, ownerId=item[2], voiceChannelId=item[0], textChannelId=item[1]))
            tracked = settings.TrackedChannels(voiceChannels=voice_channels, textChannels=text_channels)
            return tracked
        except Exception as ex:
            print(ex)
            traceback.print_exc()
