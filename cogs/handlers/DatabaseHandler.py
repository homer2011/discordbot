from discord.ext import commands
from discord import Embed
from ..util.CoreUtil import format_thousands
import mysql.connector
from mysql.connector import Error
from math import ceil
from dateutil import relativedelta
import datetime


def STARTup(test):  # setting
    if test == 2:  # if 2 = test
        db_user = "admin"
        token = ""
        testingservers = [305380209366925312, 301755382160818177] #sanity 301755382160818177
        bot_prefix = "!"
    else:
        db_user = "root"
        token = ""  # TWITCH BOT REAL #april_fools test
        testingservers = [305380209366925312] #[783483960889966613, 305380209366925312, 989596371931787265, 1123061497388597300]
        bot_prefix = "¤"

    return db_user, token, testingservers, bot_prefix

def create_server_connection(host_name, user_name, user_password, database_name=None):  # setup SQL
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=database_name
        )
        print(f"MySQL Database connection successful") #
    except Error as err:
        print(f"Error: '{err}'")

    return connection

db_user, token, testingservers, bot_prefix = STARTup(1)

db = create_server_connection("localhost", f"{db_user}", f"{db_user}") #live test
mycursor = db.cursor(buffered=True)  # connection to Mysql


def get_all_users():
    mycursor.execute(
        "select userId, displayName, mainRSN, altRSN, rankId, points, isActive, joinDate, leaveDate, referredBy, birthday "
        "from sanity2.users"
    )

    sql_users_list = mycursor.fetchall()

    return sql_users_list

def get_all_active_users():
    mycursor.execute(
        "select userId, displayName, mainRSN, altRSN, rankId, points, isActive, joinDate, leaveDate, referredBy, birthday, diaryPoints, masterDiaryPoints, diaryTierClaimed "
        "from sanity2.users where isActive = 1"
    )

    sql_users_list = mycursor.fetchall()

    return sql_users_list

def get_role(roleName: str):
    mycursor.execute(
        f"select * from sanity2.roles where name = '{roleName}'"
    )
    output = mycursor.fetchall()
    if output:
        return output[0][1]
    else:
        return None

def get_all_ranks(name : str = None):
    if name:
        mycursor.execute(
            "select id,name,discordRoleId,pointRequirement,diaryPointRequirement,masterDiaryRequirement,maintenancePoints "
            "from sanity2.ranks "
            f"where name like \'{name}\'"
        )
    else:
        mycursor.execute(
            "select id,name,discordRoleId,pointRequirement,diaryPointRequirement,masterDiaryRequirement,maintenancePoints "
            "from sanity2.ranks "
        )

    role_id_list = mycursor.fetchall()

    return role_id_list

def get_channel(name : str):
    mycursor.execute(
        f"select * from sanity2.channels where name like \'{name}\' "
    )

    channel_info = mycursor.fetchall()

    return channel_info[0][0]


def get_user_points(user_id):
    ### CHECK if user is in clan
    mycursor.execute(
        f"select points from sanity2.users where userId = {user_id}"
    )
    points = mycursor.fetchall()

    if len(points) > 0:
        #print(f"{user_id} HAS {points[0][0]} points")
        return int(points[0][0])
    else:
        #print(f"{user_id} NEGATIVE")
        print(f"{user_id} is NOT in the database")
        return None

def get_user_points_april_fools(user_id):
    ### CHECK if user is in clan
    mycursor.execute(
        f"select points from sanityApril.users where userId = {user_id}"
    )
    points = mycursor.fetchall()

    if len(points) > 0:
        #print(f"{user_id} HAS {points[0][0]} points")
        return int(points[0][0])
    else:
        #print(f"{user_id} NEGATIVE")
        print(f"{user_id} is NOT in the database")
        return None

def update_user_points(userId : int, pointGain : int):
    currentPoints = get_user_points(userId)
    #print(f"{userId} has {currentPoints} points UPDATEUSERPOINTS")
    if currentPoints+1 > 0:
        new_points = int(currentPoints + pointGain)
        #print(f"NEW POIUNTS {new_points}")

        mycursor.execute(
            f"update sanity2.users set points = {new_points} where userId = {userId} "
        )

        db.commit()

