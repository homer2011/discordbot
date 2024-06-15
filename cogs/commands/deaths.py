from discord.ext import commands
import discord
from bot import bot
from ..handlers.DatabaseHandler import mycursor, db
import random as r

@bot.event
async def on_message(message):
    if message.channel.id == 1020568180147638332: #and message.author.id == 1020568216981995570:
        #print(message.attachments)
        #print(message.attachments[0])
        if message.attachments and "died lmfao" in message.content.lower() and len(message.content) < 30: #and filename = "image.png"
            #print(message.attachments[0])
            number = r.randint(0, 8)
            filename = f"{number}ded.png"
            await message.attachments[0].save(f"{filename}")

            #send
            rsn = (message.content).lower().replace(" died lmfao.", "")
            if len(rsn) > 12:
                rsn = rsn[0:11]

            #dasc
            death_channel = bot.get_channel(1020739207154651296) #replace with actual death channel
            embed = discord.Embed(
                description=f"**{message.content}**"
            )
            file = discord.File(f"{filename}",filename=f"{filename}")
            embed.set_image(url=f"attachment://{filename}")

            death_msg = await death_channel.send(file=file, embed=embed)
            #await death_msg.add_reaction("<:sit:1020751564983513168>")
            #print(death_msg.id)

            mycursor.execute("INSERT INTO sanity2.deathTable (msgID, time, rsn) VALUES (%s, %s, %s)",
                             (death_msg.id, message.created_at, rsn))
            db.commit()

    else:
        await bot.process_commands(message)


class deaths(commands.Cog):
    def __init__(self, bot):
        self.client = bot



def setup(bot):
    bot.add_cog(deaths(bot))