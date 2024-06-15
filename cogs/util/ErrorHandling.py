from http.client import InvalidURL

import aiohttp
import mysql.connector
from discord.ext import commands
from bot import bot
from mysql.connector.errors import IntegrityError

#examples, meh still work 2 do

class ErrorHandling(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    @bot.event
    async def on_application_command_error(ctx, error):
        exco = getattr(error, "original", error)
        print(exco)
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.respond("This command is on a %.2fs cooldown" % error.retry_after, ephemeral=True)
        elif isinstance(error, (commands.MissingRole, commands.MissingAnyRole)):
            rolelist = ""
            for role in range(len(error.missing_roles)):
                rolelist = rolelist + f"<@&{error.missing_roles[role]}> "
            await ctx.respond(f"You are missing any of these roles: {rolelist}",ephemeral=True)

        elif isinstance(error, commands.CommandInvokeError):
            await ctx.respond(f"Bot is missing permissions",ephemeral=True)

        #sql errors
        elif isinstance(exco, IntegrityError):
            await ctx.respond(f"{exco}",ephemeral=True)
            #add to auditlog?

        else:
            raise error



    @bot.event  # errorhandlign
    async def on_command_error(ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.respond(f"user was not found",ephemeral=True)
        elif isinstance(error, commands.CommandNotFound):
            print(error.args[0])
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.respond('This command is on a %.2fs cooldown' % error.retry_after, delete_after=5,ephemeral=True)
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.respond(f"{str(error.args[0])}",ephemeral=True)
        elif isinstance(error, commands.MissingPermissions):
            await ctx.respond(f"{str(error.args[0])}",ephemeral=True)
        elif isinstance(error, (commands.MissingRole, commands.MissingAnyRole)):
            rolelist = ""
            for role in range(len(error.missing_roles)):
                rolelist = rolelist + f"{error.missing_roles[role]} "
            await ctx.respond(f"You are missing any of these roles: {rolelist}",ephemeral=True)
        else:
            raise error

def setup(bot):
    bot.add_cog(ErrorHandling(bot))