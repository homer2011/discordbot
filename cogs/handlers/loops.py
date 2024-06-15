import gspread
import mysql
from discord.ext import commands, tasks
from discord.ui import View, Modal, InputText, Button, button
import datetime
from datetime import time
import discord
from dateutil import relativedelta
from bot import bot
from cogs.commands import admin
from cogs.commands.admin import datetime_to_string
from cogs.handlers.DatabaseHandler import get_all_ranks, get_all_users, updateUserRank, mycursor, getUserData, db, insert_Point_Tracker, db_user,updatersn, \
    getUserData, get_all_active_users, get_channel, insert_audit_Logs, fetchranksGracePeriod, update_user_points, insert_Point_Tracker, turnListOfIds_into_names, add_user_todb, bingoModeCheck
from cogs.handlers.EmbedHandler import embedVariable
from cogs.util.CoreUtil import get_diary_difficulty
import requests

"""
2 checks required:
 1. check if database matches discord -> loop through every member in server
 2. check if user from server is missing in DB

Loops:
 1. Check if users are not added, or retired
 2. check if points / diary reqs > threshold for next rankup ---- unless we check when drops are accepted -> change from loop to normal command and trigger from accept
    - need something to check the diary / master diary points hmmge"""
def getUserPointsThisMonth(userId :int):
    month = datetime.datetime.now().month
    year = datetime.datetime.now().year

    mycursor.execute(
        f"SELECT sum(pointtracker.points) from sanity2.pointtracker inner join sanity2.users on pointtracker.userId = users.userId "
        f" where month(`date`) = {month} and year(`date`) = {year} and users.userId = {userId}"
    )
    dataThisMonth = mycursor.fetchall()
    if len(dataThisMonth) > 0:
        return dataThisMonth[0][0]
    else:
        return 0

def getUserPointsPrevious2Month(userId :int):
    month = datetime.datetime.now().month
    year = datetime.datetime.now().year
    prevmonth = 0

    if month == 2:
        year -= 1
        month = 12
    else:
        prevmonth += 2


    if month == 1:
        year -= 1
        month = 11
    else:
        prevmonth += 2


    if prevmonth == 4:
        month -= 2

    mycursor.execute(
        f"SELECT sum(pointtracker.points) from sanity2.pointtracker inner join sanity2.users on pointtracker.userId = users.userId "
        f" where month(`date`) = {month} and year(`date`) = {year} and users.userId = {userId}"
    )
    dataPastMonth = mycursor.fetchall()
    if len(dataPastMonth) > 0:
        return dataPastMonth[0][0]
    else:
        return 0

def getUserPointsPreviousMonth(userId :int):
    month = datetime.datetime.now().month
    year = datetime.datetime.now().year

    if month == 1:
        year -= 1
        month = 12
    else:
        month -= 1

    mycursor.execute(
        f"SELECT sum(pointtracker.points) from sanity2.pointtracker inner join sanity2.users on pointtracker.userId = users.userId "
        f" where month(`date`) = {month} and year(`date`) = {year} and users.userId = {userId}"
    )
    dataPastMonth = mycursor.fetchall()
    if len(dataPastMonth) > 0:
        return dataPastMonth[0][0]
    else:
        return 0


def updateNick(userId : int, NewNick : str):
    mycursor.execute(
        f"update sanity2.users set displayName = '{NewNick}' where userId = {userId}"
    )
    db.commit()

def updateDiaryTier(userId :int, tierClaimed: int):
    mycursor.execute(
        f"update sanity2.users set diaryTierClaimed = {tierClaimed} where userId = {userId}"
    )
    db.commit()

def getUserDiaryTier(userId :int):
    mycursor.execute(
        f"select diaryTierClaimed from sanity2.users where userId = {userId}"
    )
    tierClaimed = mycursor.fetchall()[0][0]

    return tierClaimed

def getDiaryPointReward(diaryTier):
    mycursor.execute(
        f"select points from sanity2.diaryrewards where diaryTier = {diaryTier}"
    )
    data = mycursor.fetchall()

    return data[0][0]

