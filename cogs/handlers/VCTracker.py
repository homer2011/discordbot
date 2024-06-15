import datetime
from datetime import timedelta
from bot import bot
from .DatabaseHandler import mycursor, db, testingservers, get_all_ranks, get_adminCommands_roles
from .EmbedHandler import descriptionOnlyEmbed
import pandas as pd
import discord
from discord.ext import commands, tasks, bridge, pages
from discord.ext.commands import has_any_role
import numpy as np
def secondsToHours(seconds : int):
    hours = round(seconds/60/60,2)

    return hours

def getdisplayNameFromID(userId: int):
    mycursor.execute(
        f"select displayName from sanity2.users where userId = {userId}"
    )
    displayName = mycursor.fetchall()[0][0]

    return displayName

def getUserListofVcUsers():
    mycursor.execute(
        f"select DISTINCT(userId) from sanity2.vctracker"
    )

    data = mycursor.fetchall()
    return [entry[0] for entry in data]


def getTimeSpentInVCLeaderboard(days:int):
    d = {'userId': [], 'channelId': [], 'Timespent': []}  # data for sum of time spent
    df = pd.DataFrame(data=d)

    dd = {'userId': [], 'channelId': [], 'joinDate': [], 'leaveDate': []}
    datadf = pd.DataFrame(data=dd)

    user_ids = getUserListofVcUsers()
    # user_ids = [314872131186065418,147910030384037888,187414477845692417,222777177643417605]
    for user in user_ids:
        # for x in range(5):
        # user = user_ids[x]

        prev_entry_status = 0
        prev_entry_channnel = 0
        prev_entry_datetime = 0

        userId = user
        # print("===============")
        # print(userId)

        mycursor.execute(
            f"select status,v.channelId, `datetime` from sanity2.vctracker v where userId = {userId} and status in (1,9) and channelId != 608741991794081802 and date_format(v.`datetime`, '%Y-%m-%d-%T') >= NOW() - INTERVAL {days} DAY order by 3 asc,1 desc"
            # 608741991794081802 is afk channel
        )
        data = mycursor.fetchall()
        for entry in data:
            if entry[0] == 1:
                prev_entry_status = entry[0]
                prev_entry_channnel = entry[1]
                prev_entry_datetime = round(entry[2].timestamp())
                prev_entry_datetime_normal = entry[2]

            elif entry[0] == 9:
                if prev_entry_channnel == entry[1] and prev_entry_status == 1:
                    list_of_channelIds = df.loc[df['userId'] == userId, 'channelId'].to_list()

                    # print(list_of_channelIds)
                    if entry[1] in list_of_channelIds:  # add time to current
                        new_time = df.loc[(df['channelId'] == entry[1]) & (
                                df['userId'] == userId), 'Timespent'].sum() + round(
                            entry[2].timestamp()) - prev_entry_datetime
                        df['Timespent'][(df['userId'] == userId) & (df['channelId'] == entry[1])] = new_time

                        # add to second table
                        datadf.loc[len(datadf.index)] = [userId, entry[1], prev_entry_datetime_normal, entry[2]]


                    else:  # add to df
                        df.loc[len(df.index)] = [userId, entry[1], round(entry[2].timestamp()) - prev_entry_datetime]

                        # add to second table
                        datadf.loc[len(datadf.index)] = [userId, entry[1], prev_entry_datetime_normal, entry[2]]

    # print(timespent)
    # print(df)
    totalTimeSpent = df[['userId', 'Timespent']].groupby(by='userId').sum().sort_values(by=['Timespent'],
                                                                                        ascending=False)

    list_of_embeds = []
    description = ""
    page = 0
    ranking = 1
    count = 1
    multiplier = 0

    # print("BIG STUFF HAPPENING")
    #print(len(totalTimeSpent.iterrows()))
    for index, row in totalTimeSpent.iterrows():
        fail = 0
        try:
            test = (index)
            test2 = (row[0])
            # print("SUCCESS")
        except:
            fail = 1
            # print("FAIL")

        if fail == 0:
            if len(description) < 1700 or (ranking - (count + multiplier * 25)) == 25:
                hours = secondsToHours(row[0])
                discordName = getdisplayNameFromID(index)
                description += f"{ranking}. {discordName} - `{hours}` hours \n"
                ranking += 1
                count += 1
                # print(description)

            else:
                embed = discord.Embed(title=f"VC Stats past {days} days - page {page}", description=description)
                description = ""
                page += 1
                multiplier += 1
                count = 1
                list_of_embeds.append(embed)

    return list_of_embeds

