import requests
from urlextract import URLExtract
import discord
from discord.ext import commands, bridge, pages
from discord.ext.commands import has_any_role
import datetime
import gspread
from discord.ui import InputText, Modal, button, Button, View
from discord import Embed
from ..handlers.DatabaseHandler import add_boss, get_adminCommands_roles, testingservers, add_drop, insert_audit_Logs, \
    add_channel, enableCompMode, update_user_points, turnListOfIds_into_names, updateUserId, get_all_users, \
    get_drop_names, \
    updateGracePeriod, insert_Point_Tracker, add_user_todb, mycursor, db, get_all_ranks, get_bosses, getUserData, \
    get_channel, update_boss_url
from ..handlers.diaryHandler import checkUserDiary
from ..handlers.EmbedHandler import embedVariable
from math import ceil



def datetime_to_string(rows):
    for line in rows:
        for i, item in enumerate(line):
            if isinstance(item, datetime.date):
                line[i] = str(item)
            if item == "":
                line[i] = None
            if isinstance(item, int):
                line[i] = str(item)

def updateDiaryTierClaimed(userId, rankClaimed):
    mycursor.execute(
        f"update sanity2.users set diaryTierClaimed = {rankClaimed} where userId = {userId}"
    )
    db.commit()



def insertRefs(trialId : int, refIds : str):
    mycursor.execute(
        f"insert into sanity2.referrals (userId, referralIds)"
        f" Values (%s, %s)",
        (trialId,refIds)
    )

    db.commit()

def selectPbFromId(pbId : int):
    mycursor.execute(
        f"select members, bossId, scale, time, status from sanity2.personalbests where submissionId = {pbId}"
    )

    data = mycursor.fetchone()

    return data, [title[0] for title in mycursor.description]


def updatePb(pbId, participants, bossId : int, scale: int, time : str, status : int):
    mycursor.execute(
        f"update sanity2.personalbests set members = '{participants}', bossId = {bossId}, scale = {scale}, time = '{time}', status = {status} where submissionId = {pbId}"
    )

    db.commit()

async def drop_searcher(ctx : discord.AutocompleteContext):
    """
        Returns a list of matching DROPS from the DROPS table list."""
    drop_names = get_drop_names()

    return [
        drop for drop in drop_names if (ctx.value.lower() in drop.lower())
    ]

async def boss_searcher(ctx : discord.AutocompleteContext):
    """
        Returns a list of matching DROPS from the DROPS table list."""
    boss_names, boss_ids = get_bosses()

    return [
        boss for boss in boss_names if (ctx.value.lower() in boss.lower())
    ]

def db_pageinatorGetPages(data, listOfTableTitles, tableName, maxColumns): #prob the best pageinator maker. String has to be less than 2000 characters for embed

    numInTable = len(data)
    listOfTableTitles_text = ", ".join([str(name) for name in listOfTableTitles])

    test = []

    count = 0
    stringf = ""
    while count <= numInTable-1: #adds the text up
        #print(count)
        stringTest = ' - '.join([str(text) for text in data[count][1:maxColumns]])
        stringf += f"**{data[count][0]}** - {stringTest} \n" #makes first item bold, rest normal joined

        if len(stringf) > 1700 or count == numInTable-1:
            test.append(Embed(title=f"Database - {tableName}", description=f"**{listOfTableTitles_text}** \n\n {stringf}"))
            stringf = ""

        count += 1

    return test

def get_table_names():
    mycursor.execute(
        "show tables from sanity2"
    )
    list = mycursor.fetchall()

    return list

async def table_searcher(ctx : discord.AutocompleteContext): #gets all tables from a schema
    tableList = get_table_names()
    proper_format = [table[0] for table in tableList]

    return [
        table for table in proper_format if (ctx.value.lower() in table.lower())
    ]

async def table_searcher(ctx : discord.AutocompleteContext): #gets all tables from a schema
    tableList = get_table_names()
    proper_format = [table[0] for table in tableList]

    return [
        table for table in proper_format if (ctx.value.lower() in table.lower())
    ]
