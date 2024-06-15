import asyncio

import discord.utils
import gspread
import requests
from PIL import ImageFont, Image, ImageDraw, ImageOps
from discord.ext import commands, tasks, bridge, pages
from discord import Embed
from bot import bot
import datetime
from datetime import timedelta
from io import StringIO
import os
import numpy as np
from .admin import datetime_to_string
from ..handlers.DatabaseHandler import get_all_users, get_all_ranks, get_user_points, testingservers, insert_audit_Logs, \
    getrsn, updatersn, \
    pageinatorGetPages, getPointsMonthly, getBingoBoard, getMemberAge, mycursor, getUserData, db, \
    turnListOfIds_into_names, get_user_points_april_fools, bingoModeCheck
from ..handlers.EmbedHandler import descriptionOnlyEmbed
from ..handlers.diaryHandler import checkUserDiary, maxDiaryPoints
from ..util.CoreUtil import format_thousands, get_scale_text
from ..handlers.birthdayshit import getBirthdays
from ..handlers.PbHighscores import getHiscorePbsIgnoreUrl, getBossInfo
from discord.ext.commands import has_any_role, is_owner
from math import ceil, floor
from io import BytesIO
from dateutil import relativedelta
#from selenium import webdriver
#from selenium.webdriver.chrome.options import Options
#from selenium.webdriver.chrome.service import Service

def get_text_width(text, font):
    """Calculates the width of a text string rendered with the given font."""

    # Create a temporary image to measure the text
    test_img = Image.new('RGB', (1, 1))
    test_draw = ImageDraw.Draw(test_img)

    # Get text dimensions using the provided font
    return test_draw.textsize(text, font)[0]

def make_circular(image):
    """Converts a square PIL Image into a transparent circular one."""

    # Create a new RGBA image with transparent background
    output = Image.new("RGBA", image.size, (0, 0, 0, 0))

    # Draw a white filled circle on a mask
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + image.size, fill=255)

    # Paste the original image onto the new one, using the mask
    output.paste(image, (0, 0), mask=mask)

    return output

def ifPlayerInDB(rsn:str):
    mycursor.execute(
        f"select * from sanity2.bingobosskc where RSN = '{rsn}'"
    )
    data = mycursor.fetchall()

    if len(data) == 0:
        return None
    else:
        return True

def getBossesNameFromTable():
    mycursor.execute(
        "select * from sanity2.bingobosskc"
    )
    mycursor.fetchall()
    description = [header[0] for header in mycursor.description]
    return description

def addPlayerToTable(rsn:str):
    mycursor.execute(
        f"INSERT INTO sanity2.bingobosskc(RSN) VALUES ('{rsn}')"
    )
    db.commit()

def updatebingobossEhb(rsn:str, boss:str, new_ehb:int):
    mycursor.execute(
        f"update sanity2.bingobosskc set {boss} = {new_ehb} where RSN ='{rsn}'"
    )
    db.commit()

def getRelevantBosses(limit : int = None):
    if not limit:
        limit = 9999

    mycursor.execute(
        f"select bossId,`scale` from sanity2.personalbests group by 1,2 order by 1 asc,2 asc limit {limit}"
    )
    bossesNscales = mycursor.fetchall()

    return bossesNscales


def createPageInatorPbs(data, scale:int):
    test = []
    multiplierx25 = 0
    if len(data) > 0:
        for y in range(ceil(len(data) / 25)):
            stringf = ""
            for x in range(25):
                if len(data) > x + multiplierx25:
                    # print(x+multiplierx25)
                    membernames, memberids = turnListOfIds_into_names(str(data[x + multiplierx25][2]).split(","))
                    timestamp = data[x+multiplierx25][4]
                    proof = data[x+multiplierx25][1]
                    new_string = f"{x + multiplierx25 + 1}. `{data[x + multiplierx25][0]}` - `{membernames}` - <t:{round(timestamp.timestamp())}:R> - [Proof]({proof}) \n"

                    if len(new_string) + len(stringf) < 4000:
                        stringf += new_string
                    else:
                        multiplierx25 -= 1
                    # print(table[x+multiplierx25])
                    # print(stringf)
                else:
                    # print(f"DONE AT {x+multiplierx25}")
                    break

            test.append(
                Embed(title=f"{data[0][5]} pbs - Page {y + 1}",
                      description=f"{get_scale_text(scale)} {data[0][5]} Personal bests! \n\n {stringf}"))

            multiplierx25 += 25
    else:
        test.append(
            "NONE"
        )

    return test


def createFirstPageStats(month:int, year:int, title:str, subtitle:str = None):
    #points gained
    #most common drops
    #most gained player

    #points status
    mycursor.execute(
        f"select sum(value) as 'Total value',count(*) as 'Number of drops' from sanity2.submissions s where status = 2 and month(submittedDate) = {month} and year(submittedDate) = {year}"
    )
    data = mycursor.fetchall()
    total_points_gained = data[0][0]
    number_of_drops = data[0][1]

    # 3 most common drops
    mycursor.execute(
        f"select notes,sum(value) as 'Total value',count(*) as 'Number of drops' from sanity2.submissions s where status = 2 and month(submittedDate) = {month} and year(submittedDate) = {year}  "
        f" group by notes order by sum(value) DESC limit 3"
    )
    Three_most_common_dropsdata = mycursor.fetchall()

    most_common_text = ""
    count = 1
    for drop in Three_most_common_dropsdata:
        most_common_text += f"{count}. `{drop[0]}` - pts: `{drop[1]}`\n"
        count += 1

    mycursor.execute(
        f"select userId,sum(value) as 'Total value',count(*) as 'Number of drops' from sanity2.submissions s "
            f" where status = 2 and month(submittedDate) = {month} and year(submittedDate) = {year}"
            f" group by userId order by sum(value) DESC limit 3"
    )
    top_three_players_by_amount = mycursor.fetchall()
    most_gained_players = ""
    count = 1
    for player in top_three_players_by_amount:
        nickName = getUserData(player[0])[1]
        most_gained_players += f"{count}. {nickName} - `{player[1]}`\n"
        count += 1

    mycursor.execute(
        f"select userId,sum(value) as 'Total value',count(*) as 'Number of drops' from sanity2.submissions s "
            f" where status = 2 and month(submittedDate) = {month} and year(submittedDate) = {year}"
            f" group by userId order by count(*) DESC limit 3"
    )
    top_three_players_by_count = mycursor.fetchall()
    top_three_players_by_count_text = ""
    count = 1
    for player in top_three_players_by_count:
        nickName = getUserData(player[0])[1]
        top_three_players_by_count_text += f"{count}. {nickName} - `{player[2]}`\n"
        count += 1

    embed = Embed(
        title=f"{title}",
        description=f"**Misc Stats**\n\n"
                    f"**Total points gained** - `{total_points_gained}`\n"
                    f"**Number of drops submitted** - `{number_of_drops}`\n\n"
                    f"**Most common drops** \n {most_common_text} \n"
                    f"**Most points submitted** \n {most_gained_players} \n"
                    f"**Most drops submitted (by count)** \n {top_three_players_by_count_text} \n\n For stats of top submitted items, use the next pages!"
    )

    return embed


