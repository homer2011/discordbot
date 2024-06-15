import discord
from discord.ext import commands
from ..handlers.DatabaseHandler import mycursor, setUserDiaryPoints
from ..util.CoreUtil import get_scale_text, get_diary_difficulty

"""
Checks to do
 1. Global check -> check each users submission -> assign points
 2. On submissionAccept check -> check participants. If time < current best time (if any) -> assign points
 3. diary points and master diary points
"""

def maxDiaryPoints():
    mycursor.execute(
        f"select sum(CASE when maxDifficulty = 1 then 1 when maxDifficulty = 2 then 3 when maxDifficulty = 3 then 6 when maxDifficulty = 4 then 10 when maxDifficulty = 5 then 15 END) from sanity2.diarytimes d"
    )
    data = mycursor.fetchall()

    mycursor.execute(
        f"select count(*) from sanity2.diarytimes where maxDifficulty = 5"
    )
    masterDiaryCount = mycursor.fetchall()[0][0]

    return data[0][0], masterDiaryCount


def getUserPb(userId : int, bossId : int, scale : int):
    mycursor.execute(
        f"select time, imageUrl  from sanity2.personalbests where members like '%{userId}%' "
        f" and (status = 2 or status = 6) and bossId = {bossId} and scale = {scale} "
        f" order by cast(substring_index(time, ':',1) as UNSIGNED) asc, substring_index(time, ':',-1) asc"
        f" limit 1"
    )

    data = mycursor.fetchall()

    if len(data) > 0:
        #print(f"DATA {data} from getUserPb")
        time = data[0][0]
        imageUrl = data[0][1]

        return time, imageUrl
    else:
        return None, None


def getDiaryTier(currentPts : int):
    mycursor.execute(
        f"SELECT diaryTier FROM sanity2.diaryrewards d WHERE diaryPointsReq <= {currentPts} ORDER BY points desc  limit 1"
    )
    data = mycursor.fetchall()
    if data:
        tier = data[0][0]
    else:
        tier = "0"
    return tier

def checkUserDiary(userId : int):
    mycursor.execute(
        "select * from sanity2.diarytimes "
        " inner join sanity2.bosses  on bosses.id =  diarytimes.bossId "
    )
    diaryTimes = mycursor.fetchall()

    #print(f"DIARY TIMES BIG BIG {diaryTimes}")

    userDiaryPoints = 0
    masterDiaryPoints = 0
    diaryMsg = ""

    for diary in diaryTimes:
        diaryPointGain = 0
        masterDiaryGain = 0
        diaryMsg_V0 = ""

        #print(f"DIARY {diary}")
        bossId = diary[1]
        scale = diary[2]
        maxDif = diary[3]
        time, imageUrl = getUserPb(userId, bossId, scale)

        if time and imageUrl:
            scale_text = get_scale_text(scale)

            #print(time, imageUrl)
            player_minutes = int(time.split(":")[0])
            player_seconds = float(time.split(":")[1])
            #print(f"MINUTES: {player_minutes} AND SECONDS {player_seconds}")
            #print(f"PLAYER MIN {player_minutes}")
            #print(f"DIARY MIN {int(diary[4].split(':')[0])}")
            #print(f"{diary[10]} DAT GUT STUFF {player_seconds+(60*(player_minutes-int(diary[4].split(':')[0])))}")
            if maxDif >= 1:
                if player_minutes <= int(diary[4].split(":")[0]) and (player_seconds+(60*(player_minutes-int(diary[4].split(":")[0])))) <= float(diary[4].split(":")[1]): #easy diary
                    diaryPointGain = 1
                    diaryMsg_V0 = f"<:easy:1179474217046114325> **{diary[10]}** - **{scale_text}** - {time} - {get_diary_difficulty(1)} - [url]({imageUrl}) \n\n"

            if maxDif >= 2:
                if player_minutes <= int(diary[5].split(":")[0]) and (player_seconds+(60*(player_minutes-int(diary[5].split(":")[0])))) <= float(diary[5].split(":")[1]): #medium diary
                    diaryPointGain = 3
                    diaryMsg_V0 = f"<:medium:1179474223052361760> **{diary[10]}** - **{scale_text}** - {time} - {get_diary_difficulty(2)} - [url]({imageUrl}) \n\n"

            if maxDif >= 3:
                if player_minutes <= int(diary[6].split(":")[0]) and (player_seconds+(60*(player_minutes-int(diary[6].split(":")[0])))) <= float(diary[6].split(":")[1]): #hard diary
                    diaryPointGain = 6
                    diaryMsg_V0 = f"<:hard:1179474324730691675> **{diary[10]}** - **{scale_text}** - {time} - {get_diary_difficulty(3)} - [url]({imageUrl}) \n\n"

            if maxDif >= 4:
                if player_minutes <= int(diary[7].split(":")[0]) and (player_seconds+(60*(player_minutes-int(diary[7].split(":")[0])))) <= float(diary[7].split(":")[1]): #elite diary
                    diaryPointGain = 10
                    diaryMsg_V0 = f"<:elite:1179474253289095209> **{diary[10]}** - **{scale_text}** - {time} - {get_diary_difficulty(4)} - [url]({imageUrl}) \n\n"

            if maxDif >= 5:
                if player_minutes <= int(diary[8].split(":")[0]) and (player_seconds+(60*(player_minutes-int(diary[8].split(":")[0])))) <= float(diary[8].split(":")[1]): #master diary
                    diaryPointGain = 15
                    masterDiaryGain = 1
                    diaryMsg_V0 = f"<:master:1179474251854651442> **{diary[10]}** - **{scale_text}** - {time} - {get_diary_difficulty(5)} - [url]({imageUrl}) \n\n"

            userDiaryPoints += diaryPointGain
            masterDiaryPoints += masterDiaryGain
            diaryMsg += diaryMsg_V0

    setUserDiaryPoints(userId,userDiaryPoints,masterDiaryPoints)


    mycursor.execute(
        f"select displayName from sanity2.users where userId = {userId}"
    )
    displayName = mycursor.fetchall()[0][0]

    maxPoints, numMasterDiaries = maxDiaryPoints()


    currentDiaryTier = getDiaryTier(userDiaryPoints)

    embed = discord.Embed(
        title=f"{displayName} Diary {userDiaryPoints}/{maxPoints} - Tier {currentDiaryTier}",
        description=diaryMsg
    )

    return embed, userDiaryPoints, masterDiaryPoints


class DiaryHandler(commands.Cog):
    def __init__(self, bot):
        self.client = bot



def setup(bot):
    bot.add_cog(DiaryHandler(bot))


