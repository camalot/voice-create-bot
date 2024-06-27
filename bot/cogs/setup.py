import inspect
import os
from time import gmtime, strftime
import traceback
import typing

import discord
from discord import app_commands
from discord.ext import commands
from bot.cogs.lib import utils
from bot.cogs.lib import member_helper
from bot.cogs.lib.logger import Log
from bot.cogs.lib.enums.loglevel import LogLevel
from bot.cogs.lib.bot_helper import BotHelper
from bot.cogs.lib.enums.addremove import AddRemoveAction
from bot.cogs.lib.messaging import Messaging
from bot.cogs.lib.models.category_settings import PartialGuildCategorySettings
from bot.cogs.lib.mongodb.channels import ChannelsDatabase
from bot.cogs.lib.mongodb.categorysettings import CategorySettingsDatabase
from bot.cogs.lib.users import Users
from bot.cogs.lib.settings import Settings

class SetupCog(commands.Cog):
    group = app_commands.Group(name="setup", description="Voice Create Setup Commands")

    def __init__(self, bot):
        _method = inspect.stack()[0][3]
        # get the file name without the extension and without the directory
        self._module = os.path.basename(__file__)[:-3]
        self._class = self.__class__.__name__
        self.settings = Settings()
        self.bot = bot

        self.channel_db = ChannelsDatabase()
        self.category_db = CategorySettingsDatabase()

        self.messaging = Messaging(bot)
        self._users = Users(bot)
        self.bot_helper = BotHelper(bot)

        log_level = LogLevel[self.settings.log_level.upper()]
        if not log_level:
            log_level = LogLevel.DEBUG

        self.log = Log(minimumLogLevel=log_level)
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Logger initialized with level {log_level.name}")
        self.log.debug(0, f"{self._module}.{self._class}.{_method}", f"Initialized {self._class}")

    @commands.group(name='setup', aliases=['s'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def setup(self, ctx) -> None:
        await ctx.message.delete()
        pass

    @commands.guild_only()
    # @commands.has_permissions(administrator=True)
    async def bitrate(
        self,
        ctx,
        category: typing.Optional[typing.Union[str, discord.CategoryChannel, int]] = None,
        bitrate: typing.Optional[int] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id

        try:
            if not self._users.isAdmin(ctx):
                self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"{ctx.author.name} is not an admin")
                return

            discord_category = None
            if category is None:
                # TODO: ask for the category
                # get the category for the current channel
                discord_category = ctx.channel.category

            if isinstance(category, str):
                discord_category = discord.utils.get(ctx.guild.categories, name=category)
            elif isinstance(category, int):
                discord_category = discord.utils.get(ctx.guild.categories, id=category)

            if discord_category is None:
                raise commands.BadArgument(f"Category {category} not found")

            bitrate_min = 8
            bitrate_limit = int(round(ctx.guild.bitrate_limit / 1000))
            bitrate_value = bitrate
            if bitrate_value is None or bitrate_value < bitrate_min or bitrate_value > bitrate_limit:
                bitrate_value = await self.messaging.ask_number(
                    ctx=ctx,
                    title=self.settings.get_string(guild_id, "title_voice_channel_settings"),
                    message=utils.str_replace(
                        self.settings.get_string(guild_id, "info_bitrate"),
                        bitrate_min=str(bitrate_min),
                        bitrate_limit=str(bitrate_limit)
                    ),
                    min_value=8,
                    max_value=bitrate_limit,
                    timeout=60,
                    required_user=ctx.author,
                )

                if bitrate_value is None:
                    bitrate_value = bitrate_limit

            self.settings.db.set_guild_category_settings(
                PartialGuildCategorySettings(
                    guildId=guild_id,
                    categoryId=discord_category.id,
                    bitrate=bitrate_value
                )
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @commands.guild_only()
    async def limit(
        self,
        ctx,
        category: typing.Optional[typing.Union[str, discord.CategoryChannel, int]] = None,
        limit: typing.Optional[int] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id

        try:
            if not self._users.isAdmin(ctx):
                self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"{ctx.author.name} is not an admin")
                return

            discord_category = None
            if category is None:
                # TODO: ask for the category
                # get the category for the current channel
                discord_category = ctx.channel.category

            if isinstance(category, str):
                discord_category = discord.utils.get(ctx.guild.categories, name=category)
            elif isinstance(category, int):
                discord_category = discord.utils.get(ctx.guild.categories, id=category)

            if discord_category is None:
                raise commands.BadArgument(f"Category {category} not found")

            limit_min = 0
            limit_max = 100
            limit_value = limit
            if limit_value is None or limit_value < limit_min or limit_value > limit_max:
                limit_value = await self.messaging.ask_number(
                    ctx=ctx,
                    title=self.settings.get_string(guild_id, "title_voice_channel_settings"),
                    message=self.settings.get_string(guild_id, 'ask_limit'),
                    min_value=limit_min,
                    max_value=limit_max,
                    timeout=60,
                    required_user=ctx.author,
                )

                if limit_value is None:
                    limit_value = 0

            self.settings.db.set_guild_category_settings(
                PartialGuildCategorySettings(
                    guildId=guild_id,
                    categoryId=discord_category.id,
                    limit=limit_value
                )
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @commands.guild_only()
    async def locked(
        self,
        ctx,
        category: typing.Optional[typing.Union[str, discord.CategoryChannel, int]] = None,
        locked: typing.Optional[bool] = None,
    ) -> None:
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id

        try:
            if not self._users.isAdmin(ctx):
                self.log.debug(guild_id, f"{self._module}.{self._class}.{_method}", f"{ctx.author.name} is not an admin")
                return

            discord_category = None
            if category is None:
                # TODO: ask for the category
                # get the category for the current channel
                discord_category = ctx.channel.category

            if isinstance(category, str):
                discord_category = discord.utils.get(ctx.guild.categories, name=category)
            elif isinstance(category, int):
                discord_category = discord.utils.get(ctx.guild.categories, id=category)

            if discord_category is None:
                raise commands.BadArgument(f"Category {category} not found")

            locked_value = locked
            if locked_value is None:
                locked_value = await self.messaging.ask_yes_no(
                    ctx=ctx,
                    title=self.settings.get_string(guild_id, "title_voice_channel_settings"),
                    question=self.settings.get_string(guild_id, 'ask_default_locked'),
                    timeout=60,
                    required_user=ctx.author,
                )

                if locked_value is None:
                    locked_value = False

            self.settings.db.set_guild_category_settings(
                PartialGuildCategorySettings(
                    guildId=guild_id,
                    categoryId=discord_category.id,
                    locked=locked_value
                )
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{self._class}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @commands.guild_only()
    async def default_role(
        self,
        ctx,
        category: typing.Optional[typing.Union[str, discord.CategoryChannel, int]] = None,
        default_role: typing.Optional[typing.Union[str, discord.Role, int]] = None,
    ) -> None:
        pass

    @setup.command(name="category", aliases=['cat'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def category(self, ctx):
        _method = inspect.stack()[1][3]
        guild_id = ctx.guild.id

        # is user an admin
        if not self._users.isAdmin(ctx):
            await ctx.channel.send("You are not an administrator. You cannot use this command.", ephemeral=True)
            return

        pass

    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @group.command(name="category", description="Setup category settings for dynamic voice channels")
    @app_commands.describe(category="The category to setup for dynamic channels.")
    @app_commands.describe(bitrate="The bitrate for the dynamic channels. Default: 64")
    @app_commands.describe(limit="The maximum number of users that can join the dynamic channels. Default: 0")
    @app_commands.describe(auto_game="Enable channel name from current game. Default: False")
    @app_commands.describe(allow_soundboard="Allow soundboard in dynamic channels. Default: False")
    @app_commands.describe(auto_name="Auto name the dynamic channels. Default: True")
    @app_commands.describe(locked="Lock the dynamic channels so no one can join unless permitted. Default: False")
    @app_commands.describe(default_role="The default role for the dynamic channels. Default: @everyone")
    async def category_app_command(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
        bitrate: typing.Optional[int] = None,
        limit: typing.Optional[int] = None,
        auto_game: typing.Optional[bool] = False,
        allow_soundboard: typing.Optional[bool] = False,
        auto_name: typing.Optional[bool] = True,
        locked: typing.Optional[bool] = False,
        default_role: typing.Optional[discord.Role] = None,
    ):
        _method = inspect.stack()[0][3]
        if interaction.guild is None:
            return

        guild_id = interaction.guild.id
        try:
            if not self._users.isAdmin(interaction):
                await interaction.response.send_message(
                    self.settings.get_string(interaction.guild.id, "info_permission_denied"),
                    ephemeral=True,
                )
                return
            await self._configure_category(
                guild_id=guild_id,
                category_id=category.id,
                bitrate=bitrate,
                limit=limit,
                auto_game=auto_game,
                allow_soundboard=allow_soundboard,
                auto_name=auto_name,
                locked=locked,
                default_role=default_role,
            )
            await interaction.response.send_message("Category settings updated", ephemeral=True)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())

    async def _configure_category(
        self,
        guild_id: int,
        category_id: int,
        bitrate: typing.Optional[int],
        limit: typing.Optional[int],
        auto_game: typing.Optional[bool] = False,
        allow_soundboard: typing.Optional[bool] = False,
        auto_name: typing.Optional[bool] = True,
        locked: typing.Optional[bool] = False,
        default_role: typing.Optional[discord.Role] = None,
    ):

        # update the category to set the permission overwrites for the default role

        self.category_db.set_guild_category_settings(
            guildId=guild_id,
            categoryId=int(category_id),
            channelLimit=limit if limit is not None else 0,
            channelLocked=locked if locked is not None else False,
            autoGame=auto_game if auto_game is not None else False,
            allowSoundboard=allow_soundboard if allow_soundboard is not None else False,
            autoName=auto_name if auto_name is not None else True,
            bitrate=bitrate if bitrate is not None else 64,
            defaultRole=default_role.id if default_role else "@everyone"
        )

    @setup.command(name="channel", aliases=['c'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def channel(self, ctx) -> None:
        _method = inspect.stack()[0][3]
        try:
            pass
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(ctx)

    @commands.guild_only()
    @app_commands.guild_only()
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    @group.command(name="channel", description="Create a new CREATE voice channel")
    @app_commands.describe(channel_name="The name of the channel to create. Default: CREATE CHANNEL 🔊")
    @app_commands.describe(category="The category to create the channel in and all dynamic channels.")
    async def channel_app_command(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
        channel_name: typing.Optional[str] = "CREATE CHANNEL 🔊",
        use_stage: typing.Optional[bool] = False,
    ):
        _method = inspect.stack()[0][3]
        if interaction.guild is None:
            return

        guild_id = interaction.guild.id
        try:
            # is user an admin
            if not self._users.isAdmin(interaction):
                await interaction.response.send_message(
                    self.settings.get_string(interaction.guild.id, "info_permission_denied"),
                    ephemeral=True,
                )
                return

            if channel_name is None or channel_name == "":
                channel_name = "CREATE CHANNEL 🔊"
            if use_stage is None:
                use_stage = False

            self.log.debug(guild_id, _method, f"category: {category}")

            default_role = self.settings.db.get_default_role(
                guildId=guild_id, categoryId=category.id, userId=None
            )
            self.log.debug(guild_id, _method, f"default_role: {default_role}")
            temp_default_role = utils.get_by_name_or_id(interaction.guild.roles, default_role)
            self.log.debug(guild_id, _method, f"temp_default_role: {temp_default_role}")
            system_default_role = interaction.guild.default_role
            temp_default_role = temp_default_role if temp_default_role else system_default_role
            if use_stage:
                new_channel = await category.create_stage_channel(
                    name=channel_name,
                    bitrate=64 * 1000,
                    user_limit=0,
                    position=0,
                    overwrites={
                        temp_default_role: discord.PermissionOverwrite(
                            view_channel=True,
                            connect=True,
                            speak=True,
                            stream=False,
                            use_voice_activation=True
                        )
                    },
                    reason=f"Created for VoiceCreateBot by {interaction.user.name}"
                )
            else:
                new_channel = await category.create_voice_channel(
                    name=channel_name,
                    bitrate=64 * 1000,
                    user_limit=0,
                    position=0,
                    overwrites={
                        temp_default_role: discord.PermissionOverwrite(
                            view_channel=True,
                            connect=True,
                            speak=True,
                            stream=False,
                            use_voice_activation=True
                        )
                    },
                    reason=f"Created for VoiceCreateBot by {interaction.user.name}"
                )

            self.channel_db.set_create_channel(
                guildId=guild_id,
                voiceChannelId=new_channel.id,
                categoryId=category.id,
                ownerId=interaction.user.id,
                useStage=use_stage
            )

            await interaction.response.send_message(f"Channel {new_channel.mention} created", ephemeral=True)
        except Exception as e:
            self.log.error(guild_id, _method, str(e), traceback.format_exc())
        pass

    @setup.group(name="role", aliases=['r'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def role(self, ctx):
        pass

    # set prefix command that allows multiple prefixes to be passed in
    @setup.command(name='prefix', aliases=['p'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def prefix(self, ctx, *, prefixes: typing.List[str] = []):
        _method = inspect.stack()[0][3]
        try:
            guild_id = ctx.guild.id
            if len(prefixes) == 0:
                prefixes = self.settings.db.get_prefixes(guildId=guild_id)
                if prefixes is None:
                    await ctx.send_embed(
                        channel=ctx.channel,
                        title="Prefixes",
                        message=f"Prefixes are not set", delete_after=10)
                    return
                await ctx.send_embed(
                    channel=ctx.channel,
                    title="Prefixes",
                    message=f"Prefixes are `{', '.join(prefixes)}`",
                    delete_after=10)
            else:
                self.settings.db.set_prefixes(
                    guildId=ctx.guild.id,
                    prefixes=prefixes
                )
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    title=self.settings.get_string(guild_id, "title_prefix"),
                    message=f'{ctx.author.mention}, {utils.str_replace(self.settings.get_string(guild_id, "info_set_prefix"), prefix=prefixes[0])}',
                    delete_after=10)

                await ctx.send_embed(
                    channel=ctx.channel,
                    title="Prefixes",
                    message=f"Prefixes set to `{', '.join(prefixes)}`",
                    delete_after=10)
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"Error: {e}")
            traceback.print_exc()

    @role.command(name="user", aliases=['u'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def user(self, ctx, inputRole: typing.Optional[typing.Union[str, discord.Role]] = None):
        _method = inspect.stack()[0][3]
        try:
            guild_id = ctx.guild.id
            author = ctx.author
            if inputRole is None:
                # NO ROLE PASSED IN. Treat this as a get command
                if member_helper.is_in_voice_channel(ctx.author):
                    voice_channel = ctx.author.voice.channel
                    user_id = self.channel_db.get_channel_owner_id(guildId=guild_id, channelId=voice_channel.id)
                    result_role_id = self.settings.db.get_default_role(
                        guildId=guild_id,
                        categoryId=voice_channel.category.id,
                        userId=user_id
                    )
                    if result_role_id:
                        role: discord.Role = utils.get_by_name_or_id(ctx.guild.roles, result_role_id)
                        await self.messaging.send_embed(
                            channel=ctx.channel,
                            title=self.settings.get_string(guild_id, 'title_voice_channel_settings'),
                            message=f"{author.mention}, {utils.str_replace(self.settings.get_string(guild_id, 'info_get_default_role'), role=role.name)}",
                            fields=None,
                            delete_after=30
                        )
                    else:
                        await self.messaging.send_embed(
                            channel=ctx.channel,
                            title=self.settings.get_string(guild_id, 'title_voice_channel_settings'),
                            message=f"{author.mention}, {self.settings.get_string(guild_id, 'info_default_role_not_found')}",
                            fields=None, delete_after=5
                        )
                else:
                    await self.messaging.send_embed(
                        channel=ctx.channel,
                        title=self.settings.get_string(guild_id, "title_not_in_channel"),
                        message=f'{author.mention}, {self.settings.get_string(guild_id, "info_not_in_channel")}',
                        delete_after=5
                    )
                return
            default_role: discord.Role = ctx.guild.default_role

            if isinstance(inputRole, str):
                default_role = discord.utils.get(ctx.guild.roles, name=inputRole)
            elif isinstance(inputRole, discord.Role):
                default_role = inputRole

            if default_role is None:
                raise commands.BadArgument(f"Role {default_role} not found")
            # self.db.set_default_role_for_guild(ctx.guild.id, default_role.id)
            ctx.send(f"Default role set to {default_role.name}")
        except Exception as e:
            self.log.error(ctx.guild.id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())

    @group.command(name="admin", description="Add or remove an admin role")
    @commands.guild_only()
    @app_commands.guild_only()
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(action="Add or Remove the role")
    @app_commands.describe(role="The role to add or remove")
    async def role_admin_app_command(self, interaction: discord.Interaction, action: AddRemoveAction, role: discord.Role):
        _method = inspect.stack()[0][3]
        if interaction.guild is None:
            return

        guild_id = interaction.guild.id
        try:
            if not self._users.isAdmin(interaction):
                await interaction.response.send_message(
                    self.settings.get_string(guild_id, "info_permission_denied"),
                    ephemeral=True,
                )
                return

            if action == AddRemoveAction.ADD:
                self.settings.db.add_admin_role(guildId=guild_id, roleId=role.id)
                await interaction.response.send_message(f"Added role {role.name}", ephemeral=True)
            elif action == AddRemoveAction.REMOVE:
                self.settings.db.delete_admin_role(guildId=guild_id, roleId=role.id)
                await interaction.response.send_message(f"Removed role {role.name}", ephemeral=True)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(interaction)

    @group.command(name="default-role", description="Set the default role for channels")
    @commands.guild_only()
    @app_commands.guild_only()
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(role="The role to set as the default role for channels")
    async def role_default_app_command(self, interaction: discord.Interaction, role: discord.Role):
        _method = inspect.stack()[0][3]
        if interaction.guild is None:
            return

        guild_id = interaction.guild.id
        try:
            if not self._users.isAdmin(interaction):
                await interaction.response.send_message(
                    self.settings.get_string(guild_id, "info_permission_denied"),
                    ephemeral=True,
                )
                return

            self.settings.db.set_default_role(guildId=guild_id, roleId=role.id)
            await interaction.response.send_message(f"Set role {role.name} as the default guild role", ephemeral=True)
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(interaction)

    @role.command(name="admin", aliases=['a'])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx, action: typing.Optional[AddRemoveAction],  role: typing.Optional[typing.Union[str, discord.Role]]):
        _method = inspect.stack()[0][3]
        guild_id = ctx.guild.id
        try:
            if not self._users.isAdmin(ctx):
                await self.messaging.send_embed(
                    channel=ctx.channel,
                    message=self.settings.get_string(guild_id, "info_permission_denied"),
                    title=self.settings.get_string(guild_id, "title_permission_denied"),
                    delete_after=10
                )
                return

            if action is None and role is None:
                # return the list of admin roles
                pass

            admin_role: typing.Optional[discord.Role] = None
            if isinstance(role, str):
                admin_role = discord.utils.get(ctx.guild.roles, name=role)
            elif isinstance(role, discord.Role):
                admin_role = role

            if admin_role is None:
                raise commands.BadArgument(f"Role {admin_role} not found")

            if action == AddRemoveAction.ADD:
                self.settings.db.add_admin_role(guildId=guild_id, roleId=admin_role.id)
                ctx.send(f"Added role {admin_role.name}", delete_after=5)
            elif action == AddRemoveAction.REMOVE:
                self.settings.db.delete_admin_role(guildId=guild_id, roleId=admin_role.id)
                ctx.send(f"Removed role {admin_role.name}", delete_after=5)
        except Exception as e:
            await self.messaging.notify_of_error(ctx)
            self.log.error(guild_id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())


    # @staticmethod
    async def language_autocomplete(self, interaction: discord.Interaction, current: str) -> typing.List[app_commands.Choice[str]]:
        # return as list of discord.app_commands.Choice
        languages = self.settings.languages
        # languages is a dictionary of language code and language name
        # set the choice value to the language code
        # set the choice name to the language name
        # loop the language dictionary keys and return a list of discord.app_commands.Choice
        return [
            app_commands.Choice(name=value, value=key)
            for key, value in languages.items()
            if current.lower() in key.lower() or current == "" or current.lower() in value.lower()
        ]

    @group.command(name="language", description="Get or Set the language for the bot")
    @commands.guild_only()
    @app_commands.guild_only()
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(language="The language to set for the bot")
    @app_commands.autocomplete(language=language_autocomplete)
    async def language_app_command(self, interaction: discord.Interaction, language: typing.Optional[str]) -> None:
        _method = inspect.stack()[0][3]
        if interaction.guild is None:
            return
        guild_id = interaction.guild.id
        try:
            if not self._users.isAdmin(interaction):
                await interaction.response.send_message(
                    self.settings.get_string(guild_id, "info_permission_denied"),
                    ephemeral=True,
                )
                return

            if language is None or language == "":
                language = self.settings.db.get_language(guildId=guild_id)
                await interaction.response.send_message(
                    self.settings.get_string(guildId=guild_id, key="info_language_get", language=language),
                    ephemeral=True,
                )
                return

            if not language.lower() in [key.lower() for key,value in self.settings.languages.items()]:
                await interaction.response.send_message(
                    self.settings.get_string(guildId=guild_id, key="info_language_not_found", language=language),
                    ephemeral=True,
                )
                return

            self.settings.db.set_language(guildId=guild_id, language=language)
            self.settings.set_guild_strings(guildId=guild_id, lang=language)
            await interaction.response.send_message(
                self.settings.get_string(guildId=guild_id, key="info_language_set", language=language),
                ephemeral=True,
            )
        except Exception as e:
            self.log.error(guild_id, f"{self._module}.{_method}", f"{e}", traceback.format_exc())
            await self.messaging.notify_of_error(interaction)


async def setup(bot):
    await bot.add_cog(SetupCog(bot))