def getMonthlyDropStatus(month:int, year:int):
    mycursor.execute(
        f"select notes,sum(value) as 'Total value',count(*) as 'Number of drops' from sanity2.submissions s where status = 2 and month(submittedDate) = {month} and year(submittedDate) = {year}  "
        f" group by notes order by sum(value) DESC"
    )
    data = mycursor.fetchall()

    return data


def getStarRanksPointsbyMonth(month:int, year:int):
    mycursor.execute(
        f"select u.userId, u.displayName, CASE 	when sum(points) > 0 then sum(points) 	else 0 END as 'points'"
        f" from (select u.userId, u.displayName from sanity2.users u where u.isActive = 1 and u.rankId in (select id from sanity2.ranks where maintenancePoints > 0)) u"
        f" left join (select p.userId,p.points from sanity2.pointtracker p where month(p.date) = {month} and year(p.date) = {year}) p on p.userId = u.userId"
        f" group by u.userId, u.displayName order by sum(points) desc"
    )
    starRanksData = mycursor.fetchall()

    return starRanksData

def getNonStarRanksPointsbyMonth(month:int, year:int):
    mycursor.execute(
        f"select u.userId, u.displayName, CASE 	when sum(points) > 0 then sum(points) 	else 0 END as 'points'"
        f" from (select u.userId, u.displayName from sanity2.users u where u.isActive = 1 and u.rankId in (select id from sanity2.ranks where maintenancePoints <= 0)) u"
        f" left join (select p.userId,p.points from sanity2.pointtracker p where month(p.date) = {month} and year(p.date) = {year}) p on p.userId = u.userId"
        f" group by u.userId, u.displayName order by sum(points) desc"
    )
    nonStarRankData = mycursor.fetchall()

    return nonStarRankData

def createPageInator3Wide(data,title : str, subtitle : str):
    test = []
    multiplierx25 = 0
    if len(data) > 0:
        for y in range(ceil(len(data) / 25)):
            stringf = ""
            for x in range(25):
                if len(data) > x + multiplierx25:
                    # print(x+multiplierx25)
                    stringf += f"{x + multiplierx25 + 1}. **{data[x + multiplierx25][0]}** - {data[x + multiplierx25][1]} - `{format_thousands(data[x + multiplierx25][2])}`\n"
                    # print(table[x+multiplierx25])
                    # print(stringf)
                else:
                    # print(f"DONE AT {x+multiplierx25}")
                    break

            test.append(
                Embed(title=f"{title} - {y + 1}",
                      description=f"{subtitle} \n\n {stringf}"))

            multiplierx25 += 25
    else:
        test.append(
            "NONE"
        )

    return test



def createPageInator(data,title : str, subtitle : str):
    test = []
    multiplierx25 = 0
    if len(data) > 0:
        for y in range(ceil(len(data) / 25)):
            stringf = ""
            for x in range(25):
                if len(data) > x + multiplierx25:
                    # print(x+multiplierx25)
                    stringf += f"{x + multiplierx25 + 1}. {data[x + multiplierx25][1]} - `{format_thousands(data[x + multiplierx25][2])}`\n"
                    # print(table[x+multiplierx25])
                    # print(stringf)
                else:
                    # print(f"DONE AT {x+multiplierx25}")
                    break

            test.append(
                Embed(title=f"{title} - {y + 1}",
                      description=f"{subtitle} \n\n {stringf}"))

            multiplierx25 += 25
    else:
        test.append(
            "NONE"
        )

    return test


def countrySearcher(ctx : discord.AutocompleteContext):

    countryCodesISO = ["AF","AX","AL","DZ","AS","AD","AO","AI","AQ","AG","AR","AM","AW","AU","AT","AZ","BS","BH","BD","BB","BY","BE","BZ","BJ","BM","BT","BO","BQ","BA","BW","BV","BR","IO","BN","BG","BF","BI","CV","KH","CM","CA","KY","CF","TD","CL","CN","CX","CC","CO","KM","CD","CG","CK","CR","CI","HR","CU","CW","CY","CZ","DK","DJ","DM","DO","EC","EG","SV","GQ","ER","EE","SZ","ET","FK","FO","FJ","FI","FR","GF","PF","TF","GA","GM","GE","DE","GH","GI","GR","GL","GD","GP","GU","GT","GG","GN","GW","GY","HT","HM","VA","HN","HK","HU","IS","IN","ID","IR","IQ","IE","IM","IL","IT","JM","JP","JE","JO","KZ","KE","KI","KP","KR","KW","KG","LA","LV","LB","LS","LR","LY","LI","LT","LU","MO","MK","MG","MW","MY","MV","ML","MT","MH","MQ","MR","MU","YT","MX","FM","MD","MC","MN","ME","MS","MA","MZ","MM","NA","NR","NP","NL","NC","NZ","NI","NE","NG","NU","NF","MP","NO","OM","PK","PW","PS","PA","PG","PY","PE","PH","PN","PL","PT","PR","QA","RE","RO","RU","RW","BL","SH","KN","LC","MF","PM","VC","WS","SM","ST","SA","SN","RS","SC","SL","SG","SX","SK","SI","SB","SO","ZA","GS","SS","ES","LK","SD","SR","SJ","SE","CH","SY","TW","TJ","TZ","TH","TL","TG","TK","TO","TT","TN","TR","TM","TC","TV","UG","UA","AE","GB","UM","US","UY","UZ","VU","VE","VN","VG","VI","WF","EH","YE","ZM","ZW"]

    return [
        country for country in countryCodesISO if (ctx.value.lower() in country.lower())
    ]