def insert_drop_into_submissions(userId : int, typeId : int, status : int, participants, value : int, imageUrl : str, submittedDate, notes : str):
    mycursor.execute(
        "insert into sanity2.submissions (userId, typeId, status, participants, value, imageUrl, submittedDate, notes)"
        "VALUES (%s,%s,%s,%s,%s,%s,%s, %s)",
        (userId, typeId, status, participants, value, imageUrl, submittedDate, notes)
    )

    db.commit()

    return mycursor.lastrowid

def update_drop_submission(Id : int, reviewedBy : int, reviewDate, status : int, bingoVal : int = None, reviewNote = None, messageUrl:str =None):
    if not bingoVal:
        bingoVal = 0

    if reviewNote:
        mycursor.execute(
            f"update sanity2.submissions set reviewedBy={reviewedBy}, reviewedDate = '{reviewDate}', status={status}, bingo = {bingoVal}, reviewNote = {reviewNote} where Id = {Id}"
        )
    else:
        mycursor.execute(
            f"update sanity2.submissions set reviewedBy={reviewedBy}, reviewedDate = '{reviewDate}', status={status}, bingo = {bingoVal} where Id = {Id}"
        )

    if messageUrl:
        mycursor.execute(
            f"update sanity2.submissions set messageUrl = '{messageUrl}' where Id = {Id}"
        )

    db.commit()

def updateDropStatus(dropId : int , status : int, participants : str):
    mycursor.execute(
        f"update sanity2.submissions set status={status}, participants = '{participants}' where Id = {dropId}"
    )

    db.commit()

def updateDropStatusONLY(dropId : int, status : int):
    mycursor.execute(
        f"update sanity2.submissions set status={status} where Id = {dropId}"
    )

    db.commit()

def get_drop_names():
    mycursor.execute(
        f"select * from sanity2.drops"
    )

    list = mycursor.fetchall()
    name_list = [drop[1] for drop in list]

    return name_list

def get_bingo_drop_names():
    mycursor.execute(
        f"select * from sanity2.bingodrops"
    )

    list = mycursor.fetchall()
    name_list = [drop[1] for drop in list]

    return name_list

def turnListOfIds_into_names(listOfIds):
    sql_format = f"({','.join(str(clannie) for clannie in listOfIds)})"
    mycursor.execute(
        f"select * from sanity2.users where userId in {str(sql_format)}"
    )
    sql_clannies_list = mycursor.fetchall()

    clannies_names = ', '.join([tupleObj[1] for tupleObj in sql_clannies_list])
    clannie_ids = [tupleObj[0] for tupleObj in sql_clannies_list]

    return clannies_names, clannie_ids

def add_boss(name : str, imageUrl : str = None):
    mycursor.execute(
        f"insert into sanity2.bosses (name, imageUrl)"
        f"Values (%s, %s)",
        (name, imageUrl)
    )
    db.commit()


def update_boss_url(name : str, imageUrl : str = None):
    mycursor.execute(
        f"update sanity2.bosses set imageUrl = '{imageUrl}' where name = '{name}'",
    )
    db.commit()

def add_drop(name : str, value : int = None):
    mycursor.execute(
        f"insert into sanity2.drops (name, value)"
        f"Values (%s, %s)",
        (name, value)
    )
    db.commit()

def get_adminCommands_roles():
    mycursor.execute(
        "select * from sanity2.roles where adminCommands = 1"
    )
    table = mycursor.fetchall()

    return table


def insert_audit_Logs(userId, actionType, actionDate, actionNote = None, affectedUsers = None):
    mycursor.execute(
        f"insert into sanity2.auditlogs (userId, affectedUsers, actionType, actionNote, actionDate)"
        f"Values (%s, %s, %s, %s, %s)",
        (userId, affectedUsers, actionType, actionNote, actionDate)
    )

    db. commit()


