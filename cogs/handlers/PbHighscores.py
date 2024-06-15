import discord
from discord.ext import commands, tasks
from bot import bot
from datetime import time
from ..handlers.DatabaseHandler import get_channel, turnListOfIds_into_names, mycursor, db, get_role
from ..handlers.EmbedHandler import descriptionOnlyEmbed
from ..util.CoreUtil import get_scale_text, get_scale_text_reverse

def getDiaryTimes():
    mycursor.execute(
        "select diarytimes.diaryId, diarytimes.bossId, diarytimes.scale, bosses.name, bosses.imageUrl from sanity2.diarytimes"
        " inner join sanity2.bosses on diarytimes.bossId = bosses.Id"
    )

    data = mycursor.fetchall()

    return data

def getBossInfo(bossId : int):
    mycursor.execute(
                f"select imageUrl,name from sanity2.bosses where id = {bossId}"
    )

    return mycursor.fetchall()[0]

def getHiscorePbsIgnoreUrl(bossId : int, scale : int):
    mycursor.execute(
        f"select personalbests.time, personalbests.imageUrl, personalbests.members, bosses.imageUrl, personalbests.submittedDate, bosses.name "
        f"from sanity2.personalbests"
        f" inner join sanity2.bosses on personalbests.bossId = bosses.id"
        f" where personalbests.status = 2 and personalbests.bossId = {bossId} and personalbests.scale = {scale} and "
        f" length(personalbests.members) > 6 and members not like '%697357223290077263%' "
        f" order by cast(substring_index(personalbests.time, ':',1) as UNSIGNED) asc, substring_index(personalbests.time, ':',-1) asc"
    )

    data = mycursor.fetchall()

    return data

def getHiscorePbs(bossId : int, scale : int):
    mycursor.execute(
        f"select personalbests.time, personalbests.imageUrl, personalbests.members, bosses.imageUrl, personalbests.submittedDate, bosses.name "
        f"from sanity2.personalbests"
        f" inner join sanity2.bosses on personalbests.bossId = bosses.id"
        f" where personalbests.status = 2 and personalbests.bossId = {bossId} and personalbests.scale = {scale} and "
        f" length(personalbests.members) > 6 and length(bosses.imageUrl) > 4 and members not like '%697357223290077263%' "
        f" order by cast(substring_index(personalbests.time, ':',1) as UNSIGNED) asc, substring_index(personalbests.time, ':',-1) asc"
    )

    data = mycursor.fetchall()

    return data

def get_all_nonquit_users():
    mycursor.execute(
        "select userId, displayName, mainRSN, altRSN, rankId, points, isActive, joinDate, leaveDate, referredBy, birthday "
        "from sanity2.users where rankId != -1"
    )

    sql_users_list = mycursor.fetchall()

    return sql_users_list

@tasks.loop(time=[time(hour=i*6, minute=44) for i in range(4)])  # check if people quit -> set status = 6. Counts for diary, but not leaderboard
async def checkUserPbs():
    print("STARTING PB CHECK=")
    mycursor.execute(
        "select * from sanity2.personalbests where status = 2"
    )

    data = mycursor.fetchall()

    all_users = get_all_nonquit_users()
    all_users_ids = [member[0] for member in all_users]

    for pbSubmission in data:
        members = pbSubmission[2].split(",")
        scale = pbSubmission[5]
        for member in members:
            try:
                member = int(member)
            except:
                member = 421124532
            if member not in all_users_ids or scale != len(members):
                mycursor.execute(
                    f"update sanity2.personalbests set status = 6 where submissionId = {pbSubmission[0]}"
                )

                db.commit()

        #print(members)

    print("===FINISHED PB CHECK=")


@checkUserPbs.before_loop  # REMOVES
async def before():
    await bot.wait_until_ready()
checkUserPbs.start()

