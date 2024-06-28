import inspect
import json
import os
import traceback

import discord
from bot.cogs.lib import channels, logger, messaging, settings, users, utils
from bot.cogs.lib.enums.category_settings_defaults import CategorySettingsDefaults
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.enums.system_actions import SystemActions
from bot.cogs.lib.models.embedfield import EmbedField
from bot.cogs.lib.mongodb.channels import ChannelsDatabase
from bot.cogs.lib.mongodb.guilds import GuildsDatabase
from bot.cogs.lib.mongodb.tracking import TrackingDatabase
from bot.cogs.lib.mongodb.users import UsersDatabase
from bot.cogs.lib.mongodb.usersettings import UserSettingsDatabase
from discord.ext import commands


class ChannelCreatorCog(commands.Cog):
    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        self._class = self.__class__.__name__

        self.channel_db = ChannelsDatabase()
        self.usersettings_db = UserSettingsDatabase()
        self.users_db = UsersDatabase()
        self.guild_db = GuildsDatabase()
        self.tracking_db = TrackingDatabase()

        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self.settings = settings.Settings()
        self.bot = bot
        self._messaging = messaging.Messaging(bot)
        self._users = users.Users(bot)
        self._channels = channels.Channels(bot)

        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG

        self.log = logger.Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Initialized {self._class}")

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        _method = inspect.stack()[1][3]
        guild_id = 0
        try:
            if before and after:
                if before.id == after.id:
                    # This handles a manual channel rename. it changes the text channel name to match.
                    guild_id = before.guild.id or after.guild.id
                    channel = await self._channels.get_or_fetch_channel(after.id)
                    if channel is None or not channel.category:
                        self.log.debug(guild_id, _method, "Unable to locate category", traceback.format_exc())
                        return
                    category_id = channel.category.id
                    owner_id = self.channel_db.get_channel_owner_id(guild_id, after.id)
                    if owner_id:
                        owner = await self._users.get_or_fetch_member(before.guild, owner_id)
                        if not owner:
                            self.log.warn(
                                guild_id, _method, f"Unable to find owner [user:{owner_id}] for the channel: {channel}"
                            )
                            return

                        if before.name == after.name:
                            # same name. ignore
                            self.log.debug(guild_id, _method, "Channel Names are the same. Nothing to do")
                            return
                        else:
                            default_role = self.settings.db.get_default_role(
                                guildId=guild_id, categoryId=category_id, userId=owner_id
                            )
                            self.log.debug(guild_id, _method, f"default_role: {default_role}")
                            temp_default_role = utils.get_by_name_or_id(after.guild.roles, default_role)
                            self.log.debug(guild_id, _method, f"temp_default_role: {temp_default_role}")
                            user_settings = self.usersettings_db.get_user_settings(guild_id, owner_id)
                            system_default_role = after.guild.default_role

                            self.log.debug(guild_id, _method, f"Channel Type: {after.type}")

                            if after.type == discord.ChannelType.voice:
                                # new channel name
                                text_channel_id = self.channel_db.get_text_channel_id(
                                    guildId=guild_id, voiceChannelId=after.id
                                )
                                text_channel = None
                                if text_channel_id:
                                    text_channel = await self._channels.get_or_fetch_channel(int(text_channel_id))
                                if text_channel:
                                    self.log.debug(guild_id, _method, f"Change Text Channel Name: {after.name}")
                                    new_tc_name = utils.format_text_channel_name(after.name)
                                    if text_channel.name != new_tc_name:
                                        await text_channel.edit(name=new_tc_name)
                                        await self._messaging.send_embed(
                                            text_channel,
                                            self.settings.get_string(guild_id, 'title_update_channel_name'),
                                            f'''{owner.mention}, {
                                                utils.str_replace(
                                                    self.settings.get_string(guild_id, "info_channel_name_change"),
                                                    channel=text_channel.name,
                                                )
                                            }''',
                                            delete_after=5,
                                        )
                                        self.log.debug(guild_id, _method, f"Text Channel Name Changed: {new_tc_name}")
                                else:
                                    self.log.warn(
                                        guildId=guild_id,
                                        method=_method,
                                        message=f"Unable to locate text channel for voice channel: {after.name}",
                                    )

                                self.channel_db.track_channel_name(
                                    guildId=guild_id,
                                    channelId=after.id,
                                    ownerId=owner_id,
                                    name=after.name,
                                )

                            if after.type == discord.ChannelType.text:
                                # this might trigger a channel name change for the voice channel
                                # causing the voice channel to be renamed to the text channel name
                                # with the "format" of the text channel like spaces will be replaced with dashes
                                voiceChannel = None
                                voice_channel_id = self.channel_db.get_voice_channel_id_from_text_channel(
                                    guildId=guild_id, textChannelId=after.id
                                )
                                if voice_channel_id:
                                    voiceChannel = await self._channels.get_or_fetch_channel(voice_channel_id)
                                if voiceChannel:
                                    self.log.debug(guild_id, _method, f"Change Voice Channel Name: {after.name}")
                                    new_vc_name = utils.format_voice_channel_name(after.name)
                                    if voiceChannel.name != new_vc_name:
                                        await voiceChannel.edit(name=new_vc_name)
                                        await self._messaging.send_embed(
                                            after,
                                            self.settings.get_string(guild_id, 'title_update_channel_name'),
                                            f'{owner.mention}, {utils.str_replace(self.settings.get_string(guild_id, "info_channel_name_change"), channel=after.name)}',
                                            delete_after=5,
                                        )
                                        self.log.debug(guild_id, _method, f"Voice Channel Name Changed: {new_vc_name}")

                            if user_settings:
                                self.usersettings_db.update_user_channel_name(
                                    guildId=guild_id, userId=owner_id, channelName=after.name
                                )
                            else:
                                self.usersettings_db.insert_user_settings(
                                    guildId=guild_id,
                                    userId=owner_id,
                                    channelName=after.name,
                                    channelLimit=CategorySettingsDefaults.CHANNEL_LIMIT,
                                    channelLocked=CategorySettingsDefaults.LOCKED,
                                    bitrate=CategorySettingsDefaults.BITRATE,
                                    defaultRole=temp_default_role.id if temp_default_role else system_default_role.id,
                                    autoGame=CategorySettingsDefaults.AUTO_GAME,
                                    autoName=CategorySettingsDefaults.AUTO_NAME,
                                    allowSoundboard=CategorySettingsDefaults.ALLOW_SOUNDBOARD,
                                )

        except discord.errors.NotFound as nf:
            self.log.warn(guild_id, _method, str(nf), traceback.format_exc())
        except Exception as e:
            self.log.error(guild_id, _method, str(e), traceback.format_exc())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        _method = inspect.stack()[1][3]
        guild_id = member.guild.id
        self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"On Voice State Update")

        voiceChannels = self.guild_db.get_guild_create_channels(guild_id)
        if voiceChannels is None:
            self.log.debug(
                guild_id,
                f"{self._module}.{self._class}.{_method}",
                f"No voice create channels found for GuildID: {guild_id}",
            )
            pass
        else:
            try:
                self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"Check for user in Create Channel")
                for voiceChannel in voiceChannels:
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Check for user in Create Channel {voiceChannel}",
                    )

                if after.channel is not None and after.channel.id in voiceChannels:
                    # User Joined the CREATE CHANNEL
                    self.log.debug(
                        guild_id, f"{self._module}.{self._class}.{_method}", f"User requested to CREATE CHANNEL"
                    )
                    category_id = after.channel.category_id
                    source_channel = after.channel
                    source_channel_id = after.channel.id

                    userSettings = self.usersettings_db.get_user_settings(
                        guildId=guild_id, userId=member.id
                    )

                    if userSettings is not None:
                        self.log.debug(
                            guild_id, f"{self._module}.{self._class}.{_method}", f"User Settings: {json.dumps(userSettings.__dict__)}"
                        )

                    guildSettings = self.settings.db.get_guild_category_settings(
                        guildId=guild_id, categoryId=category_id
                    )

                    useStage = (
                        self.guild_db.get_use_stage_on_create(
                            guildId=guild_id, channelId=source_channel_id, categoryId=category_id
                        )
                        or 0
                    )

                    # CHANNEL SETTINGS START
                    limit = CategorySettingsDefaults.CHANNEL_LIMIT
                    locked = CategorySettingsDefaults.LOCKED
                    auto_name = CategorySettingsDefaults.AUTO_NAME
                    auto_game = CategorySettingsDefaults.AUTO_GAME
                    allow_soundboard = CategorySettingsDefaults.ALLOW_SOUNDBOARD
                    bitrate = CategorySettingsDefaults.BITRATE
                    name = utils.get_random_name()
                    user_name = name
                    # get game activity from all activities
                    game_activity = None
                    for activity in member.activities:
                        if activity.type == discord.ActivityType.playing:
                            game_activity = activity
                            break

                    is_playing = game_activity is not None

                    default_role_id = self.settings.db.get_default_role(
                        guildId=guild_id, categoryId=category_id, userId=member.id
                    )

                    if default_role_id is None:
                        default_role = member.guild.default_role
                    else:
                        default_role = (
                            utils.get_by_name_or_id(member.guild.roles, default_role_id) or member.guild.default_role
                        )

                    if userSettings is None:
                        self.log.info(
                            guild_id,
                            f"{self._module}.{self._class}.{_method}",
                            f"User Settings not found for {member.id}. Using Guild Settings or Defaults",
                        )
                        if guildSettings is not None:
                            limit = guildSettings.channel_limit
                            locked = guildSettings.channel_locked
                            bitrate = guildSettings.bitrate
                            auto_name = guildSettings.auto_name
                            auto_game = guildSettings.auto_game
                            allow_soundboard = guildSettings.allow_soundboard
                        else:
                            limit = CategorySettingsDefaults.CHANNEL_LIMIT
                            locked = CategorySettingsDefaults.LOCKED
                            bitrate = CategorySettingsDefaults.BITRATE
                            auto_name = CategorySettingsDefaults.AUTO_NAME
                            auto_game = CategorySettingsDefaults.AUTO_GAME
                            allow_soundboard = CategorySettingsDefaults.ALLOW_SOUNDBOARD
                    else:
                        user_name = userSettings.channel_name
                        limit = userSettings.channel_limit
                        bitrate = userSettings.bitrate
                        locked = userSettings.channel_locked
                        auto_name = userSettings.auto_name
                        auto_game = userSettings.auto_game
                        allow_soundboard = userSettings.allow_soundboard

                        self.log.info(
                            guild_id, f"{self._module}.{self._class}.{_method}", f"User Channel Name: {user_name}"
                        )

                        if not auto_name:
                            name = user_name
                        if auto_game and is_playing:
                            name = game_activity.name

                    # CHANNEL SETTINGS END

                    mid = member.id
                    category = discord.utils.get(member.guild.categories, id=category_id)
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Creating channel {name} in {category} with bitrate {bitrate}kbps",
                    )
                    is_community = member.guild.features.count("COMMUNITY") > 0
                    if useStage and is_community:
                        self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"Creating Stage Channel")
                        stage_topic = utils.get_random_name(noun_count=1, adjective_count=2)
                        voiceChannel = await member.guild.create_stage_channel(
                            name,
                            topic=stage_topic,
                            category=category,
                            reason="Create Stage Channel Request by {member}",
                            position=0,
                        )
                        self.tracking_db.track_system_action(
                            guildId=guild_id, userId=member.id, action=SystemActions.CREATE_STAGE_CHANNEL
                        )
                    else:
                        self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"Created Voice Channel")
                        voiceChannel = await source_channel.clone(
                            name=name, reason="Create Channel Request by {member}"
                        )
                        self.tracking_db.track_system_action(
                            guildId=guild_id, userId=member.id, action=SystemActions.CREATE_VOICE_CHANNEL
                        )

                    textChannel = await member.guild.create_text_channel(name, category=category, position=0)
                    await textChannel.edit(sync_permissions=True)
                    channelID = voiceChannel.id

                    self.log.debug(
                        guild_id, f"{self._module}.{self._class}.{_method}", f"Moving {member} to {voiceChannel}"
                    )
                    await member.move_to(voiceChannel)

                    self.users_db.track_user_join_channel(member.guild.id, member.id, voiceChannel.id)

                    # if the bot cant do this, dont fail...
                    try:
                        self.log.debug(guild_id, _method, f"Setting permissions on {voiceChannel}")
                        # if use_voice_activity is not True, some cases where people cant speak, unless they use P2T
                        await voiceChannel.set_permissions(
                            member,
                            speak=True,
                            priority_speaker=True,
                            connect=True,
                            read_messages=True,
                            send_messages=True,
                            view_channel=True,
                            use_voice_activation=True,
                            stream=True,
                            move_members=True,
                            use_soundboard=allow_soundboard,
                        )
                        await textChannel.set_permissions(
                            member,
                            read_messages=True,
                            send_messages=True,
                            view_channel=True,
                            read_message_history=True,
                            use_soundboard=allow_soundboard,
                        )
                    except Exception as ex:
                        self.log.error(
                            guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc()
                        )
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Set user limit to {limit} on {voiceChannel}",
                    )
                    await voiceChannel.edit(name=name, user_limit=limit, bitrate=(bitrate * 1000), position=0)

                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Track voiceChannel userID: {mid} channelID: {channelID}",
                    )
                    self.log.debug(
                        guild_id,
                        f"{self._module}.{self._class}.{_method}",
                        f"Track Voice and Text Channels {name} in {category}",
                    )

                    self.channel_db.track_new_channel_set(
                        guildId=guild_id,
                        ownerId=mid,
                        voiceChannelId=channelID,
                        textChannelId=textChannel.id,
                        channelName=name,
                    )

                    try:
                        if default_role:
                            self.log.debug(
                                guild_id,
                                f"{self._module}.{self._class}.{_method}",
                                f"Check if bot can set channel for {default_role.name} {voiceChannel}",
                            )
                            await textChannel.set_permissions(
                                default_role,
                                read_messages=(not locked),
                                send_messages=(not locked),
                                read_message_history=(not locked),
                                view_channel=True,
                            )
                            await voiceChannel.set_permissions(
                                default_role,
                                speak=True,
                                connect=(not locked),
                                read_messages=(not locked),
                                send_messages=(not locked),
                                view_channel=True,
                                stream=(not locked),
                                use_voice_activation=True,
                                move_members=(not locked),
                                use_soundboard=allow_soundboard,
                            )
                    except Exception as ex:
                        self.log.error(
                            guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc()
                        )

                    await self._messaging.send_embed(
                        textChannel,
                        self.settings.get_string(guild_id, 'title_new_voice_text_channel'),
                        f"{member.mention}, {self.settings.get_string(guild_id, 'info_new_voice_text_channel')}",
                        delete_after=None,
                        footer=None,
                    )
                    # init_message contains keys that point to strings in the language file.
                    init_message = self.settings.init_message
                    if init_message:
                        # title, message, fields=None, delete_after=None, footer=None
                        fields = []

                        prefix = self.settings.db.get_prefixes(guild_id)[0]
                        for f in range(len(init_message['fields'])):
                            fields.append(
                                EmbedField(
                                    self.settings.get_string(guild_id, init_message['fields'][f]['name']),
                                    utils.str_replace(init_message['fields'][f]['value'], prefix=prefix),
                                ).to_dict()
                            )
                        await self._messaging.send_embed(
                            textChannel,
                            self.settings.get_string(guild_id, init_message['title']),
                            f"{member.mention}, {self.settings.get_string(guild_id, init_message['message'], prefix=prefix)}",
                            fields=fields,
                            delete_after=None,
                            footer=None,
                        )
            except discord.errors.NotFound as nf:
                self.log.warn(guild_id, f"{self._module}.{self._class}.{_method}", str(nf))
            except Exception as ex:
                self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", str(ex), traceback.format_exc())


async def setup(bot):
    await bot.add_cog(ChannelCreatorCog(bot))