def getTimeSpentInVC(author : discord.Member):
    d = {'userId': [], 'channelId': [], 'Timespent': []}  # data for sum of time spent
    df = pd.DataFrame(data=d)

    dd = {'userId': [], 'channelId': [], 'joinDate': [], 'leaveDate': []}
    datadf = pd.DataFrame(data=dd)

    user_ids = getUserListofVcUsers()
    # user_ids = [314872131186065418,147910030384037888,187414477845692417,222777177643417605]

    days = 14

    if author.id in user_ids:

        for user in user_ids:

            prev_entry_status = 0
            prev_entry_channnel = 0
            prev_entry_datetime = 0

            userId = user
            # print("===============")
            # print(userId)

            mycursor.execute(
                f"select status,v.channelId, `datetime` from sanity2.vctracker v where userId = {userId} and status in (1,9) and channelId != 608741991794081802 and date_format(v.`datetime`, '%Y-%m-%d-%T') >= NOW() - INTERVAL {days} DAY order by 3 asc,1 desc"
                # 608741991794081802 is afk channel
            )
            data = mycursor.fetchall()
            for entry in data:
                if entry[0] == 1:
                    prev_entry_status = entry[0]
                    prev_entry_channnel = entry[1]
                    prev_entry_datetime = round(entry[2].timestamp())
                    prev_entry_datetime_normal = entry[2]

                elif entry[0] == 9:
                    if prev_entry_channnel == entry[1] and prev_entry_status == 1:
                        list_of_channelIds = df.loc[df['userId'] == userId, 'channelId'].to_list()

                        # print(list_of_channelIds)
                        if entry[1] in list_of_channelIds:  # add time to current
                            new_time = df.loc[(df['channelId'] == entry[1]) & (
                                        df['userId'] == userId), 'Timespent'].sum() + round(
                                entry[2].timestamp()) - prev_entry_datetime
                            df['Timespent'][(df['userId'] == userId) & (df['channelId'] == entry[1])] = new_time

                            # add to second table
                            datadf.loc[len(datadf.index)] = [userId, entry[1], prev_entry_datetime_normal, entry[2]]


                        else:  # add to df
                            df.loc[len(df.index)] = [userId, entry[1], round(entry[2].timestamp()) - prev_entry_datetime]

                            # add to second table
                            datadf.loc[len(datadf.index)] = [userId, entry[1], prev_entry_datetime_normal, entry[2]]

        # print(timespent)
        # print(df)
        totalTimeSpent = df.loc[df['userId'] == author.id, 'Timespent'].sum()
        #print(f" total time spent {totalTimeSpent}")
        test = df.sort_values('Timespent', ascending=False).to_dict()
        # print(test)

        # dataframe with dates
        # print(datadf)

        user_pairs = pd.merge(datadf, datadf, on='channelId', suffixes=('_user1', '_user2'))
        user_pairs = user_pairs[user_pairs['userId_user1'] != user_pairs['userId_user2']]

        overlap_condition = (
                (user_pairs['joinDate_user1'] <= user_pairs['leaveDate_user2']) &
                (user_pairs['joinDate_user2'] <= user_pairs['leaveDate_user1'])
        )
        user_pairs = user_pairs[overlap_condition]

        user_pairs['max_joinDate'] = np.maximum(user_pairs['joinDate_user1'], user_pairs['joinDate_user2'])
        user_pairs['min_leaveDate'] = np.minimum(user_pairs['leaveDate_user1'], user_pairs['leaveDate_user2'])
        user_pairs['overlapTime'] = user_pairs['min_leaveDate'] - user_pairs['max_joinDate']
        user_pairs['overLapSeconds'] = user_pairs['overlapTime'].dt.total_seconds()
        user_pairs['userId_user2'] = user_pairs['userId_user2'].astype(str)

        # print(user_pairs)

        test = user_pairs.query(f"userId_user1 == {author.id}").groupby(["userId_user2"], as_index=False)[
            "overLapSeconds"].sum().sort_values(['overLapSeconds'], ascending=False)

        values = test.values

        if len(values) > 4:
            description = f"Total time in VC: {secondsToHours(int(totalTimeSpent))} hours \n\n" \
                          f"**Top 5 vc friendos**\n " \
                          f"1. {getdisplayNameFromID(int(values[0][0]))} - `{secondsToHours(int(values[0][1]))}` hours \n" \
                          f"2. {getdisplayNameFromID(int(values[1][0]))} - `{secondsToHours(int(values[1][1]))}` hours \n" \
                          f"3. {getdisplayNameFromID(int(values[2][0]))} - `{secondsToHours(int(values[2][1]))}` hours \n" \
                          f"4. {getdisplayNameFromID(int(values[3][0]))} - `{secondsToHours(int(values[3][1]))}` hours \n" \
                          f"5. {getdisplayNameFromID(int(values[4][0]))} - `{secondsToHours(int(values[4][1]))}` hours \n"

            embed = descriptionOnlyEmbed(title=f"{author.display_name} VC stats past {days} days",desc=description)
        else: #not enough data
            embed=descriptionOnlyEmbed(desc="Not enough data - join more vcs")

        return embed
    else:
        embed = descriptionOnlyEmbed(f"{author.display_name} has not been in vcs <:sadpeepochub:832152660353744927>")
        return embed

