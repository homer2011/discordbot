import discord
from discord.ext import commands
from ..util.CoreUtil import utc_time

def greenDropsEmbed(title : str, drop_name : str, drop_value : float, clannies : str, nonClannies : int, extra_note : str = None): #, image : discord.File
    embed = discord.Embed(
        title=title,
        color=discord.Colour.green()
    )
    embed.add_field(name="Drop:", value=drop_name) #inline=False to show them on 1 line each
    embed.add_field(name="Drop value (m)", value=str(drop_value))
    embed.add_field(name="Clannies", value=clannies)
    embed.add_field(name="Nonclannies", value=str(nonClannies))

    if extra_note:
        embed.add_field(name="Extra notes", value=extra_note)


    embed.set_image(url="attachment://image.png")

    embed.set_footer(text=utc_time())

    return embed

def embedVariable(title : str, color : discord.Colour, *args):
    embed = discord.Embed(
        title=title,
        color=color
    )
    for arg in args:
        if arg[1]:
            embed.add_field(name=arg[0],value=arg[1])

    embed.set_image(url="attachment://image.png")

    embed.set_footer(text=utc_time())

    return embed

def descriptionOnlyEmbed(desc : str, title : str = None):
    if title:
        embed = discord.Embed(
            title=title,
            description=desc,
            colour=discord.Colour.blue()
        )
    else:
        embed = discord.Embed(
            description=desc,
            colour=discord.Colour.blue()
        )

    return embed


class EmbedHandler(commands.Cog):
    def __init__(self, bot):
        self.client = bot

def setup(bot):
    bot.add_cog(EmbedHandler(bot))