def insert_Point_Tracker(userId : int, points : int, date, notes = None, dropId = None):
    mycursor.execute(
        f"insert into sanity2.pointtracker (userId, points, date, notes, dropId)"
        f"Values (%s, %s, %s, %s, %s)",
        (userId, points, date, notes, dropId)
    )

    db.commit()


def get_bosses():
    mycursor.execute(
        "select * from sanity2.bosses"
    )
    table = mycursor.fetchall()
    boss_names = [boss[1] for boss in table]
    boss_ids = [boss[0] for boss in table]

    return boss_names, boss_ids

def add_channel(channelName : str, channelId : int):
    mycursor.execute(
        f"insert into sanity2.channels (id, name)"
        f"Values (%s, %s)",
        (channelId, channelName)
    )
    db.commit()


def add_user_todb(userId : int, displayName : str, rankId : int, points : int, isActive : int, joinDate, referredBy : str):
    displayName = displayName.replace("`","")

    mycursor.execute(
        f"insert into sanity2.users (userId, displayName, rankId, points, isActive, joinDate, referredBy) "
        f" Values (%s, %s, %s, %s, %s, %s, %s)",
        (userId, displayName, rankId, points, isActive, joinDate, referredBy)
    )

    db.commit()


def insert_Personal_Best(userId : int, members, bossId : int, status :int,
                         scale : int, time, submissionDate, imageUrl):
    mycursor.execute(
        f"insert into sanity2.personalbests (submitterUserId, members, status, bossId, scale, time, submittedDate, imageUrl)"
        f"Values (%s, %s, %s, %s, %s, %s, %s, %s)",
        (userId, members, status, bossId, scale, time, submissionDate, imageUrl)
    )

    pbId = mycursor.lastrowid

    db.commit()

    return pbId

def update_Personal_best(submissionId : int, status : int, imageUrl : str = None):
    if imageUrl:
        mycursor.execute(
            f"update sanity2.personalbests set status = {status}, imageUrl = '{imageUrl}' where submissionId = {submissionId}"
        )
    else:
        mycursor.execute(
            f"update sanity2.personalbests set status = {status} where submissionId = {submissionId}"
        )

    db.commit()

def accept_decline_personalBest(submissionId : int, status:int, reviewedBy : int, reviewedDate, reviewNote : str = None):
    mycursor.execute(
        f"update sanity2.personalbests set status = {status}, reviewedBy = {reviewedBy}, reviewedDate = '{reviewedDate}' where submissionId = {submissionId} "
    )

    db.commit()

def bingoModeCheck():
    mycursor.execute(
        "select * from sanity2.miscmodes where modeName = 'bingo'"
    )

    table = mycursor.fetchall()[0][1]


    return table

def enableCompMode(on_or_off : int):
    mycursor.execute(
        f"update sanity2.miscmodes set modeStatus = {on_or_off} where modeName = 'bingo'"
    )
    db.commit()

def getrsn(userId, main):
    mycursor.execute(
        f"select * from sanity2.users where userId = {userId}"
    )

    table = mycursor.fetchall()

    if main == 1:
        old_rsn = table[0][2]
    else:
        old_rsn = table[0][3]

    return old_rsn

def updatersn(userId : int, main : int, rsn:str):
    if main == 1:
        mycursor.execute(
            f"update sanity2.users set mainRSN = '{rsn}' where userId = {userId}"
        )
    else:
        mycursor.execute(
            f"update sanity2.users set altRSN = '{rsn}' where userId = {userId}"
        )

    db.commit()

def updateGracePeriod(datetimethingy):
    mycursor.execute(
        f"update sanity2.ranksgraceperiod set gracePeriod = '{datetimethingy}'"
    )

    db.commit()

def fetchranksGracePeriod():
    mycursor.execute(
        "select * from sanity2.ranksgraceperiod"
    )
    table = mycursor.fetchall()

    return table[0][0]