@tasks.loop(time=[time(hour=i*6, minute=47) for i in range(4)])
#@tasks.loop(hours=100)
#@tasks.loop(minutes=30)  # update hiscores channel -> editing embed
async def updateHiScores():
    print("STARTING UPDATING HISCORE=")
    sanity = bot.get_guild(301755382160818177)
    pb_channel_id = get_channel("hiscore")
    pb_channel = await sanity.fetch_channel(pb_channel_id)

    pb_top3_ids = []
    role_id = get_role('top3')
    top3_role = sanity.get_role(role_id)
    current_top_3 = [member.id for member in top3_role.members]

    #channel_messages = await pb_channel.history().flatten()
    async for message in pb_channel.history():
        #print("=========================")
        #print(message)
        if message.embeds:
            for embed in message.embeds:
                embed_dict = embed.to_dict()

            try:
                title = embed_dict["title"]
            except:
                title = None

            if title: #embed with title -> try to edit / update
                #print(f"PB UPDATE gucci {title}")
                boss_name = title.replace("**","").split(" - ")[0]
                #print(boss_name)
                boss_scale = get_scale_text_reverse(title.replace("**","").split(" - ")[1])
                #print(boss_scale)

                mycursor.execute(
                    f"select * from sanity2.bosses where name = '{boss_name}'"
                )
                bossId = mycursor.fetchall()[0][0]

                pbdata = getHiscorePbs(bossId, int(boss_scale))
                # print(F"DATA \n {pbdata}")

                pb_msg = ""
                counter = 0
                list_of_team_ids = []
                for x in range(min(3, (len(pbdata)))):
                    membernames, memberids = turnListOfIds_into_names(str(pbdata[counter][2]).split(","))
                    # print(membernames)

                    while memberids in list_of_team_ids and counter < 150:
                        counter += 1
                        membernames, memberids = turnListOfIds_into_names(str(pbdata[counter][2]).split(","))

                    if x == 0:
                        placemsg = "🥇"
                    elif x == 1:
                        placemsg = "🥈"
                    elif x == 2:
                        placemsg = "🥉"

                    timestamp = pbdata[counter][4]

                    pb_msg += f"{placemsg} `{pbdata[counter][0]}` - `{membernames}` - <t:{round(timestamp.timestamp())}:R> - [Proof]({pbdata[counter][1]}) \n"

                    #list for adding roles
                    for id in memberids:
                        #print(f"added {id} -text: place: {x}  time:`{pbdata[counter][0]}` - {membernames}")
                        pb_top3_ids.append(id)

                    #unique team ids ? idk tbh
                    list_of_team_ids.append(memberids)

                    counter += 1

                embed = descriptionOnlyEmbed(title=f"**{getBossInfo(bossId)[1]}** - {get_scale_text(boss_scale)}",
                                             desc=f"{pb_msg}")

                #embed = descriptionOnlyEmbed(title="DN",desc="haaha")
                await message.edit(embed=embed)

    unique_top_3_ids = list(set(pb_top3_ids))
    #print(unique_top_3_ids)

    ### ADD role IF not in
    add_role_list = [id for id in unique_top_3_ids if id not in current_top_3]
    for id in add_role_list:
        member = sanity.get_member(id)
        if member:
            await member.add_roles(top3_role)
        else:
            print(f"member {id} not found")

    ### REMOVE role IF not in
    remove_role_list = [id for id in current_top_3 if id not in unique_top_3_ids]
    for id in remove_role_list:
        member = sanity.get_member(id)
        if member:
            await member.remove_roles(top3_role)
        else:
            print(f"member {id} not found")

    print("===FINISHED UPDATING HISCORE=")

@updateHiScores.before_loop  # REMOVES
async def before():
    await bot.wait_until_ready()
updateHiScores.start()


class PbHiscore(commands.Cog):
    def __init__(self, bot):
        self.client = bot


    @commands.command()
    async def dohiscorething(self, ctx: discord.ApplicationContext):
        pb_channel_id = get_channel("hiscore")
        data = getDiaryTimes()
        #await ctx.message.delete()

        uniqueBossIds = list(set([boss[1] for boss in data]))
        #print(uniqueBossIds)

        pb_channel = await ctx.guild.fetch_channel(pb_channel_id)

        if ctx.channel.id == pb_channel_id:
            await ctx.channel.purge(limit=None)
            #print(pb_channel)

            for bossId in uniqueBossIds:
                if getBossInfo(bossId)[0]:
                    await pb_channel.send(f"{getBossInfo(bossId)[0]}")

                    diariesScale = [boss[2] for boss in data if boss[1] == bossId]
                    for scale in diariesScale:

                        pbdata = getHiscorePbs(bossId, scale)
                        #print(F"DATA \n {pbdata}")

                        pb_msg = ""
                        counter = 0
                        list_of_team_ids = []
                        for x in range(min(5,(len(pbdata)))):
                            membernames, memberids = turnListOfIds_into_names(str(pbdata[counter][2]).split(","))
                            #print(membernames)

                            while memberids in list_of_team_ids and counter < 150:
                                counter += 1
                                membernames, memberids = turnListOfIds_into_names(str(pbdata[counter][2]).split(","))

                            if x == 0:
                                placemsg = "🥇"
                            elif x == 1:
                                placemsg ="🥈"
                            elif x == 2:
                                placemsg = "🥉"

                            timestamp = pbdata[counter][4]

                            pb_msg += f"{placemsg} `{pbdata[counter][0]}` - `{membernames}` - <t:{round(timestamp.timestamp())}:R> - [Proof]({pbdata[counter][1]}) \n"

                            list_of_team_ids.append(memberids)

                            counter += 1

                        embed = descriptionOnlyEmbed(title=f"**{getBossInfo(bossId)[1]}** - {get_scale_text(scale)}", desc=f"{pb_msg}")

                        await pb_channel.send(embed=embed)

            #print(diariesScale)


def setup(bot):
    bot.add_cog(PbHiscore(bot))