def getRoleId(name : str):
    mycursor.execute(
        f"select * from sanity2.roles where name = '{name}'"
    )
    data = mycursor.fetchall()
    if len(data) > 0:
        return data[0][1]
    else:
        return None

def latestNameChanges(groupId):
    x = requests.get(f'https://api.wiseoldman.net/v2/groups/{groupId}/name-changes?limit=5')
    return x.json()

def checkIfRSNinDB(rsn : str):
    mycursor.execute(
        f"select * from sanity2.users where mainRSN = '{rsn}'"
    )
    data = mycursor.fetchall()

    if data:
        return data
    else:
        return None




class diaryPointClaimerView(View):  # for council / drop acceptors etc in #posted-drops
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction):
        mycursor.execute(
            "select discordRoleId,name from sanity2.roles where adminCommands = 1"
        )
        data = mycursor.fetchall()
        list = [i[0] for i in data]

        interaction_user_roleID_list = [role.id for role in interaction.user.roles]

        check = any(role in interaction_user_roleID_list for role in list)
        return check

    @button(label="Give pts!", custom_id="acceptor-accept-button-66" ,style=discord.ButtonStyle.green, emoji="✅")
    async def givepts(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        now = datetime.datetime.now()
        #title = int(str(embed_dict["title"]))
        tiersClaimed = int(embed_dict["fields"][0]["value"])
        thisTier = int(embed_dict["fields"][1]["value"])
        points = int(embed_dict["fields"][2]["value"])
        userId = int(embed_dict["fields"][3]["value"])

        #print(memberId, previousRankId, newRankId)

        embed = discord.Embed.from_dict(embed_dict)
        embed.color = discord.Color.green()


        insert_audit_Logs(interaction.user.id, 5, now, f"DiaryTierClaimed {tiersClaimed} - pts {points} ",userId)
        update_user_points(userId,points)
        insert_Point_Tracker(userId,points,datetime.datetime.now(),f"Diary tier {thisTier}")

        #set diaryTier in users table to max(current claimed / prev claim)
        tiersClaimedDb = getUserDiaryTier(userId)
        updateDiaryTier(userId,max(tiersClaimedDb,thisTier))

        await interaction.message.edit(embed=embed,view=None)
        #await interaction.response.send_message("drop accepted and points given",)


    @button(label="Already claimed higher tier", custom_id="acceptor-decline-button-77", style=discord.ButtonStyle.danger, emoji="✖️")
    async def alreadyclaimedpts(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        now = datetime.datetime.now()
        # title = int(str(embed_dict["title"]))
        tiersClaimed = int(embed_dict["fields"][0]["value"])
        thisTier = int(embed_dict["fields"][1]["value"])
        points = int(embed_dict["fields"][2]["value"])
        userId = int(embed_dict["fields"][3]["value"])

        embed = discord.Embed.from_dict(embed_dict)
        embed.color = discord.Color.red()

        tiersClaimedDb = getUserDiaryTier(userId)
        insert_audit_Logs(interaction.user.id, 5, now, f"DiaryTierClaimed set to {max(tiersClaimedDb, thisTier)} - no pts", userId)
        updateDiaryTier(userId, max(tiersClaimedDb, thisTier))

        await interaction.message.edit(embed=embed,view=None)
        #await interaction.response.send_message("The submission has been removed")

"""@task.loop(seconds=30)
async def auditlogposter():"""

@tasks.loop(time=[time(hour=16,minute=14)]) #UPDATE RSN changes
async def rsnwiseoldmanupdater():
    text = latestNameChanges(230)

    lengthJson = len(text)
    for x in range(len(text)):
        entry = (text[lengthJson-x-1])

        prevRSN = entry["oldName"]
        checkRSN = checkIfRSNinDB(prevRSN)
        #print(checkRSN)
        status = entry['status']

        if checkRSN and status == 'approved':
            newRsn = entry['newName']
            dbUserId = checkRSN[0][0]
            updatersn(dbUserId,1,newRsn)
            print(f"updated {dbUserId} rsn to {newRsn}")

    print("done updating names!")

@rsnwiseoldmanupdater.before_loop  # REMOVES
async def before():
    await bot.wait_until_ready()
rsnwiseoldmanupdater.start()


@tasks.loop(time=[time(hour=17,minute=41)])
async def updatealldairiepoints():
    try:
        await admin.Admin.updatediaries(ctx=None)
        print("finished updating diary points")
    except:
        print("failed updating diary points - updatealldairiepoints - might have worked still")

@updatealldairiepoints.before_loop  # REMOVES
async def before():
    await bot.wait_until_ready()
updatealldairiepoints.start()

@tasks.loop(minutes=5)
async def bingoSheetUpdater():
    bingoVal = bingoModeCheck()
    #print(bingoVal)
    if bingoVal == 1:
        #DO BINGO STUFF
        print(F"UPDATING BINGO SHEET---")
        try:
            sa = gspread.service_account("sanitydb-v-363222050972.json")
            sheet = sa.open(f"bingo")
            test = 1
        except gspread.exceptions.APIError:
            test = 0
            print("API ERROR UPDATING GSPREAD sheet")

        if test == 1:
            # tableList = [table[0] for table in mycursor.fetchall()]
            # print(tableList)
            # for table in tableList:
            # print(f"TABLE ==== {table}")
            workSheet = sheet.worksheet("Ark1")
            # Get the values from column A
            column_values = workSheet.col_values(1)
            len_gsheet = len(column_values)
            if len_gsheet > 0:
                joinedFormat = f"({','.join(str(value) for value in column_values if str(value) != 'Id')})"
            else:
                joinedFormat = "(0,1,2)"

            # print(joinedFormat)

            # NEW bingo drops from past 15 days
            mycursor.execute(
                f"SELECT Id,userId,participants,value,imageUrl,notes,submittedDate from sanity2.submissions where bingo = 1 "
                f"  and status = 2  and Id not in {joinedFormat}"
                # and submittedDate  BETWEEN NOW() - INTERVAL 15 DAY AND NOW() <- only past 15 days
            )
            table = mycursor.fetchall()
            # descriptions = [[str(item[0]) for item in mycursor.description]]

            actualTable = [list(tuple) for tuple in table]

            datetime_to_string(actualTable)  # gspread doesnt like datetime.datetime obj -> converts to string
            workSheet.update(values=actualTable, range_name=f'A{len_gsheet + 1}')




@bingoSheetUpdater.before_loop  # REMOVES
async def before():
    await bot.wait_until_ready()
bingoSheetUpdater.start()

@tasks.loop(time=[time(hour=20,minute=14)])
async def elderRankGiver():
    active_users_list = get_all_active_users()
    sanity = bot.get_guild(301755382160818177)
    now = datetime.datetime.now()

    for member in active_users_list:
        joinDate = member[7]
        relativeDif = relativedelta.relativedelta(now, joinDate)
        years = relativeDif.years
        elder_role_id = getRoleId("1YEAR")

        if years > 0:
            member_disc = sanity.get_member(member[0])
            if member_disc:
                """print(f"{member_disc.display_name}")"""
                member_ranks = [rank.id for rank in member_disc.roles]
                if elder_role_id not in member_ranks:
                    new_role = sanity.get_role(elder_role_id)
                    #print(f"added elder role to {member[0]}")
                    await member_disc.add_roles(new_role)
                    insert_audit_Logs(member_disc.id,8,datetime.datetime.now(),"Elder role assigned",member_disc.id)

@elderRankGiver.before_loop  # REMOVES
async def before():
    await bot.wait_until_ready()
elderRankGiver.start()

@tasks.loop(time=[time(hour=18)]) #
async def diaryPointsClaimer():
    mycursor.execute(
        "select userId ,displayName ,max(diaryPoints) ,max(masterDiaryPoints) ,max(diaryTierClaimed), max(d.diaryTier), max(d.diaryPointsReq)  from sanity2.users u"
        " inner join sanity2.diaryrewards d on u.diaryPoints >= d.diaryPointsReq "
        " where rankId != 1"
        " group by userId,displayName "
        " having max(u.diaryTierClaimed) < max(d.diaryTier)"
    )
    diaryPointDif = mycursor.fetchall()

    #print(diaryPointDif)

    if len(diaryPointDif) > 0:
        channel = await bot.fetch_channel(get_channel("rank-updates"))
        await channel.send("=================New DIARY claim MSG==================")

        for user in diaryPointDif:
            userId = user[0]
            claimedTiers = user[4]
            tiersToClaim = user[5]

            for x in range(tiersToClaim-claimedTiers):
                textdifficulty = get_diary_difficulty(claimedTiers+x+1)
                pointReward = getDiaryPointReward(claimedTiers+x+1)
                embed = embedVariable(f"{user[1]} - {textdifficulty} diary points",discord.Colour.yellow(),("Tiers claimed",str(claimedTiers)),("Tier to claim",claimedTiers+x+1),("Points",pointReward),("UserID",userId))

                view = diaryPointClaimerView()
                await channel.send(embed=embed,view=view)

@diaryPointsClaimer.before_loop  # REMOVES
async def before():
    await bot.wait_until_ready()
diaryPointsClaimer.start()

@tasks.loop(time=[time(hour=i, minute=5) for i in range(24)]) #check if people missing in db
async def checkUsersMissingDb():
    print("STARTING USER CHECK=")
    rank_id_list = get_all_ranks()
    #print(rank_id_list)
    db_rank_ids = [dbrank[2] for dbrank in rank_id_list]
    flex_rank_ids = [(dbrank[0],dbrank[2]) for dbrank in rank_id_list]
    #print(flex_rank_ids)

    user_ids_in_DB = [user[0] for user in get_all_users()]

    sanity = bot.get_guild(301755382160818177)

    for member in sanity.members:
        #print(member)
        if member.id in user_ids_in_DB:
            #print(member.display_name, member.id)
            #sync databse to what discord actually has
            #get highest rank of role -> check if matching db
            member_ranks = [rank.id for rank in member.roles]
            clan_ranks = [role for role in member_ranks if role in db_rank_ids]
            try:
                max_role_id = max([flex_id[0] for flex_id in flex_rank_ids if flex_id[1] in clan_ranks])
            except:
                max_role_id = 0

            if member.nick:
                memberDisplayName = member.nick
            else:
                memberDisplayName = member.display_name

            memberDisplayName = memberDisplayName.replace("`","").replace("\'","")
            user_data = getUserData(member.id)

            display_Name_DB = user_data[1]
            user_rank_indb = user_data[4]

            #print(display_Name_DB, user_rank_indb, max_role_id)

            if user_rank_indb != max_role_id:
                #update user rank to max_role_di
                updateUserRank(member.id,max_role_id)
                print(f"UPDATED {member.id} to {max_role_id}")
                insert_audit_Logs(userId=228143014168625153,actionType=8,actionDate=datetime.datetime.now(),actionNote=f"UPDATED {member.id} RANK from {user_rank_indb} to {max_role_id}",affectedUsers=f"{member.id}")

            if memberDisplayName != display_Name_DB:
                updateNick(member.id, memberDisplayName)
                print(f"UPDATED {member.id} to {memberDisplayName}")
                insert_audit_Logs(userId=228143014168625153, actionType=8, actionDate=datetime.datetime.now(),
                                  actionNote=f"UPDATED {member.id} NAME from {display_Name_DB} to {memberDisplayName}",
                                  affectedUsers=f"{member.id}")

            #print(F"HIGHEST RANK FOR {member.display_name} is {max_role_id}")

        else:
            member_ranks = [rank.id for rank in member.roles]
            if any(rank in db_rank_ids for rank in member_ranks):
                print(f"==========={member.display_name} MISSING FROM DB===========")
                add_user_todb(member.id,member.display_name,1,0,1,datetime.datetime.now(),"None")
                #DO SOMETHING!

    print("===FINISHED USER CHECK=")


@checkUsersMissingDb.before_loop  # REMOVES
async def before():
    await bot.wait_until_ready()
checkUsersMissingDb.start()


#### members ready for rankup!
@tasks.loop(time=[time(hour=18, minute=1)]) #
async def checkRankUps():
    print("START CheckRankUPS!")

    active_users_list = get_all_active_users()
    #get tuple of ranks!

    rank_list = get_all_ranks()
    #print(rank_list)

    #db_rank_ids = [dbrank[2] for dbrank in rank_id_list]
    flex_rank_ids = [(dbrank[0], dbrank[2]) for dbrank in rank_list]
    #print(flex_rank_ids)
    sanity = bot.get_guild(301755382160818177)
    #sanity = bot.get_guild(305380209366925312) #test

    #print(rank_list)
    rank_ids = [rank[0] for rank in rank_list]
    int_index = [i for i in range(len(rank_ids))]
    rank_Name = [rank[1] for rank in rank_list]
    rank_discordId = [rank[2] for rank in rank_list]
    rank_points = [rank[3] for rank in rank_list]
    rank_diaryReq = [rank[4] for rank in rank_list]
    rank_masterdiaryReq = [rank[5] for rank in rank_list]
    rank_maintenancePoints = [rank[6] for rank in rank_list]

    gracePeriod = fetchranksGracePeriod()
    now = datetime.datetime.now()
    #print(now > gracePeriod)
    #print(gracePeriod)

    channel = await bot.fetch_channel(get_channel("rank-updates"))

    #await channel.send("=================New Rank Update MSG==================")

    for member in active_users_list:
        #if member[1] == "Mike":
        member_disc = sanity.get_member(member[0])

        if member_disc:
            """print(f"{member_disc.display_name}")"""

            member_ranks = [rank.id for rank in member_disc.roles]
            #print(F"ROLES {member_ranks}")
            clan_ranks = [role for role in member_ranks if role in rank_discordId]
            if len(clan_ranks) != 0:

                #print(F"CLAN RANKS {clan_ranks}")
                #print(f"{member} FKS IT UP")
                max_role_id = max([flex_id[0] for flex_id in flex_rank_ids if flex_id[1] in clan_ranks])
                #======================
                #their CURRENT role!


                #Now for calculating actual rank
                points = member[5]
                currentRank = member[4]
                join_date = member[7]
                diaryPoints = member[11]
                masterdiaryPoints = member[12]
                #print(points, currentRank,join_date, diaryPoints, masterdiaryPoints)



                #print(((diaryPoints >= rank_diaryReq[x]) or (masterdiaryPoints >= rank_masterdiaryReq[0])))
                userPointsLast2Month = getUserPointsPrevious2Month(member_disc.id)
                if not userPointsLast2Month:
                    userPointsLast2Month = 0

                userPointsLastMonth = getUserPointsPreviousMonth(member_disc.id)
                if not userPointsLastMonth:
                    userPointsLastMonth = 0

                #print(f"last month pts {userPointsLastMonth}")
                userPointsThisMonth = getUserPointsThisMonth(member_disc.id)
                if not userPointsThisMonth:
                    userPointsThisMonth = 0

                #print(f"current month pts {userPointsThisMonth}")
                maxMonthPoints = max(userPointsThisMonth,userPointsLastMonth,userPointsLast2Month)
                #print(f"max {maxMonthPoints}")

                """print(f"{member_disc.display_name} points last month = {userPointsLastMonth}")"""
                calculated_rank = max([x for x in int_index if points >= rank_points[x] and ((diaryPoints >= rank_diaryReq[x]) or (masterdiaryPoints >= rank_masterdiaryReq[x])) and (maxMonthPoints >= rank_maintenancePoints[x])]) #
                #print(f"{member_disc.display_name} LONG STUFF {rank_list[calculated_rank][0]} ")

                #print("=================================")
                #if member_disc.id == 143306878779260929:
                    #print("TIIIIIIIZKU=====================")
                #print(f"embedVariable {member_disc.display_name} rank change MemberdiscID {member_disc.id} Previous rankID {max_role_id}) New rankID {rank_list[calculated_rank][0]}")

                #print(calculated_rank)
                if max_role_id > rank_list[calculated_rank][0] and now > gracePeriod and int(max_role_id) != 1: #DEMOTE
                    #PROPOSE RANK CHANGE

                    view = rankChangerView()

                    old_rank_name = [id[1] for id in rank_list if id[0] == max_role_id][0]
                    new_rank_name = [id[1] for id in rank_list if id[0] == rank_list[calculated_rank][0]][0]

                    embed = embedVariable(f"{member_disc.display_name} rank change",discord.Colour.yellow(),("MemberdiscID",member_disc.id), ("Previous rankID",max_role_id), ("New rankID", rank_list[calculated_rank][0]),("Old rank name",old_rank_name),("New rank name",new_rank_name))

                    await channel.send(embed=embed, view=view)
                elif max_role_id < rank_list[calculated_rank][0] and int(max_role_id) != 1: #PROMOTE
                    #PROPOSE RANK CHANGE
                    view = rankChangerView()

                    old_rank_name = [id[1] for id in rank_list if id[0] == max_role_id][0]
                    new_rank_name = [id[1] for id in rank_list if id[0] == rank_list[calculated_rank][0]][0]



                    embed = embedVariable(f"{member_disc.display_name} rank change",discord.Colour.yellow(),("MemberdiscID",member_disc.id), ("Previous rankID",max_role_id), ("New rankID", rank_list[calculated_rank][0]),
                                              ("Old rank name",old_rank_name),("New rank name",new_rank_name))
                    await channel.send(embed=embed, view=view)

            else:
                print(f"{member[0]} IS IN SERVer -> BUT NO ROLES")  # -> set to -1
                mycursor.execute(
                    f"update sanity2.users set isActive = 0, rankId = -1, leaveDate = '{datetime.datetime.now()}' where userId = {member[0]}"
                )
                db.commit()

                now = datetime.datetime.now()
                insert_audit_Logs(228143014168625153, 8, now, f"{member[0]} has left disc", member[0])

        else:
            print(f"{member[0]} IS MISSING FROM SANITY DISC SERVER") #-> set to -1
            mycursor.execute(
                f"update sanity2.users set isActive = 0, rankId = -1, leaveDate = '{datetime.datetime.now()}' where userId = {member[0]}"
            )
            db.commit()

            now = datetime.datetime.now()
            insert_audit_Logs(228143014168625153,8,now,f"{member[0]} has left disc",member[0])

    print("FINISHED checkRankUPS")


@checkRankUps.before_loop  # REMOVES
async def before():
    await bot.wait_until_ready()
checkRankUps.start()


@tasks.loop(time=[time(hour=18, minute=5)])
async def nitroPoints():
    # check if day = first of month
    dayOfMonth = datetime.datetime.now().day
    if dayOfMonth == 1:
        mycursor.execute(
            f"select * from sanity2.pointtracker p where notes = 'nitro points' and (MONTH(date) = month(now()) and year(date) = year(now()))"
        )
        nitroPointsGiven = mycursor.fetchall()
        print(f"LEN NITROPOINTS {len(nitroPointsGiven)}")

        if len(nitroPointsGiven) < 2:
            print("START NITRO POINTS!")


            sanity = bot.get_guild(301755382160818177)
            nitro_role = sanity.get_role(586808186003259404)
            role_member_ids = [member.id for member in nitro_role.members]
            #print(f"OLD ID LIST {role_member_ids}")

            clannies_names, new_id_list = turnListOfIds_into_names(role_member_ids)
            #print(f"NEW ID LIST {new_id_list}")

            for member_id in new_id_list:
                #give nitro points
                #print(member_id)
                update_user_points(member_id,50)
                insert_Point_Tracker(member_id,50,datetime.datetime.now(),"nitro points")

                #add points -> add into point tracker for each user

            insert_audit_Logs(userId=979856389868494898,actionType=8,actionDate=datetime.datetime.now(),actionNote="Added monthly nitro points!")
            print("FINISHED NITRO POINTS")

@nitroPoints.before_loop  # REMOVES
async def before():
    await bot.wait_until_ready()
nitroPoints.start()


class rankChangerView(View):  # for council / drop acceptors etc in #posted-drops
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction):
        mycursor.execute(
            "select discordRoleId,name from sanity2.roles where adminCommands = 1"
        )
        data = mycursor.fetchall()
        list = [i[0] for i in data]

        interaction_user_roleID_list = [role.id for role in interaction.user.roles]

        check = any(role in interaction_user_roleID_list for role in list)
        return check

    @button(label="Assign Rank", custom_id="acceptor-accept-button-4" ,style=discord.ButtonStyle.green, emoji="✅")
    async def assignrank(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        now = datetime.datetime.now()
        #title = int(str(embed_dict["title"]))
        memberId = int(embed_dict["fields"][0]["value"])
        previousRankId = int(embed_dict["fields"][1]["value"])
        newRankId = int(embed_dict["fields"][2]["value"])

        #print(memberId, previousRankId, newRankId)


        embed = discord.Embed.from_dict(embed_dict)

        embed.color = discord.Color.green()

        rank_ids = get_all_ranks()
        db_rank_ids = [dbrank[2] for dbrank in rank_ids]
        #print(db_rank_ids)

        sanity = bot.get_guild(301755382160818177)
        member = sanity.get_member(int(memberId))

        mycursor.execute(
            f"select discordRoleId from sanity2.ranks where id = {newRankId}"
        )
        New_rank_id = mycursor.fetchall()[0][0]
        new_role = sanity.get_role(int(New_rank_id))

        await member.add_roles(new_role)

        for rankId in db_rank_ids:
            # get role and remove from user
            role = sanity.get_role(rankId)
            member_roles = [role.id for role in member.roles]

            if rankId != new_role.id and rankId in member_roles:
                await member.remove_roles(role)

        insert_audit_Logs(interaction.user.id, 5, now, f"{member.display_name} updated rankid from {previousRankId} to {newRankId}",member.id)
        updateUserRank(member.id,newRankId)

        await interaction.message.edit(embed=embed,view=None)
        #await interaction.response.send_message("drop accepted and points given",)


    @button(label="Delete", custom_id="acceptor-decline-button-5", style=discord.ButtonStyle.danger, emoji="✖️")
    async def removeSubmission(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()


        embed = discord.Embed.from_dict(embed_dict)
        embed.color = discord.Color.red()

        await interaction.message.edit(embed=embed,view=None)
        #await interaction.response.send_message("The submission has been removed")


class Loops(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    @tasks.loop(time=[time(hour=i, minute=43) for i in range(24)])
    #@tasks.loop(minutes=2) #uncomment above
    async def sanityOverViewUpdater():  # update the sheets #users and #drops
        if db_user == "admin":
            print("==========UPDATING SHEETS STARTED==========")

            sheetlist = [("personalbests","submissionId"),("pointtracker","Id"),("users","userId"),("submissions","Id")]

            for item in sheetlist:
                sheetname = item[0]
                orderbyitem = item[1]

                try:
                    sa = gspread.service_account("sanitydb-v-363222050972.json")
                    sheet = sa.open(f"{sheetname}")
                    test = 1
                except gspread.exceptions.APIError:
                    test = 0
                    print("API ERROR UPDATING GSPREAD sheet")

                if test == 1:
                    mycursor.execute(
                        f"SELECT * from sanity2.{sheetname} order by {orderbyitem} desc limit 5000"
                    )
                    table = mycursor.fetchall()
                    descriptions = [[str(item[0]) for item in mycursor.description]]
                    actualTable = [list(tuple) for tuple in table]

                    datetime_to_string(actualTable)  # gspread doesnt like datetime.datetime obj -> converts to string
                    # print(test)
                    # print(F"====== DESCRIPTIONS==============")
                    # print(descriptions)

                    # print(F"======= TABLE =========")
                    # print(actualTable)

                    # Write the array to worksheet starting from the A2 cell
                    try:
                        workSheet = sheet.worksheet("Ark1")
                        workSheet.clear()
                        workSheet.update(values=descriptions, range_name='A1')  # insert description / header
                        workSheet.update(values=actualTable, range_name='A2')  # insert data
                    except:
                        print(f"{sheetname} update FAILED - API unavilable usually!!!")

                    try:
                        print(f"Sheet **{sheetname}** has been updated")
                    except:
                        print(f"Sheet **{sheetname}** has been updated")
                else:
                    print(f"sheet did not update - api error!")

            ##### update drops
            print("==========UPDATING SHEETS FINISHED==========")


    @sanityOverViewUpdater.before_loop  # REMOVES
    async def before():
        await bot.wait_until_ready()

    sanityOverViewUpdater.start()

def setup(bot):
    bot.add_cog(Loops(bot))