def pageinatorGetPages(rowName, rowId):
    mycursor.execute(
        f"select * from sanity2.users where {rowName} > 0 and isActive = 1 order by {rowName} desc"
    )
    table = mycursor.fetchall()
    numMembersInTable = len(table)
    # print(numMembersInTable)
    # print(table[0])

    test = []

    multiplierx25 = 0
    for y in range(ceil(len(table) / 25)):
        stringf = ""
        for x in range(25):
            if numMembersInTable > x + multiplierx25:
                # print(x+multiplierx25)
                stringf += f"{x + multiplierx25 + 1}. {table[x + multiplierx25][1]} - `{format_thousands(table[x + multiplierx25][rowId])}`\n"
                # print(table[x+multiplierx25])
            else:
                # print(f"DONE AT {x+multiplierx25}")
                break

        test.append(Embed(title=f"Sanity Point leaderboard - {y + 1}", description=f"**{rowName} Leaderboard** \n\n {stringf}"))

        multiplierx25 += 25

    return test


def getPointsMonthly(month, year):
    mycursor.execute(
        f"select u.userId, u.displayName, CASE 	when sum(points) > 0 then sum(points) 	else 0 END as 'points'"
        f" from (select u.userId, u.displayName from sanity2.users u where u.isActive = 1) u"
        f" left join (select p.userId,p.points from sanity2.pointtracker p where month(p.date) = {month} and year(p.date) = {year}) p on p.userId = u.userId"
        f" group by u.userId, u.displayName order by sum(points) desc"
    )
    table = mycursor.fetchall()

    return table

def getUserData(userId):
    mycursor.execute(
        f"select * from sanity2.users where userId = {userId}"
    )

    table = mycursor.fetchall()

    try: #if nothing
        data = table[0]
    except:
        data = []

    return data

def updateUserRank(userId : int , rankId : int):
    if rankId == 0:
        mycursor.execute(
            f"update sanity2.users set rankId = {rankId}, isActive = 0 where userId = {userId}"
        )
    else:
        mycursor.execute(
            f"update sanity2.users set rankId = {rankId}, isActive = 1 where userId = {userId}"
        )

    db.commit()

def updateUserId(old,new):
    mycursor.execute(
        f"update sanity2.users set userId = {new} where userId = {old}"
    )

    db.commit()

    mycursor.execute(
        f"update sanity2.pointtracker set userId = {new} where userId = {old}"
    )
    db.commit()

    mycursor.execute(
        f"update sanity2.personalbests set members = replace(members,'{old}','{new}') where members like '%{old}%'"
    )

    db.commit()

def getBingoBoard():
    mycursor.execute(
        "select * from sanity2.bingoboard where id = 1"
    )
    table = mycursor.fetchall()

    url = table[0][1]
    width = table[0][2]
    height = table[0][3]

    return url, width, height

def updateBingoBoard(gsheetsUrl, width : int = None, height : int = None):
    if width:
        width = f"and width = {width}"
    else:
        width = ""

    if height:
        height = f"and width = {height}"
    else:
        height = ""

    mycursor.execute(
        f"update sanity2.bingoboard set sheetsUrl = '{gsheetsUrl}' {width}  {height} where id = 1"
    )

    db.commit()

def setUserDiaryPoints(userId : int, diaryPoints : int, masterDiaryPoints : int):
    mycursor.execute(
        f"update sanity2.users set diaryPoints = {diaryPoints}, masterDiaryPoints = {masterDiaryPoints} where userId = {userId}"
    )

    db.commit()


def getMemberAge(userId: int):
    #print("hello world")

    mycursor.execute(f"select joinDate from sanity2.users where userId = {userId}")

    dateTimeObj = mycursor.fetchone()[0]
    now = datetime.datetime.now()
    #print(f"DATTIMEOBJ {dateTimeObj} ----- now {now}")

    relativeDif = relativedelta.relativedelta(now,dateTimeObj)
    #print(relativeDif)

    if dateTimeObj is None:
        return None
    else:
        return relativeDif

class DBHandler(commands.Cog):
    def __init__(self, bot):
        self.client = bot


    @commands.command(hidden=True)
    async def auditlogger(self, ctx):
        from bot import bot
        audit_log_id = get_channel("audit-log")
        audit_log_channel = await bot.fetch_channel(audit_log_id)
        await audit_log_channel.send("lol")


def setup(bot):
    bot.add_cog(DBHandler(bot))