def insertVcTrackerEvent(userId:int, channelId:int, status : int, datetime):
    try:
        mycursor.execute(
        "insert into sanity2.vctracker (userId, channelId, status, datetime)"
        "VALUES (%s,%s,%s,%s)",
        (userId, channelId, status, datetime)
        )
    except:
        #print(f"{userId} NOT IN DB (clan friend)")
        pass

    db.commit()

def formatBeforeAfter(before, after):
    try:
        before_channel_id = before.channel.id
    except AttributeError:
        before_channel_id = None

    try:
        after_channel_id = after.channel.id
    except AttributeError:
        after_channel_id = None

    if before.deaf or before.self_deaf or before.self_mute or before.mute:
        before_deafened_or_mute = True
    else:
        before_deafened_or_mute = False

    if after.deaf or after.self_deaf or after.self_mute or after.mute:
        after_deafened_or_mute = True
    else:
        after_deafened_or_mute = False

    before_list = [("Deafened_or_muted",before_deafened_or_mute), ("Channel_id",before_channel_id),
            ("Self_stream",before.self_stream),("Self_video",before.self_video)]

    after_list = [("Deafened_or_muted", after_deafened_or_mute), ("Channel_id", after_channel_id),
            ("Self_stream", after.self_stream), ("Self_video", after.self_video)]

    change = list(set(after_list) - set(before_list))

    return change, before_channel_id, after_deafened_or_mute


@bot.event
async def on_voice_state_update(member, before, after):
    change, beforeChannel, Deafened_Or_Muted = formatBeforeAfter(before, after)
    #print(change[0][0], change[0][1])
    #print(beforeChannel)
    #print(Deafened_Or_Muted)

    now = datetime.datetime.now()
    #### Conditions
    if beforeChannel == None: #action 1 = join
        insertVcTrackerEvent(member.id,after.channel.id,1,now)
        if Deafened_Or_Muted: #action 2 if muted ON JOIN
            insertVcTrackerEvent(member.id, after.channel.id, 2, now)
    try: #if no value to change
        changeValue = change[0][0]
    except:
        changeValue = None

    if changeValue:
        if change[0][0] == "Deafened_or_muted":
            if change[0][1] == True:
                insertVcTrackerEvent(member.id, after.channel.id, 2, now)
            else:
                insertVcTrackerEvent(member.id, after.channel.id, 3, now)

        if change[0][0] == "Channel_id" and beforeChannel:
            if change[0][1] != None: #AFTER.CHANNEL.ID NOT NONE
                #channel change
                insertVcTrackerEvent(member.id, before.channel.id, 9, now)
                insertVcTrackerEvent(member.id, after.channel.id, 1, now)
            else:
                #leave
                insertVcTrackerEvent(member.id, before.channel.id, 9, now)

        if change[0][0] == "Self_stream":
            if change[0][1] == True:
                insertVcTrackerEvent(member.id, after.channel.id, 4, now)
            else:
                insertVcTrackerEvent(member.id, after.channel.id, 5, now)

        if change[0][0] == "Self_video":
            if change[0][1] == True:
                insertVcTrackerEvent(member.id, after.channel.id, 6, now)
            else:
                insertVcTrackerEvent(member.id, after.channel.id, 7, now)

class VCTracker(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    all_ranks = get_all_ranks()
    rank_ids = [rank[2] for rank in all_ranks]

    admin_roles = get_adminCommands_roles()
    admin_roles_ids = [role[1] for role in admin_roles]

    """@bridge.bridge_command(guild_ids=testingservers, name="vcstats_leaderboard",
                           description="See who has spent most time in VC past 30 days")
    @has_any_role(*rank_ids)
    async def vcstats_leaderboard(self, ctx,
                                  days: discord.Option(int, description="Leaderboard for past x number of days", max_value=1000,min_value=1, required=False)):
        await ctx.defer()

        if not days:
            days = 30

        embeds = getTimeSpentInVCLeaderboard(days)

        page_groups = [
        pages.PageGroup(
            pages=embeds,
            description="Time spent in VC leaderboard",
            use_default_buttons=False,
            label="test"
        )]

        paginator = pages.Paginator(pages=page_groups, show_menu=False)
        await paginator.respond(ctx, ephemeral=False)"""

    @bridge.bridge_command(guild_ids=testingservers,name="vcstats", description="See your total time in VC and VC friendos")
    @has_any_role(*rank_ids)
    async def vcstats(self, ctx):
        """Shows time spent in vc and best friendos"""
        await ctx.defer()

        embed = getTimeSpentInVC(ctx.author)

        await ctx.respond(embed=embed)

    @bridge.bridge_command(guild_ids=testingservers, name="adminvcpeep",
                           description="See your total time in VC and VC friendos")
    @has_any_role(*admin_roles_ids)
    async def adminvcpeep(self, ctx, member: discord.Member):
        """Get your VC stats"""
        await ctx.defer()
        if not member:
            member = ctx.author

        embed = getTimeSpentInVC(member)

        await ctx.respond(embed=embed)


def setup(bot):
    bot.add_cog(VCTracker(bot))