async def table_table_searcher(ctx : discord.AutocompleteContext): #gets column names in a table - seems to struggle if table is changed, so only works in "first shot"
    #print(ctx.value) #current field value
    tableName = ctx.options["table"] #all field values
    #print(tableName)
    #print(ctx.focused) #focused field
    #tableList = get_table_names()
    #print(tableName)
    mycursor.execute(
        f"select * from sanity2.`{tableName}`"
    )

    test = mycursor.fetchall()

    description = mycursor.description

    try:
        proper_format = [title[0] for title in description]
        #print(f"PROPER FORMAT {proper_format}")
        #print([table for table in proper_format if (ctx.value.lower() in table.lower())])
        return [
            table for table in proper_format if (ctx.value.lower() in table.lower())
        ]
    except:
        print("lol its fucked")

def updateDropValue(dropName:str, newDropValue : int):
    mycursor.execute(
        f"update sanity2.drops set value = {newDropValue} where name = '{dropName}'"
    )
    db.commit()


class trialFeedbackButton(View):
    def __init__(self):
        super().__init__(timeout=None) # timeout of the view must be set to None
        self.value = None

    @discord.ui.button(label="Send feedback", custom_id="button-trialfeedback", style=discord.ButtonStyle.primary, emoji="📨") # the button has a custom_id set
    async def button_callback(self, button, interaction):
        print("FEEDBACK BUTTON WORKING")
        modal = TrialFeedbackModal(title=f"Trial feedback form")
        await interaction.response.send_modal(modal)

class TrialFeedbackModal(Modal):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(InputText(label="+1 or -1", value="+1"))

        self.add_item(
            InputText(
                label="Feedback",
                placeholder="Add feedback here",
                style=discord.InputTextStyle.long,
            )
        )

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"Feedback from {interaction.user.display_name}", color=discord.Color.blue())
        embed.add_field(name="Rating", value=self.children[0].value, inline=False)
        embed.add_field(name="Comment:", value=self.children[1].value, inline=False)

        embed1 = (interaction.message.embeds[0])
        embed_dict = embed1.to_dict()
        embed_title = embed_dict["title"]
        feedback_name = embed_title.replace(" application","")  #name of trial
        embed_title = embed_title.replace(" application","-feedback").lower() #name of text channel
        embed_title = embed_title.replace(" ", "-")

        channel = discord.utils.get(interaction.guild.channels, name=embed_title)
        #print(channel)
        await channel.send(embeds=[embed])

        await interaction.response.send_message(f"✅ Your feedback for **{feedback_name}** has been submitted", ephemeral=True)


class pbChangeAcceptor(View):  # for council / drop acceptors etc in #posted-drops
    def __init__(self, author, titles):
        super().__init__(timeout=None)
        self.value = None
        self.author = author
        self.titles = titles

    async def interaction_check(self, interaction: discord.Interaction):
        if self.author.id == interaction.user.id:
            return True

    @button(label="Accept PB change", custom_id="acceptor-accept-button-5" ,style=discord.ButtonStyle.green, emoji="✅")
    async def acceptPbEdit(self, button: Button, interaction: discord.Interaction):
        for embed in interaction.message.embeds:
            embed_dict = embed.to_dict()

        now = datetime.datetime.now()
        pb_id = str(embed_dict["title"]).split("- ")[1]
        participants_id = embed_dict["fields"][0]["value"]
        bossId = int(embed_dict["fields"][1]["value"])
        scale = int(embed_dict["fields"][2]["value"])
        time = (embed_dict["fields"][3]["value"])
        status = (embed_dict["fields"][4]["value"])

        insert_audit_Logs(interaction.user.id,6,now,f"pbId {pb_id} updated to {participants_id}, {bossId}, {scale}, {time}, {status}",participants_id)

        updatePb(pb_id,participants_id,bossId,scale,time,status)

        embed.color = discord.Color.green()
        await interaction.response.edit_message(embed=embed, view=None)
        #await interaction.response.send_message("PB submission has been updated",ephemeral=True)

    @button(label="Edit", custom_id="edit-button-2", style=discord.ButtonStyle.gray, emoji="✏️")
    async def editSubmission(self, button: Button, interaction: discord.Interaction):
        for embed in interaction.message.embeds:
            embed_dict = embed.to_dict()

        data = []
        pb_id = str(embed_dict["title"]).split("- ")[1]
        participants_id = embed_dict["fields"][0]["value"]
        bossId = int(embed_dict["fields"][1]["value"])
        scale = int(embed_dict["fields"][2]["value"])
        time = (embed_dict["fields"][3]["value"])
        status = (embed_dict["fields"][4]["value"])

        data.extend([participants_id,bossId,scale,time,status])

        modal = pbEditSubmissionModal(title="Edit pb in DB",data=data,titles=self.titles)
        await interaction.response.send_modal(modal)


