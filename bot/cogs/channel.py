import inspect
import os
import traceback
import typing

import discord
from bot.cogs.lib import channels, logger, messaging, users, utils
from bot.cogs.lib.enums.category_settings_defaults import CategorySettingsDefaults
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.models.category_settings import GuildCategorySettings
from bot.cogs.lib.mongodb.channels import ChannelsDatabase
from bot.cogs.lib.mongodb.tracking import TrackingDatabase
from bot.cogs.lib.mongodb.usersettings import UserSettingsDatabase
from bot.cogs.lib.settings import Settings
from discord.ext import commands


class ChannelCog(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__

        self.channel_db = ChannelsDatabase()
        self.usersettings_db = UserSettingsDatabase()
        self.tracking_db = TrackingDatabase()

        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = Settings()
        self.bot = bot
        self._messaging = messaging.Messaging(bot)
        self._users = users.Users(bot)
        self._channels = channels.Channels(bot)

        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Initialized {self._class}")

    @commands.group(name="channel", aliases=["ch"])
    async def channel(self, ctx):
        if ctx.guild:
            guild_id = ctx.guild.id
        else:
            guild_id = 0
        if guild_id != 0:
            await ctx.message.delete()

    # @channel.group(name="name", aliases=["n"])
    # async def channel_name(self, ctx, *, name: typing.Optional[str] = None):
    #     if ctx.guild:
    #         guild_id = ctx.guild.id
    #     else:
    #         guild_id = 0
    #     if guild_id != 0:
    #         await ctx.message.delete()

    @channel.command()
    async def save(self, ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            if self._users.isInVoiceChannel(ctx):
                voice_channel_id = ctx.author.voice.channel.id
                voice_channel = ctx.author.voice.channel
            else:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, "title_not_in_channel"),
                    f'{ctx.author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                    delete_after=5,
                )
                return

            author_id = ctx.author.id
            category_id = ctx.author.voice.channel.category.id

            owner_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if owner_id != author_id and not self._users.isAdmin(ctx):
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_permission_denied'),
                    f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_permission_denied')}",
                    delete_after=5,
                )
                return

            category_settings = self.settings.db.get_guild_category_settings(guildId=guild_id, categoryId=category_id)
            default_role = self.settings.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            temp_default_role = utils.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role

            if category_settings is None:
                category_settings = GuildCategorySettings(
                    guildId=guild_id,
                    categoryId=category_id,
                    channelLimit=0,
                    channelLocked=False,
                    bitrate=CategorySettingsDefaults.BITRATE,
                    defaultRole=temp_default_role.id if temp_default_role else None,
                )

            is_tracked_channel = (
                len(
                    [
                        c
                        for c in self.channel_db.get_tracked_voice_channel_id_by_owner(
                            guildId=guild_id, ownerId=owner_id
                        )
                        if c == voice_channel_id
                    ]
                )
                >= 1
            )
            if not is_tracked_channel:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_update_channel_name'),
                    f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_voice_not_tracked')}",
                    delete_after=5,
                )
                return

            user_settings = self.usersettings_db.get_user_settings(guildId=guild_id, userId=owner_id)
            if user_settings:
                self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"Insert/Update Channel Name: {user_settings.channel_name} -> {voice_channel.name}")
                self.usersettings_db.update_user_channel_name(
                    guildId=guild_id, userId=owner_id, channelName=voice_channel.name
                )
            else:
                self.usersettings_db.insert_user_settings(
                    guildId=guild_id,
                    userId=owner_id,
                    channelName=voice_channel.name,
                    channelLimit=category_settings.channel_limit,
                    channelLocked=category_settings.channel_locked,
                    bitrate=category_settings.bitrate,
                    defaultRole=temp_default_role.id,
                    autoGame=False,
                    autoName=False,
                    allowSoundboard=False,
                )
            self.tracking_db.track_command(guildId=guild_id, userId=author_id, command="save", args={})
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self._messaging.notify_of_error(ctx)
            return

    @channel.command()
    async def name(self, ctx, *, name: typing.Optional[str] = None):
        await self._name(ctx, name=name, saveSettings=True)

    async def _name(self, ctx, name: typing.Optional[str] = None, saveSettings: bool = True):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        voice_channel_id = None
        voice_channel = None

        try:
            if self._users.isInVoiceChannel(ctx):
                voice_channel_id = ctx.author.voice.channel.id
                voice_channel = ctx.author.voice.channel
            else:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, "title_not_in_channel"),
                    f'{ctx.author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                    delete_after=5,
                )
                return
            if not name or name == "":
                name = utils.get_random_name()
            author_id = ctx.author.id
            category_id = ctx.author.voice.channel.category.id

            owner_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if owner_id != author_id and not self._users.isAdmin(ctx):
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_permission_denied'),
                    f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_permission_denied')}",
                    delete_after=5,
                )
                return
            category_settings = self.settings.db.get_guild_category_settings(guildId=guild_id, categoryId=category_id)
            default_role = self.settings.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            temp_default_role = utils.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role

            if category_settings is None:
                category_settings = GuildCategorySettings(
                    guildId=guild_id,
                    categoryId=category_id,
                    channelLimit=0,
                    channelLocked=False,
                    bitrate=CategorySettingsDefaults.BITRATE,
                    defaultRole=temp_default_role.id if temp_default_role else None,
                )

            is_tracked_channel = (
                len(
                    [
                        c
                        for c in self.channel_db.get_tracked_voice_channel_id_by_owner(
                            guildId=guild_id, ownerId=owner_id
                        )
                        if c == voice_channel_id
                    ]
                )
                >= 1
            )
            if not is_tracked_channel:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_update_channel_name'),
                    f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_voice_not_tracked')}",
                    delete_after=5,
                )
                return

            text_channel_id = self.channel_db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            text_channel = None
            if text_channel_id:
                text_channel = await self._channels.get_or_fetch_channel(int(text_channel_id))
            if text_channel:
                await text_channel.edit(name=name)

            await voice_channel.edit(name=name)
            self.tracking_db.track_command(guildId=guild_id, userId=author_id, command="name", args={"name": name})

            if saveSettings:
                user_settings = self.usersettings_db.get_user_settings(guildId=guild_id, userId=owner_id)
                if user_settings:
                    self.usersettings_db.update_user_channel_name(guildId=guild_id, userId=owner_id, channelName=name)
                else:
                    self.usersettings_db.insert_user_settings(
                        guildId=guild_id,
                        userId=owner_id,
                        channelName=name,
                        channelLimit=category_settings.channel_limit,
                        channelLocked=category_settings.channel_locked,
                        bitrate=category_settings.bitrate,
                        defaultRole=temp_default_role.id,
                        autoGame=False,
                        autoName=True,
                        allowSoundboard=False,
                    )
            await self._messaging.send_embed(
                ctx.channel,
                self.settings.get_string(guild_id, 'title_update_channel_name'),
                f'''{ctx.author.mention}, {
                    utils.str_replace(self.settings.get_string(guild_id, "info_channel_name_change"), channel=name)
                }''',
                delete_after=5,
            )
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self._messaging.notify_of_error(ctx)

    @channel.command(aliases=["rename"])
    async def force_name(self, ctx, *, name: typing.Optional[str] = None):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        channel_id = ctx.author.voice.channel.id
        channel = ctx.author.voice.channel
        try:
            if not self._users.isInVoiceChannel(ctx):
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, "title_not_in_channel"),
                    f'{ctx.author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                    delete_after=5,
                )
                return
            if self._users.isAdmin(ctx):
                if not name or name == "":
                    name = utils.get_random_name()
                category_id = ctx.author.voice.channel.category.id
                guild_category_settings = self.settings.db.get_guild_category_settings(
                    guildId=guild_id, categoryId=category_id
                )
                owner_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=channel_id)
                if not owner_id:
                    await self._messaging.send_embed(
                        ctx.channel,
                        self.settings.get_string(guild_id, 'title_update_channel_name'),
                        f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_voice_not_tracked')}",
                        delete_after=5,
                    )
                    return
                user_settings = self.usersettings_db.get_user_settings(guildId=guild_id, userId=owner_id)
                default_role = self.settings.db.get_default_role(
                    guildId=guild_id, categoryId=category_id, userId=owner_id
                )
                temp_default_role = utils.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role
                # text channel rename is automatically handled by the change event on the voice channel.

                if channel:
                    self.log.debug(guild_id, _method, f"Edit the channel to: {channel.name} -> {name}")
                    await channel.edit(name=name)
                    await self._messaging.send_embed(
                        ctx.channel,
                        self.settings.get_string(guild_id, 'title_update_channel_name'),
                        f'''{ctx.author.mention}, {
                            utils.str_replace(self.settings.get_string(guild_id, "info_channel_name_change"), channel=name)
                        }''',
                        delete_after=5,
                    )

                if user_settings:
                    self.usersettings_db.update_user_channel_name(guildId=guild_id, userId=owner_id, channelName=name)
                else:
                    self.usersettings_db.insert_user_settings(
                        guildId=guild_id,
                        userId=owner_id,
                        channelName=name,
                        # TODO: get the category settings from the database
                        # lockChannel=guild_category_settings.channel_locked,
                        channelLocked=False,
                        channelLimit=guild_category_settings.channel_limit,
                        bitrate=guild_category_settings.bitrate,
                        defaultRole=temp_default_role.id,
                        autoGame=False,
                        # TODO: get the category settings from the database
                        autoName=True,
                        allowSoundboard=False,
                    )
            else:
                self.log.debug(guild_id, _method, f"{ctx.author} tried to run command 'rename'")
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self._messaging.notify_of_error(ctx)

    @channel.command()
    async def mute(self, ctx, userOrRole: typing.Optional[typing.Union[discord.Role, discord.Member]] = None):
        guild_id = ctx.guild.id
        _method = inspect.stack()[1][3]
        try:
            author_id = ctx.author.id
            category_id = None
            category = None
            voice_channel = None
            if self._users.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                category = voice_channel.category
                category_id = category.id
                voice_channel_id = voice_channel.id
            else:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_not_in_channel'),
                    f'{ctx.author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                    delete_after=5,
                )
                return
            owner_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if owner_id is None:
                # no owner found for this channel
                self.log.warn(guild_id, _method, f"No owner found for channel {voice_channel_id}")
                return

            if (not self._users.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_permission_denied'),
                    f'{ctx.author.mention}, {self.settings.get_string(guild_id, "title_permission_denied")}',
                    delete_after=5,
                )
                return

            owner = await self._users.get_or_fetch_user(owner_id)

            default_role = self.settings.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            everyone = utils.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role
            text_channel_id = self.channel_db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            text_channel = None
            if text_channel_id:
                text_channel = await self._channels.get_or_fetch_channel(text_channel_id)

            permRoles = []
            if everyone:
                permRoles = [everyone]
            if userOrRole:
                permRoles.append(userOrRole)
            if text_channel:
                await text_channel.set_permissions(
                    owner,
                    connect=True,
                    read_messages=True,
                    send_messages=True,
                    view_channel=True,
                    read_message_history=True,
                )
                for r in permRoles:
                    await text_channel.set_permissions(r, send_messages=False)

            await voice_channel.set_permissions(owner, speak=True)
            for r in permRoles:
                await voice_channel.set_permissions(r, speak=False)

            await self._messaging.send_embed(
                ctx.channel,
                self.settings.get_string(guild_id, "title_channel_mute"),
                f'{ctx.author.mention}, {self.settings.get_string(guild_id, "info_channel_mute")}',
                delete_after=5,
            )

        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self._messaging.notify_of_error(ctx)

    @channel.command()
    async def unmute(self, ctx, userOrRole: typing.Optional[typing.Union[discord.Role, discord.Member]] = None):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            author_id = ctx.author.id
            category_id = ctx.author.voice.channel.category.id
            voice_channel = None
            if self._users.isInVoiceChannel(ctx):
                voice_channel = ctx.author.voice.channel
                voice_channel_id = voice_channel.id
            else:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_not_in_channel'),
                    f'{ctx.author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                    delete_after=5,
                )
                return
            owner_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel_id)
            if owner_id is None:
                # no owner found for this channel
                self.log.warn(guild_id, _method, f"No owner found for channel {voice_channel_id}")
                return
            if (not self._users.isAdmin(ctx) and author_id != owner_id) or owner_id is None:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_permission_denied'),
                    f'{ctx.author.mention}, {self.settings.get_string(guild_id, "title_permission_denied")}',
                    delete_after=5,
                )
                return

            owner = await self._users.get_or_fetch_user(owner_id)
            default_role = self.settings.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)
            everyone = utils.get_by_name_or_id(ctx.guild.roles, default_role) or ctx.guild.default_role
            text_channel_id = self.channel_db.get_text_channel_id(guildId=guild_id, voiceChannelId=voice_channel_id)
            text_channel = None
            if text_channel_id:
                text_channel = await self._channels.get_or_fetch_channel(text_channel_id)

            permRoles = []
            if everyone:
                permRoles = [everyone]
            if userOrRole:
                permRoles.append(userOrRole)
            if text_channel:
                await text_channel.set_permissions(
                    owner,
                    connect=True,
                    read_messages=True,
                    send_messages=True,
                    view_channel=True,
                    read_message_history=True,
                )
                for r in permRoles:
                    await text_channel.set_permissions(r, send_messages=True)

            await voice_channel.set_permissions(owner, speak=True)
            for r in permRoles:
                await voice_channel.set_permissions(r, speak=True)

            await self._messaging.send_embed(
                ctx.channel,
                self.settings.get_string(guild_id, "title_channel_unmute"),
                f'{ctx.author.mention}, {self.settings.get_string(guild_id, "info_channel_unmute")}',
                delete_after=5,
            )

        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self._messaging.notify_of_error(ctx)

    @channel.command()
    async def owner(self, ctx, member: discord.Member):
        _method = inspect.stack()[1][3]
        guild_id = ctx.author.guild.id
        channel = None
        try:
            if self._users.isInVoiceChannel(ctx):
                channel = ctx.author.voice.channel
            if channel is None:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, "title_set_channel_owner"),
                    f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_not_in_channel')}",
                    delete_after=5,
                )
            else:
                owner_id = self.channel_db.get_tracked_channel_owner(guildId=guild_id, voiceChannelId=channel.id)
                if not owner_id:
                    await self._messaging.send_embed(
                        ctx.channel,
                        self.settings.get_string(guild_id, "title_set_channel_owner"),
                        f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_unmanaged_channel')}",
                        delete_after=5,
                    )
                else:
                    if self._users.isAdmin(ctx) or ctx.author.id == owner_id:
                        self.channel_db.update_tracked_channel_owner(
                            guildId=guild_id, voiceChannelId=channel.id, ownerId=owner_id, newOwnerId=member.id
                        )
                        await self._messaging.send_embed(
                            ctx.channel,
                            self.settings.get_string(guild_id, "title_set_channel_owner"),
                            f"""{ctx.author.mention}, {
                                utils.str_replace(
                                    self.settings.get_string(guild_id, 'info_new_owner'), user=member.mention
                                )
                            }""",
                            delete_after=5,
                        )
                    else:
                        await self._messaging.send_embed(
                            ctx.channel,
                            self.settings.get_string(guild_id, "title_set_channel_owner"),
                            f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_permission_denied')}",
                            delete_after=5,
                        )
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self._messaging.notify_of_error(ctx)

    @channel.command()
    async def game(self, ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            author = ctx.author
            author_id = author.id
            channel_id = None
            selected_title = None
            if self._users.isInVoiceChannel(ctx):
                channel_id = ctx.author.voice.channel.id
            else:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, "title_not_in_channel"),
                    f'{author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                    delete_after=5,
                )
                return
            owner_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=channel_id)
            if owner_id != author_id and not self._users.isAdmin(ctx):
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_permission_denied'),
                    f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_permission_denied')}",
                    delete_after=5,
                )
                return
            owner = await self._users.get_or_fetch_member(ctx.guild, owner_id)
            if owner:
                selected_title = await self.ask_game_for_user(
                    targetChannel=ctx.channel,
                    user=owner,
                    title=self.settings.get_string(guild_id, "title_update_to_game"),
                )
                if selected_title:
                    await self._name(ctx, selected_title, False)
                else:
                    await self._messaging.send_embed(
                        ctx.channel,
                        self.settings.get_string(guild_id, "title_unknown_game"),
                        f'{ctx.author.mention}, {self.settings.get_string(guild_id, "info_unknown_game")}',
                        delete_after=5,
                    )
                    await ctx.message.delete()
            else:
                self.log.debug(guild_id, _method, f"Unable to locate the owner for 'game' call.")
                await ctx.message.delete()
        except discord.errors.NotFound as nf:
            self.log.warn(guild_id, _method, str(nf), traceback.format_exc())
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self._messaging.notify_of_error(ctx)

    @channel.command()
    async def give(self, ctx, newOwner: discord.Member):
        """Give ownership of the channel to another user in the channel"""
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        try:
            if not self._users.isInVoiceChannel(ctx):
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_not_in_channel'),
                    f'{ctx.author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                    delete_after=5,
                )
                return
            channel_id = ctx.author.voice.channel.id
            new_owner_id = newOwner.id
            # update_tracked_channel_owner
            owner_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=channel_id)
            if new_owner_id == owner_id:
                # Can't grant to self
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_update_owner'),
                    f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_channel_owned_you')}",
                    delete_after=5,
                )
            else:
                self.channel_db.update_tracked_channel_owner(
                    guildId=guild_id, voiceChannelId=channel_id, ownerId=owner_id, newOwnerId=new_owner_id
                )
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_update_owner'),
                    f"{ctx.author.mention}, {utils.str_replace(self.settings.get_string(guild_id, 'info_new_owner'), user=newOwner.mention)}",
                    delete_after=5,
                )
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self._messaging.notify_of_error(ctx)

    @channel.command()
    async def claim(self, ctx):
        _method = inspect.stack()[1][3]
        found_as_owner = False
        guild_id = ctx.guild.id
        try:
            if not self._users.isInVoiceChannel(ctx):
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_not_in_channel'),
                    f'{ctx.author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                    delete_after=5,
                )
                return
            channel = ctx.author.voice.channel
            aid = ctx.author.id

            owner_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=channel.id)
            if not owner_id and not self._users.isAdmin(ctx):
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_permission_denied'),
                    f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_permission_denied')}",
                    delete_after=5,
                )
            else:
                for data in channel.members:
                    if data.id == owner_id:
                        owner = await self._users.get_or_fetch_member(ctx.guild, owner_id)
                        mention = owner.mention if owner else f"<@{owner_id}>"
                        await self._messaging.send_embed(
                            ctx.channel,
                            self.settings.get_string(guild_id, 'title_update_owner'),
                            f"""{ctx.author.mention}, {
                                utils.str_replace(
                                    self.settings.get_string(guild_id, 'info_channel_owned'), user=mention
                                )
                            }""",
                            delete_after=5,
                        )
                        found_as_owner = True
                        break
                if not found_as_owner:
                    self.channel_db.update_tracked_channel_owner(
                        guildId=guild_id, voiceChannelId=channel.id, ownerId=owner_id, newOwnerId=aid
                    )
                    await self._messaging.send_embed(
                        ctx.channel,
                        self.settings.get_string(guild_id, 'title_update_owner'),
                        f"{ctx.author.mention}, {utils.str_replace(self.settings.get_string(guild_id, 'info_new_owner'), user=ctx.author.mention)}",
                        delete_after=5,
                    )
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self._messaging.notify_of_error(ctx)

    @channel.command()
    async def lock(self, ctx, role: typing.Optional[discord.Role] = None):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        author = ctx.author
        try:
            owner_id = ctx.author.id
            owner = ctx.author
            category_id = ctx.author.voice.channel.category.id
            current_voice_channel_id = None
            if not self._users.isInVoiceChannel(ctx):
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, "title_not_in_channel"),
                    f'{author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                    delete_after=5,
                )
                return

            current_voice_channel = ctx.author.voice.channel
            current_voice_channel_id = current_voice_channel.id
            isAdmin = self._users.isAdmin(ctx)
            if isAdmin:
                owner_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=current_voice_channel_id)
                owner = await self._users.get_or_fetch_user(owner_id)
            default_role = self.settings.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)

            validRole = len([ x for x in ctx.guild.roles if x.name == default_role or x.id == default_role ]) == 1
            if not validRole:
                default_role = ctx.guild.default_role.id
            owned_channel_ids = self.channel_db.get_tracked_voice_channel_id_by_owner(guildId=guild_id,ownerId=owner_id)
            is_owner = len([ c for c in owned_channel_ids if int(c) == current_voice_channel_id ]) >= 1
            if not is_owner and not isAdmin:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, "title_channel_lock"),
                    f'{author.mention}, {self.settings.get_string(guild_id, "info_not_owner")}',
                    delete_after=5,
                )
            else:
                everyone = utils.get_by_name_or_id(ctx.guild.roles, default_role)
                text_channel_id = self.channel_db.get_text_channel_id(
                    guildId=guild_id, voiceChannelId=current_voice_channel_id
                )
                if text_channel_id:
                    text_channel = await self._channels.get_or_fetch_channel(text_channel_id)
                    if text_channel:
                        await text_channel.set_permissions(
                            owner,
                            connect=True,
                            read_messages=True,
                            send_messages=True,
                            view_channel=True,
                            read_message_history=True,
                        )
                        if everyone:
                            await text_channel.set_permissions(
                                everyone,
                                read_messages=False,
                                send_messages=False,
                                view_channel=True,
                                read_message_history=False,
                            )

                    await current_voice_channel.set_permissions(
                        owner,
                        connect=True,
                        read_messages=True,
                        send_messages=True,
                        view_channel=True,
                        read_message_history=True,
                    )
                    await current_voice_channel.set_permissions(
                        everyone,
                        connect=False,
                        view_channel=True,
                        stream=False,
                    )
                    if role:
                        await current_voice_channel.set_permissions(
                            role,
                            connect=False,
                            read_messages=False,
                            send_messages=False,
                            view_channel=True,
                            stream=False,
                        )
                        if text_channel:
                            await text_channel.set_permissions(role, read_messages=False,send_messages=False, view_channel=True, read_message_history=False)

                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, "title_channel_lock"),
                    f'{author.mention}, Voice chat locked! 🔒',
                    delete_after=5,
                )
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self._messaging.notify_of_error(ctx)

    @channel.command()
    async def unlock(self, ctx, role: typing.Optional[discord.Role] = None):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id
        author = ctx.author
        try:
            owner_id = ctx.author.id
            owner = ctx.author
            category_id = ctx.author.voice.channel.category.id
            current_voice_channel_id = None
            if self._users.isInVoiceChannel(ctx):
                current_voice_channel = ctx.author.voice.channel
                current_voice_channel_id = current_voice_channel.id
            else:
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, "title_not_in_channel"),
                    f'{author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                    delete_after=5,
                )
                return

            if self._users.isAdmin(ctx):
                owner_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=current_voice_channel_id)
                owner = await self._users.get_or_fetch_user(owner_id)
            default_role = self.settings.db.get_default_role(guildId=guild_id, categoryId=category_id, userId=owner_id)

            validRole = len([ x for x in ctx.guild.roles if x.name == default_role or x.id == default_role ]) == 1
            if not validRole:
                default_role = ctx.guild.default_role.id
            owned_channel_ids = self.channel_db.get_tracked_voice_channel_id_by_owner(guildId=guild_id,ownerId=owner_id)
            is_owner = len([ c for c in owned_channel_ids if int(c) == current_voice_channel_id ]) >= 1
            if not is_owner and not self._users.isAdmin(ctx):
                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_permission_denied'),
                    f"{ctx.author.mention}, {self.settings.get_string(guild_id, 'info_permission_denied')}",
                    delete_after=5,
                )
            else:
                # everyone = discord.utils.get(ctx.guild.roles, name=default_role)
                everyone = utils.get_by_name_or_id(ctx.guild.roles, default_role)
                text_channel_id = self.channel_db.get_text_channel_id(guildId=guild_id, voiceChannelId=current_voice_channel_id)
                if text_channel_id:
                    text_channel = await self._channels.get_or_fetch_channel(text_channel_id)

                    if text_channel:
                        await text_channel.set_permissions(owner, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                        if everyone:
                            await text_channel.set_permissions(everyone, read_messages=True,send_messages=True, view_channel=True, read_message_history=True)

                    await current_voice_channel.set_permissions(owner, connect=True, read_messages=True, send_messages=True, view_channel=True, read_message_history=True)
                    await current_voice_channel.set_permissions(everyone, connect=True, view_channel=True, stream=True)
                    if role:
                        await current_voice_channel.set_permissions(role, connect=True, read_messages=True, send_messages=True, view_channel=True, stream=True)
                        if text_channel:
                            await text_channel.set_permissions(role, read_messages=True,send_messages=True, view_channel=True, read_message_history=True)

                await self._messaging.send_embed(
                    ctx.channel,
                    self.settings.get_string(guild_id, 'title_channel_unlock'),
                    f'{author.mention}, {self.settings.get_string(guild_id, "info_unlocked")}',
                    delete_after=5,
                )
        except Exception as ex:
            self.log.error(guild_id, _method, str(ex), traceback.format_exc())
            await self._messaging.notify_of_error(ctx)
        finally:
            self.channel_db.close()
            await ctx.message.delete()

async def setup(bot):
    await bot.add_cog(ChannelCog(bot))
