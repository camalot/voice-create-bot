import typing

from bot.cogs.lib import settings, utils

class Users():
    def __init__(self, bot):
        self.bot = bot
        self.settings = settings.Settings()

    def isInVoiceChannel(self, ctx):
        # if ctx is Member
        if hasattr(ctx, "voice"):
            return ctx.voice and ctx.voice.channel is not None
        # if ctx is Context
        if hasattr(ctx, "author"):
            return ctx.author and ctx.author.voice and ctx.author.voice.channel is not None

        # if ctx is interaction
        if hasattr(ctx, "user"):
            return ctx.user and ctx.user.voice and ctx.user.voice.channel is not None

    def isAdmin(self, ctx):
        guild_settings = self.settings.get(ctx.guild.id)
        is_in_guild_admin_role = False
        user = ctx.author if hasattr(ctx, "author") else ctx.user
        channel = ctx.channel if hasattr(ctx, "channel") else None
        # see if there are guild settings for admin role
        if guild_settings:
            for r in guild_settings.admin_roles:
                guild_admin_role = utils.get_by_name_or_id(ctx.guild.roles, r)
                if guild_admin_role in user.roles:
                    is_in_guild_admin_role = True
                    break
        is_bot_owner = str(user.id) == self.settings.bot_owner
        has_admin = user.guild_permissions.administrator or (user.permission_in(channel).manage_guild if channel else False)
        return is_bot_owner or is_in_guild_admin_role or has_admin

    async def get_or_fetch_user(self, userId: typing.Optional[int]):
        try:
            if userId is not None:
                user = self.bot.get_user(userId)
                if not user:
                    user = await self.bot.fetch_user(userId)
                return user
            return None
        except Exception as ex:
            return None

    async def get_or_fetch_member(self, guild, userId: typing.Optional[int]):
        try:
            if userId:
                user = guild.get_member(userId)
                if not user:
                    user = await guild.fetch_member(userId)
                return user
            return None
        except Exception as ex:
            return None