class pbEditSubmissionModal(Modal):  # modal to edit msg
    def __init__(self, data, titles, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.data = data
        self.titles = titles

        for i in range(0, len(self.titles)):
            self.add_item(InputText(label=f"{titles[i]}", value=f"{data[i]}",style=discord.InputTextStyle.short, max_length=200, min_length=1))

    async def callback(self, interaction: discord.Interaction):  # response to modal
        # await interaction.response.send_message(f"{self.children[0].value}")
        members = self.children[0].value #first field value
        bossId = self.children[1].value #NEED TO UPDATE THE CHANGED DATA!
        scale = self.children[2].value #NEED TO UPDATE THE CHANGED DATA!
        time = self.children[3].value  # NEED TO UPDATE THE CHANGED DATA!
        imageUrl = self.children[4].value  # NEED TO UPDATE THE CHANGED DATA!

        for embed in interaction.message.embeds:
            embed_dict = embed.to_dict()

        embed_dict['fields'][0]['value'] = members
        embed_dict['fields'][1]['value'] = int(bossId)
        embed_dict['fields'][2]['value'] = int(scale)
        embed_dict['fields'][3]['value'] = time
        embed_dict['fields'][4]['value'] = imageUrl

        embed = embed.from_dict(embed_dict)


        view = pbChangeAcceptor(interaction.user, self.titles)
        await interaction.response.edit_message(embed=embed,view=view)  # removes button ig
        #await msg_to_edit.delete()  # deletes old msg
        #await interaction.response.send_message("Drop submission has been updated", ephemeral=True)

class Admin(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    admin_roles = get_adminCommands_roles()
    admin_roles_ids = [role[1] for role in admin_roles]



    @discord.slash_command(guild_ids=testingservers, name="add_boss", description="Admin - Add a boss to the database")
    @has_any_role(*admin_roles_ids)
    async def addBoss(self, ctx: discord.ApplicationContext,
                      boss_name : discord.Option(str, description="boss name!!!",max_length=50),
                      imageurl : discord.Option(str, description="image url from wiki",max_length=250, required=False)):
        """add a boss to the database
        variables:
            bossname: Name of boss
            imageUrl: Url of boss from wiki"""

        names,ids = get_bosses()

        if boss_name in names:
            update_boss_url(boss_name, imageurl)
            insert_audit_Logs(ctx.author.id, 6, datetime.datetime.now(), f"addBoss {boss_name}")

            await ctx.respond(f"boss {boss_name} image has been updated")
        else:
            add_boss(boss_name, imageurl)
            insert_audit_Logs(ctx.author.id, 6, datetime.datetime.now(), f"addBoss {boss_name}")

            await ctx.respond(f"boss {boss_name} has been added")

    @discord.slash_command(guild_ids=testingservers, name="add_drop", description="Admin - Add a drop to the database")
    @has_any_role(*admin_roles_ids)
    async def addDrop(self, ctx: discord.ApplicationContext,
                      drop : discord.Option(str,description="drop name!!!",max_length=50),
                      value : discord.Option(str,description="value of drop",max_length=50, required=False)):
        """add a boss to the database
        variables:
            drop: the item added to DB
            value: drop value (not used now...)"""

        add_drop(drop, value)
        insert_audit_Logs(ctx.author.id, 6, datetime.datetime.now(), f"addDrop {drop}")

        await ctx.respond(f"drop {drop} has been added")

    @discord.slash_command(guild_ids=testingservers, name="add_channel", description="Admin - Add a channel to the database")
    @has_any_role(*admin_roles_ids)
    async def addChannel(self, ctx: discord.ApplicationContext,
                      channel_name: discord.Option(str, description="channel name", max_length=50),
                      channel_id: discord.Option(int, description="channel id (enable dev mode)")):

        insert_audit_Logs(ctx.author.id, 6, datetime.datetime.now(), f"addChannel {channel_name}:{channel_id}")
        add_channel(channel_name, channel_id)

        await ctx.respond(f"channel {channel_name} with id {channel_id} has been added")

    @discord.slash_command(guild_ids=testingservers, name="compmode", description="enable or disable bingo!")
    @has_any_role(*admin_roles_ids)
    async def compmode(self, ctx: discord.ApplicationContext,
                         on_or_off: discord.Option(int, description="1 = on, 0 = off",choices=[1, 0])):
        """This command syncs database with 'bingo' sheet"""

        enableCompMode(on_or_off)

        #SHITS BROKEN MADAFAKA
        await ctx.respond(f"comp mode (bingo mode) has been set to {on_or_off}")

    @discord.slash_command(guild_ids=testingservers, name="updatediarytime",
                           description="Admin - Update a diary time. If only easy time, put rest 0")
    @has_any_role(*admin_roles_ids)
    async def updatediarytime(self, ctx : discord.ApplicationContext,
                              boss : discord.Option(str, "Which boss (use /add_boss if not in list)", autocomplete=boss_searcher),
                              scale : discord.Option(int, "Scale of boss", min_value=1, max_value=100),
                              easytime : discord.Option(str, "Format example: 13:40  - put 0 if none"),
                              mediumtime : discord.Option(str, "Format example: 13:40  - put 0 if none"),
                              hardtime : discord.Option(str, "Format example: 13:40  - put 0 if none"),
                              elitetime : discord.Option(str, "Format example: 13:40  - put 0 if none"),
                              mastertime : discord.Option(str, "Format example: 13:40 - put 0 if none")):

        maxDif = 0
        if not easytime  == '0':
            maxDif += 1
        if not mediumtime  == '0':
            maxDif += 1
        if not hardtime  == '0':
            maxDif += 1
        if not elitetime  == '0':
            maxDif += 1
        if not mastertime  == '0':
            maxDif += 1

        mycursor.execute(
            f"select * from sanity2.bosses where name = '{boss}'"
        )
        bossId = mycursor.fetchall()[0][0]
        #print(F"BOSSID {bossId}")

        #check if bossId and scale in diaryTimes -> else insert

        mycursor.execute(
            f"select * from sanity2.diarytimes where bossId = {bossId} and `scale` = {scale}"
        )
        table = mycursor.fetchall()
        print(table)

        if table:
            mycursor.execute(
                f"update sanity2.diarytimes set maxDifficulty = {maxDif} ,timeEasy = '{easytime}',timeMedium = '{mediumtime}',timeHard = '{hardtime}',timeElite = '{elitetime}',timeMaster = '{mastertime}' where bossId = {bossId} and `scale` = {scale}"
            )
        else:
            mycursor.execute(
                f"insert into sanity2.diarytimes (bossId, scale, maxDifficulty, timeEasy, timeMedium, timeHard, timeElite,timeMaster)"
                f"Values (%s, %s, %s, %s, %s, %s, %s, %s)",
                (bossId, scale, maxDif, easytime, mediumtime, hardtime, elitetime, mastertime)
            )
        db.commit()

        await ctx.respond(f"Time for {boss} - {scale} has been updated")
        insert_audit_Logs(ctx.author.id,2,datetime.datetime.now(),f"Updated diarytime for {boss} - {scale}")

    @discord.slash_command(guild_ids=testingservers, name="ranksgraceperiod",
                           description="Admin - Set grace period date for ranks")
    @has_any_role(*admin_roles_ids)
    async def ranksgraceperiod(self, ctx: discord.ApplicationContext,
                         day: discord.Option(int, description="day of grace period date", min_value=1, max_value=31),
                         month: discord.Option(int, description="month of grace period date", min_value=1, max_value=12),
                         year : discord.Option(int, description="year of grace period date", min_value=2022, max_value=2321)):

        datetimeobj = datetime.date(year, month, day)

        updateGracePeriod(datetimeobj)

        await ctx.respond(f"Demotion prompts will no longer occur until {datetimeobj}")

    @discord.slash_command(guild_ids=testingservers, name="add_points", description="Admin - Ignores any point bonuses!")
    @has_any_role(*admin_roles_ids)
    async def add_points(self, ctx: discord.ApplicationContext,
                       amount : discord.Option(int, description="how much$$$", max_value=2000),
                       note : discord.Option(str, description="add some text who knows", max_length=150),
                       members: discord.Option(str, description="must be @ mentions!", max_length=850)):

        id_list = discord.utils.raw_mentions(members)
        error_list = []

        member_names = turnListOfIds_into_names(id_list)

        id_formatted = ",".join(str(id) for id in id_list)

        for member in id_list:
            try:
                update_user_points(member, amount)
                insert_Point_Tracker(member,amount,datetime.datetime.now(),note)
            except:
                error_list.append(member)

        now = datetime.datetime.now()
        note = f"add_points {amount} to {len(id_list)} members. Note: {note}"
        insert_audit_Logs(ctx.author.id,2,now,note,id_formatted)

        if len(error_list) > 0:
            await ctx.respond(f"Added {amount} points to everyone but {error_list}", ephemeral=True)

        else:
            await ctx.respond(f"Added {amount} points to: {member_names[0]}", ephemeral=True)

    @discord.slash_command(guild_ids=testingservers, name="updatediscordid",description="Admin - dumb fk who lost his discord acc")
    @has_any_role(*admin_roles_ids)
    async def updatediscordid(self, ctx: discord.ApplicationContext,
                         old: discord.Option(str, description="OLD MEMBER ID"),
                         new: discord.Option(str, description="NEW MEMBER ID")):

        old = int(old)
        new = int(new)

        updateUserId(old, new)

        await ctx.respond(f"{old} has been replaced with {new}")

    @commands.command()
    @has_any_role(*admin_roles_ids)
    async def pingvc(self,ctx, voiceChannelID: discord.VoiceChannel = None):
        """ Pings all members in a VC."""
        if voiceChannelID:
            channel1 = voiceChannelID
        else:
            channel1 = ctx.author.voice.channel

        membersInVoice = ""
        for member in channel1.members:
            membersInVoice += f"<@{member.id}> "
        await ctx.send(f"{membersInVoice}")

    @commands.command()
    @has_any_role(*admin_roles_ids)
    async def tag(self,ctx, voiceChannelID: discord.VoiceChannel = None):
        """ Returns all tags of members in a VC."""
        if voiceChannelID:
            channel1 = voiceChannelID
        else:
            channel1 = ctx.author.voice.channel
        # print("####################")
        # print(channel1)
        membersInVoice = ""
        for member in channel1.members:
            membersInVoice += f"<@{member.id}> "
        await ctx.send(f"`{membersInVoice}`")

    @bridge.bridge_command(guild_ids=testingservers, name="updatediaries",
                           description="Admin - force update diary points/pbs")
    @has_any_role(*admin_roles_ids)
    async def updatediaries(self, ctx: discord.ApplicationContext):
        """updates diary points and master diary points in table for all users"""
        all_users = get_all_users()
        user_ids = [user[0] for user in all_users]

        for user_id in user_ids:
            embed, diaryPoints, masterDiaryPoints = checkUserDiary(user_id)


        await ctx.respond("Updated all diary points")

    @bridge.bridge_command(guild_ids=testingservers, name="trial",
                           description="Admin - new baby")
    @has_any_role(*admin_roles_ids)
    async def trial(self, ctx: discord.ApplicationContext,
                    trial : discord.Option(discord.Member,"tag the trial!!!"),
                    referrals : discord.Option(str, "Who will be listed as refs (tag them @name ty)", max_length=500),
                    application: discord.Option(str, "copy pasta application")):
        """post this when new trial joins"""


        application = application.replace("*", "")
        application = application.replace("Main RSN:", "\n**Main RSN:**\n")
        application = application.replace("Alt RSN (if applicable, 1 max):", "\n**Alt RSN (if applicable, 1 max):**\n")
        application = application.replace("Past RSNs (Name as many as you can remember):",
                                          "\n**Past RSNs (Name as many as you can remember):**\n")
        application = application.replace(
            "Preferred Name (This name will be your name on Discord and will not change):",
            "\n**Preferred Name (This name will be your name on Discord and will not change):**\n")
        application = application.replace(
            "List who can vouch for you in Sanity (Please confirm with them first before listing their name):",
            "\n**List who can vouch for you in Sanity (Please confirm with them first before listing their name):**\n")
        application = application.replace("Tell us about yourself:", "\n**Tell us about yourself:**\n")
        application = application.replace("What content do you currently do in game?: ",
                                          "\n**What content do you currently do in game?: **\n")
        application = application.replace("Previous clans and why you left (PvM/PvP/Social/etc.):",
                                          "\n**Previous clans and why you left (PvM/PvP/Social/etc.):**\n")
        application = application.replace("Timezone:", "\n**Timezone:**\n")
        application = application.replace("Have you read the clan-rules ?:", "\n**Have you read the clan-rules ?:**\n")
        application = application.replace("Would you like to add anything?", "\n**Would you like to add anything?**\n")


        clannies_list = discord.utils.raw_mentions(referrals)  # gets @ tagged users in clannies field
        if len(clannies_list) > 0:
            refferals_formatted = f"{','.join(str(clannie) for clannie in clannies_list)}"
        else:
            refferals_formatted = ""

        name = trial.display_name
        name = ''.join(x for x in name if x.isalpha() or x in ["0","1","2","3","4","5","6","7","8","9"])

        trialData = getUserData(trial.id)

        try:
            add_user_todb(trial.id,trial.display_name,1,0,1,datetime.datetime.now(),refferals_formatted)
        except:
            print(f"{trial.display_name} OR ERROR IDK already in db")
            mycursor.execute(
                f"update sanity2.users set rankId = 1 where userId = {trial.id}"
            )
            db.commit()

        try:
            insertRefs(trial.id,refferals_formatted)
        except:
            print(f"{trial.display_name} already has refs -> ignore")

        embed = discord.Embed(
            title=f"{name} application",
            description=application,
            color=discord.Color.blue()
        )

        extractor = URLExtract()  # to send any images from thread separate

        urls = (extractor.find_urls(application))
        # print(urls)

        string_links = ""
        for url in urls:
            string_links = string_links + f" {url} \n "

        feedback_category = discord.utils.get(ctx.guild.categories, id=979900288729227334)  # name="trial feedback") #gets feedback category
        trial_app_category = discord.utils.get(ctx.guild.categories, id=557380617394978836)  # name="applications")

        feedback_chan = await ctx.guild.create_text_channel(f"{name}-feedback", category=feedback_category)
        trial_chan = await ctx.guild.create_text_channel(f"{name}", category=trial_app_category)
        #print(trial_chan.name)
        # await channelChat.set_permissions(ctx.guild.default_role, view_channel=False)
        #await ctx.message.delete()
        await trial_chan.send(embed=embed, view=trialFeedbackButton())
        if len(string_links) > 5:
            dingdonger = await trial_chan.send(string_links)
            thread = await dingdonger.create_thread(name=f"{name}-app-chatter")

        #fakeping members in feedback channel
        all_ranks = get_all_ranks()
        rank_ids = [rank[2] for rank in all_ranks]
        fakepingmsg = await thread.send(f"test")
        for rankId in rank_ids:
            fakepingmsg = await fakepingmsg.edit(f"<@&{rankId}>")
        await fakepingmsg.delete()

        await ctx.respond(f"created {trial_chan.mention} and {feedback_chan.mention} ✅", ephemeral=True)

    @discord.slash_command(guild_ids=testingservers, name="updatebingoitems",
                           description="Admin - Upload bingo file for bingo bingo!")
    @has_any_role(*admin_roles_ids)
    async def updatebingoitems(self, ctx: discord.ApplicationContext,
               file: discord.Option(discord.Attachment, "Attach .txt file of drops - 1 per line")):


        data = await file.read()
        string = data.decode()
        string = string.replace("\r","")
        #print(type(string))

        table = string.split("\n")

        #drop table -> reinsert items
        mycursor.execute(
            "delete from sanity2.bingodrops"
        )
        db.commit()

        #insert new items into bingo table
        for item in table:
            #print(item)
            mycursor.execute(
                f"insert into sanity2.bingodrops (name, value)"
                f"Values (%s, %s)",
                (item, 0)
            )
            db.commit()

        await ctx.respond("✅ Bingo table has been updated and /bingosubmit should be updated as well ✅")

    @discord.slash_command(guild_ids=testingservers, name="updatedropvalue",
                           description="Admin - update the minimum value of an item!")
    @has_any_role(*admin_roles_ids)
    async def updatedropvalue(self, ctx,
                              drop_name: discord.Option(str, "If the item is not in the list, use /add_drop!",
                                                        autocomplete=drop_searcher),
                              new_value : discord.Option(int, "Put in the new minimum value",min_value=0,max_value=10000)):

        updateDropValue(drop_name,new_value)

        await ctx.respond(f"{drop_name} minimum value has been updated to **{new_value}**")

    @discord.slash_command(guild_ids=testingservers, name="updatesheet",
                           description="Admin - update the sheets!")
    @commands.cooldown(3,100,commands.BucketType.guild)
    @has_any_role(*admin_roles_ids)
    async def updatesheet(self,ctx, sheetname : discord.Option(str, "Choose the sheet you want updated!", autocomplete=table_searcher)):
        #await ctx.defer()
        try:
            sa = gspread.service_account("sanitydb-v-363222050972.json")
            sheet = sa.open(f"{sheetname}")
            test = 1
        except gspread.exceptions.APIError:
            test = 0
            print("API ERROR UPDATING GSPREAD sheet")

        if test == 1:
            mycursor.execute(
                f"SELECT * from sanity2.{sheetname}"
            )
            table = mycursor.fetchall()
            descriptions = [[str(item[0]) for item in mycursor.description]]
            actualTable = [list(tuple) for tuple in table]

            datetime_to_string(actualTable) #gspread doesnt like datetime.datetime obj -> converts to string
            # print(test)
            #print(F"====== DESCRIPTIONS==============")
            #print(descriptions)

            #print(F"======= TABLE =========")
            #print(actualTable)

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


    @bridge.bridge_command(guild_ids=testingservers, name="showtables",
                           description="Admin - Show data from database!")
    @has_any_role(*admin_roles_ids)
    async def showtables(self, ctx,
                         table : discord.Option(str, "Pick a table", autocomplete=table_searcher),
                         reverse : discord.Option(str, "Reverse the table order for drops or smth idk..", required=False),
                         order_by : discord.Option(str, "Pick a column name to sort by", autocomplete=table_table_searcher, required=False),
                         maxcolumns : discord.Option(int, "Number of colums you want to see", min_value=1, max_value=1000, required=False)):

        if not maxcolumns:
            maxcolumns = 100

        if order_by:
            order_by_text = f"order by {order_by} desc"
        else:
            order_by_text = " "

        mycursor.execute(
            f"select * from sanity2.{table} {order_by_text}"
        )
        data = mycursor.fetchall()
        if reverse:
            data.reverse()

        pageinatorshit = db_pageinatorGetPages(data,[title[0] for title in mycursor.description],table, maxcolumns)

        #print(pageinatorshit)

        paginator = pages.Paginator(pages=pageinatorshit)
        await paginator.respond(ctx, ephemeral=False)

        #await ctx.respond(str(data)[0:1999])

    @discord.slash_command(guild_ids=testingservers, name="updatepb",
                           description="Admin - Update an already submitted PB!")
    @has_any_role(*admin_roles_ids)
    async def updatepb(self, ctx: discord.ApplicationContext,
                               pb_id: discord.Option(int, "The pb ID is stated in the title of pb submission embed", min_value=1)):

        data, titles = selectPbFromId(pb_id)
        tupletest = [(titles[i], data[i]) for i in range(0,len(titles))]

        embed = embedVariable(f"Editing pb id - {pb_id}",discord.Colour.yellow(),tupletest[0],tupletest[1],tupletest[2],tupletest[3],tupletest[4])

        view = pbChangeAcceptor(ctx.author, titles)
        await ctx.respond(embed=embed, view=view, ephemeral=True)

    @discord.slash_command(guild_ids=testingservers, name="updatedrops_fromwiki",
                           description="Admin - adds all items from wiki list")
    @has_any_role(*admin_roles_ids)
    async def updatedrops_fromwiki(self, ctx: discord.ApplicationContext):
        """Adds all items to /drop_submission command from wiki list"""
        await ctx.defer()

        drops_in_db = get_drop_names()
        drops_in_db = [drop.lower() for drop in drops_in_db]
        #print(drops_in_db)
        drops_in_db.append("%LAST_UPDATE%")
        drops_in_db.append("%LAST_UPDATE_F%")

        #get item list from wiki
        x = requests.get(
            'https://oldschool.runescape.wiki/?title=Module:GEIDs/data.json&action=raw&ctype=application%2Fjson')
        data = x.json()
        wiki_items_list = [entry for entry in data]

        added_item_count = 0
        for item in wiki_items_list:
            if item.lower() not in drops_in_db:
                add_drop(item, 0)
                added_item_count += 1

        insert_audit_Logs(ctx.author.id, 6, datetime.datetime.now(), f"addDropFromWiki {added_item_count} items added")

        await ctx.respond(f"Added {added_item_count} to the drops table")


    @discord.slash_command(guild_ids=testingservers, name="retire",
                           description="Admin - retire somebody")
    @has_any_role(*admin_roles_ids)
    async def retire(self, ctx: discord.ApplicationContext,
                     user : discord.Option(discord.Member,description="TAG THE GUY")):

        #print(user)

        rank_ids = get_all_ranks()
        db_rank_ids = [dbrank[2] for dbrank in rank_ids]
        #print(db_rank_ids)

        sanity = ctx.guild


        for rankId in db_rank_ids:
            #get role and remove from user
            role = sanity.get_role(rankId)
            try:
                await user.remove_roles(role)
            except:
                #print("DOESNT HAVE XYZ ROLE")
                continue

        retired_role_id = get_all_ranks("RETIRED")[0][2]
        retired_role = sanity.get_role(retired_role_id)

        await user.add_roles(retired_role)

        mycursor.execute(
            f"update sanity2.users set isActive = 0 where userId = {user.id}"
        )
        db.commit()

        await ctx.respond(f"{user.display_name} has been retired :)")

    @discord.slash_command(guild_ids=testingservers, name="updatediarytierclaimed",
                           description="Admin - update diary tier claimed")
    @has_any_role(*admin_roles_ids)
    async def updatediarytierclaimed(self, ctx, member : discord.Member, diarytierclaimed : int):
        updateDiaryTierClaimed(member.id, diarytierclaimed)

        await ctx.respond(f"{member.display_name} has been updated")

    @discord.slash_command(guild_ids=testingservers, name="quitto",
                           description="Admin - quitto somebody")
    @has_any_role(*admin_roles_ids)
    async def quitto(self, ctx: discord.ApplicationContext,
                     user: discord.Option(discord.Member, description="TAG THE GUY")):

        mycursor.execute(
            f"update sanity2.users set rankId = -1, leaveDate = '{datetime.datetime.now()}' where userId = {user.id}"
        )
        db.commit()

        mycursor.execute(
            f"update sanity2.personalbests set members = replace((replace(members, ',{user.id}','')),'{user.id},','')"
        )

        insert_audit_Logs(ctx.author.id,2,datetime.datetime.now(),f"{user.display_name} has quitto",user.id)

        await ctx.respond(f"{user} has been retired")








def setup(bot):
    bot.add_cog(Admin(bot))