def getRolesWithIcon():
    mycursor.execute(
        f"select * from sanity2.roles where hasRoleIcon = 1"
    )
    data = mycursor.fetchall()

    roleIds = [role[1] for role in data]

    return roleIds

def get_drop_url(dropId:int):
    mycursor.execute(
        f"select messageUrl,Id from sanity2.submissions where Id = {dropId}"
    )
    url = mycursor.fetchall()
    return url

def get_recent_drops(userId:int):
    mycursor.execute(
        f"select Id, userId, points, dropId, notes, date from sanity2.pointtracker where userId = {userId} order by Id desc limit 10"
    )

    data = mycursor.fetchall()

    return data

class User(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    all_ranks = get_all_ranks()
    rank_ids = [rank[2] for rank in all_ranks]

    @commands.command(aliases=["Points"])
    @has_any_role(*rank_ids)
    async def points(self, ctx, user : discord.Member = None):
        """ shows the users points"""
        if not user:
            user = ctx.author

        points = get_user_points(user.id)
        #april_fools
        #points = get_user_points_april_fools(user.id)
        embed = descriptionOnlyEmbed(f"**{user.display_name}** currently has `{format_thousands(points)}` clan points")
        await ctx.message.delete()
        await ctx.send(embed=embed)

    @discord.slash_command(guild_ids=testingservers, name="changersn", description="Change your main or alt!")
    @has_any_role(*rank_ids)
    async def changersn(self, ctx: discord.ApplicationContext,
                         main_or_alt: discord.Option(str, description="pick one", choices=["Main","Alt"]),
                         new_rsn: discord.Option(str, description="put in the new rsn", max_length=40)):

        if main_or_alt == "Main":
            main = 1
        else:
            main = 0

        prev_rsn = getrsn(ctx.author.id,main)
        updatersn(ctx.author.id,main,new_rsn)

        insert_audit_Logs(ctx.author.id, 2, datetime.datetime.now(), f"Changed rsn on {main_or_alt} from {prev_rsn} to {new_rsn}")

        embed = descriptionOnlyEmbed(f"changersn on {main_or_alt} from {prev_rsn} to {new_rsn}")
        await ctx.respond(embed=embed)

    @bridge.bridge_command(guild_ids=testingservers, name="personalbests", description="See some pbs!")
    @has_any_role(*rank_ids)
    async def personalbests(self, ctx):
        """Shows all submitted times for a raid/scale"""
        #get relevant scales then send out top list for each

        relevant_bossScales = getRelevantBosses(25)

        page_groups = []

        for line in relevant_bossScales:
            bossId = line[0]
            scale = line[1]

            bossName = getBossInfo(bossId)[1]
            #print(bossName)
            scaleText = get_scale_text(scale)
            #print(scaleText)

            pbData = getHiscorePbsIgnoreUrl(bossId, scale)
            #print(pbData)

            pageinator = createPageInatorPbs(pbData,scale)

            page_groups.append(pages.PageGroup(
                pages=pageinator,
                label=f"{bossName} - {scaleText}",
                description="",
                use_default_buttons=True,
            ))

        paginator = pages.Paginator(pages=page_groups, show_menu=True)
        await paginator.respond(ctx, ephemeral=False)



    @bridge.bridge_command(guild_ids=testingservers, name="leaderboard", description="see some leaderboards")
    @has_any_role(*rank_ids)
    async def leaderboard(self, ctx):
        """Shows diary points, points, monthly points"""
        diary_points = pageinatorGetPages("diaryPoints", 11)
        user_points = pageinatorGetPages("points",5)
        day30spoints = getPointsMonthly(datetime.datetime.now().month,datetime.datetime.now().year)
        numMembersInTable = len(day30spoints)
        #print(day30spoints[0][2])

        test = createPageInator(day30spoints,f"{datetime.datetime.now().strftime('%B')} leaderboard","**Point Leaderboard**")

        month = datetime.datetime.now().month
        year = datetime.datetime.now().year

        starRanksData = getStarRanksPointsbyMonth(month, year)
        starRanks = createPageInator(starRanksData,f"Star ranks data - {datetime.datetime.now().strftime('%B')}",f"**Point leaderboard**")

        nonStarRankData = getNonStarRanksPointsbyMonth(month, year)
        nonStarRank = createPageInator(nonStarRankData,f"Ranks data - {datetime.datetime.now().strftime('%B')}",f"Point leaderboard")

        if month == 1:
            year -= 1
            month = 12
        else:
            month -= 1

        starRanksData = getStarRanksPointsbyMonth(month, year)
        PrevMonthstarRanks = createPageInator(starRanksData, f"Star ranks data - {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=1)).strftime('%B')}",
                                     f"**Point leaderboard**")
        nonStarRankData = getNonStarRanksPointsbyMonth(month, year)
        PrevMonthnonStarRank = createPageInator(nonStarRankData, f"Ranks data - {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=1)).strftime('%B')}",
                                       f"Point leaderboard")


        page_groups = [
            pages.PageGroup(
                pages=diary_points,
                label="Diary points leaderboard",
                description="Poggers pogs with most pog pbs",
            ),
            pages.PageGroup(
                pages=user_points,
                label="Point leaderboard",
                description="Farmers farming big loots",
                use_default_buttons=True,
            ),
            pages.PageGroup(
                pages=test,
                label=f"Point leaderboard - {datetime.datetime.now().strftime('%B')}",
                description="Farmers farming big loots (but 30 days)",
                use_default_buttons=True,
            ),
            pages.PageGroup(
                pages=starRanks,
                label=f"Star ranks - Points - {datetime.datetime.now().strftime('%B')}",
                description="",
                use_default_buttons=True,
            ),
            pages.PageGroup(
                pages=nonStarRank,
                label=f"Non star ranks - Points {datetime.datetime.now().strftime('%B')}",
                description="",
                use_default_buttons=True,
            ),
            pages.PageGroup(
                pages=PrevMonthstarRanks,
                label=f"star ranks - Points {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=1)).strftime('%B')}",
                description="",
                use_default_buttons=True,
            ),
            pages.PageGroup(
                pages=PrevMonthnonStarRank,
                label=f"Non star ranks - Points {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=1)).strftime('%B')}",
                description="",
                use_default_buttons=True,
            )
        ]
        paginator = pages.Paginator(pages=page_groups, show_menu=True)
        await paginator.respond(ctx, ephemeral=False)

    """@bridge.bridge_command(guild_ids=testingservers, aliases=["Board"])
    @has_any_role(*rank_ids)
    async def board(self, ctx):
        # shows the bingo board
        ######### headless chrome driver is DED, idk gg
        url, width, height = getBingoBoard()

        path = "/usr/lib/chromium-browser/chromedriver"
        s = Service(path)
        browser_options = Options()
        browser_options.headless = True
        browser_options.add_argument('--no-sandbox')
        driver = webdriver.Chrome(service=s, options=browser_options)

        driver.get(url)
        # 'https://docs.google.com/spreadsheets/d/e/2PACX-1vT3zipP3i35JQvnSyFQnQLWVhxF2g-X5RJQoCZCSvXTCUxP3sc4wUaKN_cvv-kEDLE6phUFlxixazPn/pubhtml?gid=0&single=true')
        # 'https://docs.google.com/spreadsheets/d/e/2PACX-1vT1q196yjVwmGMBsk4aLCNNKQfSxqcXExiQzwe3-6RIBMmlTaMqdMJB-KWiz-tmFIsZBusj5dvETP8H/pubhtml?gid=1326284287&single=true')
        driver.set_window_size(width, height)

        screenshot = driver.save_screenshot('bingobongodongo.png')
        driver.quit()
        await ctx.send(file=discord.File('bingobongodongo.png'))"""

    @commands.command()
    @has_any_role(*rank_ids)
    async def bingowinners(self, ctx):
        """Shows past event/bingo winners"""
        mycursor.execute(
            "select * from sanity2.bingoWinners order by bingoId asc"
        )
        table = mycursor.fetchall()

        embed = Embed(
            title="Sanity - Bingo Winners",
        )

        for bingo in table:
            embed.add_field(name=f" <:bluediamond:1179473465733029948> **{bingo[1]}**", value=f"**{bingo[2]}** \n {bingo[3]}", inline=False)

        embed.set_thumbnail(url=ctx.guild.icon.url)

        await ctx.send(embed=embed)

    @bridge.bridge_command(aliases=["Age"])
    @has_any_role(*rank_ids)
    async def age(self, ctx, user: discord.Member = None):
        """ get user join date age """
        if not user:
            user = ctx.author

        age = getMemberAge(user.id)
        if age:
            #print(age)

            difference_in_years = f" `{age.years}` years"
            #print(difference_in_years)
            if age.years < 1:
                difference_in_years = ""
            difference_in_months = f" `{age.months}` months"
            if age.months < 1:
                difference_in_months = ""
            difference_in_days = f" `{age.days}` days"
            if age.days < 1:
                difference_in_days = ""


            await ctx.respond(f"{user.display_name} has been in the clan for{difference_in_years}{difference_in_months}{difference_in_days}.")
            #await ctx.message.delete()
        else:
            await ctx.respond(f"{user.display_name} does not have a join date set.")


    @bridge.bridge_command(guild_ids=testingservers)
    @has_any_role(*rank_ids)
    async def recentdrops(self, ctx, user: discord.Member = None):
        """ shows the users 10 recent point gains"""
        if not user:
            user = ctx.author

        data = get_recent_drops(user.id)

        notes = [item[4] for item in data]
        points = [item[2] for item in data]
        dropIds = [item[3] for item in data]
        date = [item[5] for item in data]

        embed_string = "**Note, points, date**\n\n"


        for x in range(len(data)):
            #print(dropIds[x])
            if dropIds[x]:
                messageUrl = get_drop_url(dropIds[x])
                #print(messageUrl)
                #print((messageUrl[0][0]))
                fail = 0
            else:
                messageUrl = None
                fail = 1

            try:
                length = len(messageUrl[0][0])
                if length < 10:
                    fail = 1
                    #print("FAIL")
                else:
                    fail = 0
            except:
                fail = 1

            if messageUrl and fail == 0:
                messageNote = f"[{notes[x]}]({messageUrl[0][0]})"
            else:
                messageNote = notes[x]

            embed_string += f"**{x+1}.** {messageNote} - `{points[x]}` - {date[x]} \n"

        embed = descriptionOnlyEmbed(embed_string,f"<:bluediamond:1179473465733029948> Past {len(data)} point events for {user.display_name}")

        await ctx.respond(embed=embed)

    @bridge.bridge_command(guild_ids=testingservers)
    @has_any_role(*rank_ids)
    async def diary(self, ctx, member: discord.Member = None):
        """shows your pbs n shit"""
        if not member:
            member = ctx.author

        embed, points, masterdiaryPoints = checkUserDiary(member.id)
        await ctx.respond(embed=embed)

    @bridge.bridge_command(guild_ids=testingservers)
    @has_any_role(*rank_ids)
    async def profile(self, ctx, member : discord.Member = None):
        if not member:
            member = ctx.author


        embed, diarypoints, masterdiaryPoints = checkUserDiary(member.id)
        maxdiarypoints, masterDiaryCount = maxDiaryPoints()

        data = getUserData(member.id)
        #print(data)
        #print(data[0])

        #userPoints = data[5]
        #april_fools
        userPoints = max(get_user_points(member.id),1)
        currentRankId = data[4]
        rsn = data[2]
        altRsn = data[3]
        joinDate = data[7]
        mycursor.execute(
            f"select * from sanity2.ranks where id in ({currentRankId},{currentRankId+1})"
        )
        rankdata = mycursor.fetchall()
        #print(rankdata)


        base_img = Image.open(r"imgs/smallv2dots.png")

        ## CURRENT RANK ICON
        role = ctx.guild.get_role(rankdata[0][6])
        asset = role.icon.with_size(256)
        data = BytesIO(await asset.read())
        roleIcon = Image.open(data).convert("RGBA")
        roleIcon = roleIcon.resize((50,50))
        base_img.paste(roleIcon, (81, 260), roleIcon)


        if len(rankdata) == 2: #NOT highest rank
            pointsToNextRank = rankdata[1][2]
            currentRankPointsReq = rankdata[0][2]
            if pointsToNextRank == 0:
                pointsToNextRank = userPoints+1
            diaryPointReqNextRank = rankdata[1][3]
            masterDiaryPointReqNextRank = rankdata[1][4]

            ## NEXT RANK ICON -> dont put if highest rank
            role = ctx.guild.get_role(rankdata[1][6])
            asset = role.icon.with_size(256)
            data = BytesIO(await asset.read())
            roleIcon = Image.open(data).convert("RGBA")
            roleIcon = roleIcon.resize((50, 50))
            base_img.paste(roleIcon, (685, 260), roleIcon)

            #bar
            roundedTo10Points = max(min(floor(((max((userPoints - currentRankPointsReq),1) / max((pointsToNextRank-currentRankPointsReq),1)) * 100) / 10) * 10, 100), 10)

            #pointstext
            pointsText = f"{userPoints}/{pointsToNextRank}"

        else: #max rank
            pointsToNextRank = userPoints+1
            diaryPointReqNextRank = 100000
            masterDiaryPointReqNextRank = 100000

            #bar
            roundedTo10Points = 100

            #pointsText
            pointsText = f"{userPoints}"


        if diarypoints >= diaryPointReqNextRank:
            diaryTextColor = (82, 132, 237) #(99, 245, 66) #no more green
        else:
            diaryTextColor = (82, 132, 237)

        if masterdiaryPoints >= masterDiaryPointReqNextRank:
            masterDiaryTextColor = (82, 132, 237) #(99, 245, 66) #no more green
        else:
            masterDiaryTextColor = (82, 132, 237)



        asset = member.display_avatar.with_size(128)
        data = BytesIO(await asset.read())
        pfp = Image.open(data).convert("RGBA")
        pfp = pfp.resize(size=[128,128])
        pfp = make_circular(pfp)
        #print(type(pfp))

        memberRolesWithIcons = [role.id for role in member.roles if role.id in getRolesWithIcon()]
        #print(f"ROLE IDS {[role.id for role in member.roles]}")
        #print(f"ROLES WITH ICONS IN MEMBERS LIST {memberRolesWithIcons}")
        # print(memberRolesWithIcons)
        adjustmentPixels = 0
        for id in memberRolesWithIcons:
            #print(F" ROLE ID ADDED {memberRolesWithIcons[x]}")
            role = ctx.guild.get_role(id)
            if role.icon:
                asset = role.icon.with_size(256)
                data = BytesIO(await asset.read())
                pokemonIcons = Image.open(data).convert("RGBA")
                pokemonIcons = pokemonIcons.resize((40, 40))
                base_img.paste(pokemonIcons, (70 + adjustmentPixels, 540), pokemonIcons)
                adjustmentPixels += 50
            else:
                print(f"{role.mention} has no role icon =====")

        base_img.paste(pfp, (80, 60), pfp)

        points_img = Image.open(fr"imgs/points/{roundedTo10Points}percent.png")
        base_img.paste(points_img, (135, 260), points_img)

        mycursor.execute(
            f"select nationality from sanity2.users where userId = {member.id}"
        )
        nationality = mycursor.fetchall()[0][0]

        if not nationality:
            nationality = "aq"
        else:
            nationality = nationality.lower()

        author_name = str(f"{member.display_name}")
        displayNameFont = ImageFont.truetype("imgs/Nexa-Heavy.ttf", 72)
        text_width = get_text_width(author_name,displayNameFont)
        #print(text_width)

        flag_img = Image.open(f"imgs/flags/{nationality}.png").convert("RGBA").resize(size=[60,45])
        base_img.paste(flag_img, (224+text_width,115), flag_img)

        #get all roles with icon


        font = "imgs/Roboto-Medium.ttf"
        title_font = ImageFont.truetype(font, 36)
        rsnFont = ImageFont.truetype(font, 30)
        altrsnFont = ImageFont.truetype(font, 21)
        text_font = ImageFont.truetype(font, 26)
        big_font = ImageFont.truetype("imgs/Nexa-Heavy.ttf",42)

        image_editable = ImageDraw.Draw(base_img)

        #ALT RSN
        if altRsn:
            image_editable.text((545, 471), altRsn, fill=(0, 0, 0), font=rsnFont, anchor="lt")  # black shadow/outline
            image_editable.text((544, 470), altRsn, fill=(82, 132, 237), font=rsnFont, anchor="lt")  # actual text

        #JOINDATE
        if joinDate:
            image_editable.text((81, 388), str(joinDate), fill=(0, 0, 0), font=rsnFont, anchor="lt")  # black shadow/outline
            image_editable.text((80, 387), str(joinDate), fill=(82, 132, 237), font=rsnFont, anchor="lt")  # actual text

        #RSN
        if not rsn:
            rsn = "/changersn"
        image_editable.text((545, 388), rsn, fill=(0, 0, 0), font=rsnFont, anchor="lt")  # black shadow/outline
        image_editable.text((544, 387), rsn, fill=(82, 132, 237), font=rsnFont, anchor="lt")  # actual text

        # POINTS
        image_editable.text((81, 201), f"Points: {pointsText}", fill=(0, 0, 0), font=big_font)  # black shadow/outline
        image_editable.text((80, 200), f"Points: {pointsText}", fill=(82, 132, 237), font=big_font)  # actual text

        # AUTHOR NAME
        #author_name = str(f"{member.display_name}")  # text split up from arg
        image_editable.text((216, 82), author_name, fill=(0, 0, 0), font=displayNameFont)  # black shadow/outline
        image_editable.text((215, 81), author_name, fill=(82, 132, 237), font=displayNameFont)  # actual text

        ####CURRENT RANK TEXT
        image_editable.text((311, 381), f"{rankdata[0][1]}", fill=(0, 0, 0), font=rsnFont)  # black shadow/outline
        image_editable.text((310, 380), f"{rankdata[0][1]}", fill=(82,132,237), font=rsnFont)  # actual text

        """###NEXT RANK TEXT
        if len(rankdata) == 2: #highest rank
            image_editable.text((311, 388), f"{rankdata[1][1]}", fill=(0, 0, 0), anchor="lt",  font=rsnFont)  # black shadow/outline
            image_editable.text((310, 387), f"{rankdata[1][1]}", fill=(82, 132, 237), anchor="lt",  font=rsnFont)  # actual text
        else:
            image_editable.text((311, 388), f"Max rank gz", fill=(0, 0, 0), anchor="lt",
                                font=rsnFont)  # black shadow/outline
            image_editable.text((310, 387), f"Max rank gz", fill=(82, 132, 237), anchor="lt",
                                font=rsnFont)  # actual text"""

        ###NEXT DIARY POINTS
        image_editable.text((81, 471), f"{diarypoints}/{maxdiarypoints}", fill=(0, 0, 0),
                            font=text_font)  # black shadow/outline
        image_editable.text((80, 470), f"{diarypoints}/{maxdiarypoints}", fill=diaryTextColor, font=text_font)  # actual text

        ###NEXT MASTER DIARY POINTS
        image_editable.text((311, 471), f"{masterdiaryPoints}/{masterDiaryCount}", fill=(0, 0, 0),
                            font=text_font)  # black shadow/outline
        image_editable.text((310, 470), f"{masterdiaryPoints}/{masterDiaryCount}", fill=masterDiaryTextColor,
                            font=text_font)  # actual text

        base_img.save("imgs/profile.png")

        base_img.close()
        flag_img.close()
        pfp.close()
        points_img.close()
        roleIcon.close()

        file = discord.File("imgs/profile.png")

        await ctx.respond(file=file)

    @commands.command()
    @has_any_role(*rank_ids)
    async def submit(self, ctx):
        """use /submit or /pbsubmission to submit drops"""
        embed = descriptionOnlyEmbed("Use the slash commands /submit or /pbsumission")
        await ctx.send(embed=embed)


    @discord.slash_command(guild_ids=testingservers, name="setnationality", description="Set a flag for /profile")
    @has_any_role(*rank_ids)
    async def setnationality(self, ctx: discord.ApplicationContext,
                         countrycode: discord.Option(str, "Choose a country code", autocomplete=countrySearcher, max_length=5)):
        """add a flag for /profile"""
        mycursor.execute(
            f"update sanity2.users set nationality = '{countrycode}' where userId = {ctx.author.id}"
        )
        db.commit()

        await ctx.respond(f"Your nationality has been updated to {countrycode}!", ephemeral=True)

    """@discord.slash_command(guild_ids=testingservers,name="test4")
    @is_owner()
    async def test(self, ctx, user:discord.Member):
        await ctx.channel.set_permissions(user, send_messages=True)"""

    @bridge.bridge_command(guild_ids=testingservers)
    @has_any_role(*rank_ids)
    @commands.cooldown(2, 300, commands.BucketType.guild)
    async def nominate(self,ctx, user: discord.Member):
        """Get the terrorists out"""
        if ctx.channel.id == 1145437443911340143:
            embed = discord.Embed(title=f"{user.display_name} #countingcord vote",
                                  description=f"{user.mention} has been voted to be removed from #countingcord. \n 10 🤝 to pass within 90s",
                                  color=0xc32222)
            sendmsg = await ctx.send(embed=embed)
            await sendmsg.add_reaction("🤝")
            passedVote = 0

            for x in range(90):
                await asyncio.sleep(1)
                sendmsg = await ctx.channel.fetch_message(sendmsg.id)
                total_count = 0
                for r in sendmsg.reactions:  # shows total reactswait
                    total_count += r.count
                    # print(total_count) #sends total amount of reactions (from all emotes9

                # print(sendmsg.reactions) #sends discord api reaction thingy

                if "<Reaction emoji='🤝' me=True count=10>" in str(
                        sendmsg.reactions) or "<Reaction emoji='🤝' me=True count=11>" in str(
                    sendmsg.reactions) or "<Reaction emoji='🤝' me=True count=12>" in str(sendmsg.reactions):
                    await ctx.channel.set_permissions(user,send_messages=False)
                    embed = discord.Embed(title=f"{user} countingcord vote passed",
                                          description=f"{user.mention} pce bozo 🤝 {ctx.author.mention}", color=0xc32222)
                    await ctx.send(embed=embed)
                    passedVote = 1
                    break  # exit loop

            if passedVote == 0:
                await ctx.send("vote failed")



    @bridge.bridge_command(guild_ids=testingservers)
    @has_any_role(*rank_ids)
    async def birthday(self, ctx):
        """Shows days until next birthday"""
        now = datetime.datetime.now()
        """ mycursor.execute(
            f"SELECT count(userID) FROM sanity2.sanitybirthdays")
        sign_ups = mycursor.fetchall()
        sign_up_count = int(sign_ups[0][0])
        #print(sign_up_count)"""

        day_of_year = datetime.datetime.now().timetuple().tm_yday

        table = getBirthdays(day_of_year)

        string_embed = ""
        birthday_count = 0
        for x in range(min(10, len(table))):
            birthdayDate = table[x][2]
            birthdayyear = birthdayDate.year
            current_year = datetime.datetime.now().year

            birthdayDateString = f"{birthdayDate.month}-{birthdayDate.day}"
            todayString = f"{now.month}-{now.day}"
            # print(F"{birthdayDateString} AND {todayString}")

            if birthdayDateString == todayString:
                age = (int(current_year) - int(birthdayyear))

                birthday_date = "🥳**Happy birthday!**🥳"
                birthday_count += 1
                if age < 100:
                    birthday_date = f"🥳Happy birthday!🥳 - Turning `{age}` \n"

                guild = bot.get_guild(301755382160818177)  # 305380209366925312 # 580855880426324106
                user = guild.get_member(int(table[x][0]))  # gets displayname of member
                string_embed = string_embed + f"**{user.display_name}** - {birthday_date} \n"

        # print(string_embed)

        embed = discord.Embed(
            title=f"<a:Baldy:792592504989417472> 🥳**Sanity birthdays!**🥳 <a:Baldy:792592504989417472>\n",
            description=f"🎉Birthday boys n girls in Sanity today:🎉 Wish them a happy birthday❤️\n\n"
                        f"{string_embed}",
            color=discord.Color.purple()
        )
        guild = bot.get_guild(301755382160818177)  # 305380209366925312 # 580855880426324106
        user = guild.get_member(int(table[0][0]))

        try:
            embed.set_thumbnail(url=f"{user.avatar.url}")
        except:
            embed.set_thumbnail(url=f"{user.default_avatar.url}")

        #channel = bot.get_channel(316209688180162560)  # 872830642646302812 #580855881302802466 # bot-stuff #872830642646302812 #921677002057064469 #public 580855881302802466
        # print(birthday_count)
        """if birthday_count > 0:
            await channel.send("<@&986487111358218310>", embed=embed)
        else:
            print("NO BIRTHDAYS")"""

        if birthday_count > 0:
            birthday_msgg = f"\n {string_embed}"
        else:
            birthday_msgg = f"\n Next birthday is in {int(table[0][2].timetuple().tm_yday - day_of_year)} day(s) 🎉\n \n"

        embed = discord.Embed(
            title=f"🥳Sanity Birthdays!🥳",
            description=  # f"x have signed up! \n"
            f"{birthday_msgg} \n"
            f"sign up with **/birthday_add**🎉"
        )

        await ctx.respond(embed=embed)

    @discord.slash_command(guild_ids=testingservers, name="birthdayadd", description="Add your birthday!")
    @has_any_role(*rank_ids)
    async def birthdayadd(self,ctx: discord.ApplicationContext,
                           day: discord.Option(int, "Which day", min_value=1, max_value=31),
                           month: discord.Option(int, "Which month", min_value=1, max_value=12),
                           year: discord.Option(int, "Which year", min_value=1900, max_value=2021, required=False)):

        author_id = ctx.author.id
        mycursor.execute(f"SELECT birthday FROM sanity2.users where userId = {ctx.author.id}")
        table = mycursor.fetchall()

        dd_date = day

        if len(str(dd_date)) == 1:
            dd_date = f"0{dd_date}"
        # print(dd_date)
        mm_date = month
        if len(str(mm_date)) == 1:
            mm_date = f"0{mm_date}"
        # print(mm_date)
        if year:
            yyyy_date = year
        else:
            yyyy_date = 1900

        if yyyy_date > 1900:
            yyyy12_date = f"-{yyyy_date}"
        else:
            yyyy12_date = ""
        date = f"{dd_date}-{mm_date}{yyyy12_date}"

        # print(yyyy_date)
        date1 = f"{yyyy_date}-{mm_date}-{dd_date}"
        # print(date)
        try:
            print(date1)
            mycursor.execute(
                f"update sanity2.users set birthday = '{date1}' where userId = {ctx.author.id}"
            )

            db.commit()
            await ctx.respond(f"{ctx.author}, your birthday has been added as {date}", ephemeral=True)
            # await ctx.send(f"{ctx.author.display_name} has added their birthday")
        except:
            await ctx.respond(f"{ctx.author}, your birthday is already added as {table[0][0]}!", ephemeral=True)

    @bridge.bridge_command(guild_ids=testingservers)
    @has_any_role(*rank_ids)
    async def topdeaths(self, ctx, time=None):
        """Get the opt-in role to see deaths channel"""
        if not time:
            time = 10000
        mycursor.execute(
            f"SELECT count(rsn) as count, rsn from sanity2.deathTable WHERE date_format(time, '%Y-%m-%d-%T') >= NOW() - INTERVAL {time} day group by rsn order by count desc")
        table = mycursor.fetchall()

        descp_string = ""
        for x in range(min(10, len(table))):
            descp_string = descp_string + f"{x + 1}. **{table[x][1]}**: `{table[x][0]}` \n"

        embed = discord.Embed(
            title="Top dyers in Sanity <:dead:1014315463091687454>",
            description=f"{descp_string} \n"
                        f"Get <:dead:1014315463091687454>role from **[here](https://discord.com/channels/301755382160818177/851910722572517437/851913509998034954)** and follow pinned steps :) ",
        )

        await ctx.send(embed=embed)


    @bridge.bridge_command(guild_ids=testingservers)
    @has_any_role(*rank_ids)
    async def userdeaths(self, ctx, *, rsn):
        rsn = rsn.lower()
        mycursor.execute(f"SELECT * from sanity2.deathTable where rsn like \"{rsn}\" order by time desc")
        table = mycursor.fetchall()
        # print(table)

        if len(table) > 0:
            channel = await bot.fetch_channel(1020739207154651296)
            descp_string = f"**{rsn}** has `{len(table)}` death(s) and most recent ones are: \n\n"
            for x in range(min(5, len(table))):
                msg_url = await channel.fetch_message(table[x][0])
                # print(table[x][0])
                # print(msg_url.content)
                descp_string = descp_string + f"{x + 1}. [Jump to mgs]({msg_url.jump_url}) \n"

            embed = discord.Embed(
                title=f"<:dead:1014315463091687454> Deaths for {rsn} <:dead:1014315463091687454>",
                description=f"{descp_string} \n"
                            f"Get <:dead:1014315463091687454>role from **[here](https://discord.com/channels/301755382160818177/851910722572517437/851913509998034954)** and follow pinned steps :) ",
            )

            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                description=f"The RSN **{rsn}** has no tracked deaths or not using the pinned format"
            )

            await ctx.send(embed=embed)

    @bridge.bridge_command(guild_ids=testingservers)
    @has_any_role(*rank_ids)
    async def monthstats(self, ctx):
        """Shows monthly stats about submitted items"""
        current_month = datetime.datetime.now().month
        current_year = datetime.datetime.now().year

        if current_month == 2:
            prev1_month = 1
            prev1_year = current_year
            prev2_month = 12
            prev2_year = current_year-1

        elif current_month == 1:
            prev1_month = 12
            prev1_year = current_year-1
            prev2_month = 11
            prev2_year = current_year-1

        else:
            prev1_month = current_month-1
            prev2_month  = current_month-2
            prev1_year = current_year
            prev2_year = current_year

        current_month_table = getMonthlyDropStatus(current_month,current_year)
        current_month_pageinator = createPageInator3Wide(current_month_table,f"Drop stats - {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=0)).strftime('%B')}",f"**Item, points gained, number of drops**")
        first_page_embed = createFirstPageStats(current_month, current_year,f"Drop stats - {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=0)).strftime('%B')}")
        current_month_pageinator.insert(0,first_page_embed)

        prev1_month_table = getMonthlyDropStatus(prev1_month, prev1_year)
        prev1_month_pageinator = createPageInator3Wide(prev1_month_table,
                                        f"Drop stats - {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=1)).strftime('%B')}",
                                        f"**Item, points gained, number of drops**")
        first_page_embed = createFirstPageStats(prev1_month, prev1_year,f"Drop stats - {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=1)).strftime('%B')}")
        prev1_month_pageinator.insert(0, first_page_embed)

        prev2_month_table = getMonthlyDropStatus(prev2_month, prev2_year)
        prev2_month_pageinator = createPageInator3Wide(prev2_month_table,
                                        f"Drop stats - {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=35)).strftime('%B')}",
                                        f"**Item, points gained, number of drops**")
        first_page_embed = createFirstPageStats(prev2_month, prev2_year,f"Drop stats - {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=35)).strftime('%B')}")
        prev2_month_pageinator.insert(0, first_page_embed)

        page_groups = [
            pages.PageGroup(
                pages=current_month_pageinator,
                label=f"Drop Stats - {datetime.datetime.now().strftime('%B')}",
                use_default_buttons=True
            ),
            pages.PageGroup(
                pages=prev1_month_pageinator,
                label=f"Drop Stats - {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=1)).strftime('%B')}",
                use_default_buttons=True
            ),
            pages.PageGroup(
                pages=prev2_month_pageinator,
                label=f"Drop stats - {(datetime.datetime.utcnow().replace(day=1) - timedelta(days=35)).strftime('%B')}",
                use_default_buttons=True
            )
        ]
        paginator = pages.Paginator(pages=page_groups, show_menu=True)
        await paginator.respond(ctx, ephemeral=False)



    @discord.slash_command(guild_ids=testingservers, name="updatebingobosskc",
                           description="Bingo - Update kcs gained during bingo for sheet")
    @commands.cooldown(1, 600, commands.BucketType.guild)
    @has_any_role(*rank_ids)
    async def updatebingobosskc(self, ctx):
        await ctx.defer()

        headers = {
            'apiKey': 'prjobo42nwlfnnjiy4sebqlb',
            'sanity discord bot': 'sanity discord bot'
        }

        competitionId = 43244
        sheetUrl = "https://docs.google.com/spreadsheets/d/14URAApCwog84B3BHx1gs2wlOoArYnPr06a-CDn12_eI/edit#gid=1066031678"
        tabName = "bingobosskc"

        description = getBossesNameFromTable()
        del description[0]

        for boss in description:
            test2 = requests.get(
                f'https://api.wiseoldman.net/v2/competitions/{competitionId}/csv?table=participants&metric={boss}',
                headers=headers)
            byte_content = test2.content

            content = byte_content.decode()
            file = StringIO(content)
            string = file.read()
            table = string.split("\n")
            del table[0]

            for item in table:
                # print(item.split(","))
                rsn = (item.split(",")[1])
                kcGained = int(item.split(",")[5])

                trueTest = ifPlayerInDB(rsn)
                if trueTest == True:
                    # RSN already in db -> update boss kc
                    updatebingobossEhb(rsn, boss, kcGained)
                else:
                    # put new RSN into db
                    addPlayerToTable(rsn)
                    updatebingobossEhb(rsn, boss, kcGained)

        # add database to sheet
        try:
            sa = gspread.service_account("sanitydb-v-363222050972.json")
            sheet = sa.open_by_url(sheetUrl)
            test = 1
        except gspread.exceptions.APIError:
            test = 0
            print("API ERROR UPDATING GSPREAD sheet")

        if test == 1:
            mycursor.execute(
                f"SELECT * from sanity2.bingobosskc"
            )
            table = mycursor.fetchall()
            descriptions = [[str(item[0]) for item in mycursor.description]]
            actualTable = [list(tuple) for tuple in table]

            # datetime_to_string(actualTable) #gspread doesnt like datetime.datetime obj -> converts to string
            # print(test)
            # print(F"====== DESCRIPTIONS==============")
            # print(descriptions)

            # print(F"======= TABLE =========")
            # print(actualTable)

            # Write the array to worksheet starting from the A2 cell
            try:
                workSheet = sheet.worksheet(tabName)
                workSheet.clear()
                workSheet.update(values=descriptions, range_name='A1')  # insert description / header
                workSheet.update(values=actualTable, range_name='A2')  # insert data
            except:
                print(f"BINGO KC update FAILED - API unavilable usually!!!")

            try:
                print(f"Sheet **BINGO KC** has been updated")
            except:
                print(f"Sheet **BINGO KC** has been updated")
        else:
            print(f"sheet did not update - api error!")

        await ctx.respond("Bingo sheet has been updated")

    @discord.slash_command(guild_ids=testingservers, name="updatebingodrops",
                           description="Bingo - Update approved drops for sheet")
    @has_any_role(*rank_ids)
    async def updatebingodrops(self,ctx):
        await ctx.defer()
        #bingoVal = bingoModeCheck()
        # print(bingoVal)
        # DO BINGO STUFF
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
        await ctx.respond("Bingo drops have been synced with sheet")


def setup(bot):
    bot.add_cog(User(bot))
