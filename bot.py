import os
import discord
from discord.ext import commands
from cogs.handlers.DatabaseHandler import bot_prefix, token
from discord.ext import bridge
from cogs.commands.dropSubmit import submissionAcceptor, submissionButtons
from cogs.commands.pbSubmit import pbsubmissionAcceptor
from cogs.commands.admin import trialFeedbackButton
#from cogs.handlers.loops import rankChangerView

intents = discord.Intents.all()
bot = bridge.Bot(command_prefix=f'{bot_prefix}', intents=intents)


#bot.load_extension("cogs.handlers.DatabaseHandler")

if bot_prefix == "!":
    for path, subdirs , files in os.walk("./cogs"): #load the cog files
        for name in files:
            if os.path.join(path, name).endswith(".py"):
                #print({path.split('/')[-1]})
                #print(f"cogs.{path.split(chr(92))[1]}.{name[:-3]}")
                if not f"cogs.{path.split('/')[-1]}.{name[:-3]}" == "cogs.handlers.DatabaseHandler":
                    bot.load_extension(f"cogs.{path.split('/')[-1]}.{name[:-3]}")
else: #run local
    for path, subdirs, files in os.walk("./cogs"):  # load the cog files
        for name in files:
            if os.path.join(path, name).endswith(".py"):
                bot.load_extension(f"cogs.{path.split(chr(92))[1]}.{name[:-3]}")

print("LOADED COGS")


@bot.event
async def on_ready():
    print(f"{bot.user} is online!")
    bot.add_view(trialFeedbackButton())
    bot.add_view(submissionAcceptor())
    bot.add_view(pbsubmissionAcceptor())
    #bot.add_view(submissionButtons())
    #bot.add_view(rankChangerView())

bot.run(token)


