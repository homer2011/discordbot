from discord.ext import commands, tasks
import discord
from datetime import datetime, time
from bot import bot
from .DatabaseHandler import mycursor

def getBirthdays(day_of_year):
    mycursor.execute(
        f"SELECT userId,displayName,birthday from sanity2.users where dayofyear(birthday) >= {day_of_year} and isActive = 1 order by month(birthday) asc, day(birthday) ASC")
    table = mycursor.fetchall()

    return table

@tasks.loop(time=[time(hour=17)]) #BIRTHDAY STARTER
async def birthday_starter():
    print("PRINTED BIRTHDAYS")
    day_of_year = datetime.now().timetuple().tm_yday

    table = getBirthdays(day_of_year)

    string_embed = ""
    birthday_count = 0
    for x in range(min(10, len(table))):
        birthdayDate = table[x][2]
        birthdayyear = birthdayDate.year
        current_year = datetime.now().year

        now = datetime.today()

        birthdayDateString = f"{birthdayDate.month}-{birthdayDate.day}"
        todayString = f"{now.month}-{now.day}"
        #print(F"{birthdayDateString} AND {todayString}")

        if birthdayDateString == todayString:
            age = (int(current_year) - int(birthdayyear))

            birthday_date = "🥳**Happy birthday!**🥳"
            birthday_count += 1
            if age < 100:
                birthday_date = f"🥳Happy birthday!🥳 - Turning `{age}` \n"

            guild = bot.get_guild(301755382160818177)  # 305380209366925312 # 580855880426324106
            user = guild.get_member(int(table[x][0])) #gets displayname of member
            string_embed = string_embed + f"**{user.display_name}** - {birthday_date} \n"

    #print(string_embed)

    embed = discord.Embed(
        title=f"<a:Baldy:792592504989417472> 🥳**Sanity birthdays!**🥳 <a:Baldy:792592504989417472>\n",
        description=f"🎉Birthday boys n girls in Sanity today:🎉 Wish them a happy birthday❤️\n\n"
                    f"{string_embed}",
        color=discord.Color.purple()
    )
    guild = bot.get_guild(301755382160818177) #305380209366925312 # 580855880426324106
    user = guild.get_member(int(table[0][0]))
    #print(user)

    try:
        embed.set_thumbnail(url=f"{user.avatar.url}")
    except:
        embed.set_thumbnail(url=f"{user.default_avatar.url}")

    channel = bot.get_channel(316209688180162560) #872830642646302812 #580855881302802466 # bot-stuff #872830642646302812 #921677002057064469 #public 580855881302802466
    #print(birthday_count)
    if birthday_count > 0:
        await channel.send("<@&986487111358218310>",embed=embed)
    else:
        print("NO BIRTHDAYS")

@birthday_starter.before_loop #REMOVES
async def before():
    await bot.wait_until_ready()
birthday_starter.start()

class birthdaystuff(commands.Cog):
    def __init__(self, bot):
        self.client = bot




def setup(bot):
    bot.add_cog(birthdaystuff(bot))