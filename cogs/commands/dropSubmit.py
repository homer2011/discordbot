import math
import time

from PIL import Image
from discord.ext import commands
from discord.ui import View, Modal, InputText, Button, button
from discord.commands import option
import datetime
import discord
from ..handlers.DatabaseHandler import testingservers, get_channel, mycursor, get_all_ranks, updateDropStatus, \
    update_user_points, insert_drop_into_submissions, update_drop_submission, get_drop_names, insert_audit_Logs, \
    insert_Point_Tracker, updateDropStatusONLY \
    , get_bingo_drop_names, bingoModeCheck, db
from ..handlers.EmbedHandler import greenDropsEmbed
from ..util.CoreUtil import uploadfile
from io import BytesIO
import requests
import asyncio
import aiohttp
def sqlSafeNameFix(itemName : str):
    newName = itemName.replace("'","\\'")

    return newName

def getDropStatus(dropId):
    mycursor.execute(
        f"select Id,status from sanity2.submissions where id = {dropId}"
    )
    data = mycursor.fetchall()
    if len(data) > 0:
        return data[0][1]
    else:
        return 0


def checkItemValueDrop(itemName : str, submittedValue : int):
    try:
        itemName = sqlSafeNameFix(itemName)
        mycursor.execute(
            f"select * from sanity2.drops d where d.name = '{itemName}' and d.value is not NULL"
        )

        data = mycursor.fetchall()
    except:
        #print(f"failed checkItemValueDrop on itemName {itemName} and value {submittedValue}")
        data = None

    if data: #should be 1, no duplicate names..
        return data[0][2] #value from db
    else:
        return submittedValue

async def imgurUrlSubmission(imgur_url : str, ctx):
    image_fail = 0
    url = imgur_url
    #url = "https://i.imgur.com/gqRHViw.jpeg"  # must be an image
    if str(url).endswith(('.png', 'jpg', '.gif', 'jpeg')) and url.startswith("https://") and "imgur" in url:   # basic URL test
        response = requests.get(url, headers = {'User-agent': 'Sanity_discord_bot_v2', 'Authorization': 'Client-ID bfbe5cf4c1ef16f'})
    #print(response.headers)
    #print(type(response))
        image_data = BytesIO(response.content)
        #print("TRUE")
        #print(type(image_data))
        image1 = discord.File(image_data, "image.png")
        #image = Image.open((image_data))
        #image.show()
    #print(image1)
    else:
        image_fail = 1

    if image_fail == 0:
        return image1
    else:
        await ctx.send(f"{ctx.author.mention} Invalid imgur link - **must be direct imgur image link** like `https://i.imgur.com/qBOlMKJ.png`")

def getSubmissionStatus(id):
    mycursor.execute(
        f"select status from sanity2.submissions where id = {id}"
    )
    status = mycursor.fetchall()[0][0]

    return status

async def drop_searcher(ctx : discord.AutocompleteContext):
    """
        Returns a list of matching DROPS from the DROPS table list."""

    drop_names = get_drop_names()

    return [
        drop for drop in drop_names if (ctx.value.lower() in drop.lower())
    ]

async def bingo_drop_searcher(ctx : discord.AutocompleteContext):
    drop_names = get_bingo_drop_names()

    return [
        drop for drop in drop_names if (ctx.value.lower() in drop.lower())
    ]

def getDropData(dropId : int): #returns participants
    mycursor.execute(
        f"select * from sanity2.submissions where Id = {dropId}"
    )
    data = mycursor.fetchall()

    if len(data) > 0:
        return data[0][4] #returns participants
    else:
        return None


class submissionAcceptor(View):  # for council / drop acceptors etc in #posted-drops
    def __init__(self):
        super().__init__(timeout=None)
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction):
        mycursor.execute(
            "select discordRoleId,name from sanity2.roles where acceptDrops = 1"
        )
        data = mycursor.fetchall()
        list = [i[0] for i in data]

        interaction_user_roleID_list = [role.id for role in interaction.user.roles]

        check = any(role in interaction_user_roleID_list for role in list)
        return check

    @button(label="Accept drop", custom_id="acceptor-accept-button-1" ,style=discord.ButtonStyle.green, emoji="✅")
    async def acceptDrop(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        now = datetime.datetime.now()
        submissionId = int(str(embed_dict["title"]).split("- ")[1])
        drop_name = embed_dict["fields"][0]["value"]
        drop_value = int(embed_dict["fields"][1]["value"])
        non_clannies = int(embed_dict["fields"][3]["value"])

        dropStatus = getDropStatus(submissionId)
        if dropStatus != 2:
            try:
                name = str(embed_dict["fields"][4]["name"])
                bingo = str(embed_dict["fields"][4]["value"])
                if name == "Extra notes": #check if extra field -> bingo pushed to 5
                    bingo = str(embed_dict["fields"][5]["value"])

                if bingo == "yup":
                    bingoVal = 1
                else:
                    bingoVal = 0
            except:
                print("bingo = 0")
                bingoVal = 0

            #print(bingoVal)

            mycursor.execute(
                f"select Id,value,participants from sanity2.submissions where Id = {submissionId}"
            )
            submissionTable = mycursor.fetchall()
            #print(submissionTable)
            #print(submissionTable)
            participants = submissionTable[0][2].split(",")

            if drop_name == "Diary Carry":
                trial_count = 0
            else:
                trial_count = submissionTable[0][2].count("*")

            for member in participants:
                if member.endswith("*"): #is trial
                    if trial_count > 1: # 2trials
                        member_id = int(member.replace("*",""))
                        point_gain = min(50, math.ceil((drop_value / (len(participants)+non_clannies) * 2)))
                    else:
                        member_id = int(member.replace("*", ""))
                        point_gain = min(50, math.ceil((drop_value / (len(participants) + non_clannies))))
                else:
                    if "*" in submissionTable[0][2] and trial_count > 0:
                        member_id = int(member)
                        point_gain = min(200, math.ceil((drop_value / (len(participants)+non_clannies)) * 2))
                    else:
                        member_id = int(member)
                        point_gain = min(200, math.ceil((drop_value / (len(participants) + non_clannies))))
                insert_Point_Tracker(member_id, point_gain, now, f"{drop_name},{drop_value},{(len(participants) + non_clannies)}", submissionId)
                update_user_points(member_id,point_gain)

            insert_audit_Logs(interaction.user.id,7,now,f"{drop_name}:{drop_value}",submissionTable[0][2])

            user_id = interaction.user.id

            update_drop_submission(Id=submissionId,reviewedBy=user_id,reviewDate=now,status=2,bingoVal=bingoVal,messageUrl=interaction.message.jump_url)

            url = interaction.message.embeds[0].image.url
            async with aiohttp.ClientSession() as session:  # creates session
                async with session.get(url) as resp:  # gets image from url
                    img = await resp.read()  # reads image from response
                    with BytesIO(img) as image:  # converts to file-like object
                        new_image = discord.File(image, "image2.png")
                        embed = discord.Embed.from_dict(embed_dict)
                        embed.set_image(url="attachment://image2.png")
                        embed.color = embed.colour.green()

            await interaction.message.edit(view=None, embed=embed)
            #await interaction.response.send_message("drop accepted and points given")

    @button(label="Edit", custom_id="edit-button-2", style=discord.ButtonStyle.gray, emoji="✏️")
    async def editSubmission(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        submissionId = int(str(embed_dict["title"]).split("- ")[1])
        drop_name = embed_dict["fields"][0]["value"] #gets value from embed
        drop_value = embed_dict["fields"][1]["value"]
        non_clannies = embed_dict["fields"][3]["value"]


        modal = acceptorEditSubmissionModal(title="Edit drop submission", drop_name=drop_name, drop_value=drop_value, nonclannies=non_clannies)
        await interaction.response.send_modal(modal)


    @button(label="Delete", custom_id="acceptor-decline-button-1", style=discord.ButtonStyle.danger, emoji="✖️")
    async def removeSubmission(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        submissionId = int(str(embed_dict["title"]).split("- ")[1])
        now = datetime.datetime.now()
        user_id = interaction.user.id

        url = interaction.message.embeds[0].image.url
        async with aiohttp.ClientSession() as session:  # creates session
            async with session.get(url) as resp:  # gets image from url
                img = await resp.read()  # reads image from response
                with BytesIO(img) as image:  # converts to file-like object
                    new_image = discord.File(image, "image2.png")
                    embed = discord.Embed.from_dict(embed_dict)
                    embed.set_image(url="attachment://image2.png")
                    embed.color = embed.colour.red()

        await interaction.message.edit(view=None, embed=embed)


        update_drop_submission(Id=submissionId, reviewedBy=user_id, reviewDate=now,status=3)
        #await interaction.response.send_message("The submission has been removed")



class submissionButtons(View):  # button
    def __init__(self, author):
        super().__init__(timeout=None)
        self.value = None
        self.author = author

    # When the confirm button is pressed, set the inner value to `True` and
    # Stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    async def interaction_check(self, interaction: discord.Interaction):
        mycursor.execute(
            "select discordRoleId,name from sanity2.roles where acceptDrops = 1"
        )
        data = mycursor.fetchall()
        list = [i[0] for i in data]

        interaction_user_roleID_list = [role.id for role in interaction.user.roles]

        check = any(role in interaction_user_roleID_list for role in list)
        if check == True or (interaction.user.id == self.author.id) == True:
            value = True
        else:
            value = False

        return value

    @button(label="Looks good (Click here to send it to #posted-drops)", custom_id="Submit-drop-1", style=discord.ButtonStyle.green, emoji="✅")
    async def submitDrop(self, button: Button, interaction: discord.Interaction):

        posted_drops = get_channel("posted-drops")

        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        submissionId = int(str(embed_dict["title"]).split("- ")[1])
        drop_name = embed_dict["fields"][0]["value"]
        drop_value = int(embed_dict["fields"][1]["value"])
        non_clannies = int(embed_dict["fields"][3]["value"])
        try:
            bingo = str(embed_dict["fields"][4]["value"])
            if bingo == "yup":
                bingoVal = 1
            else:
                bingoVal = 0
        except:
            #print("broken")
            bingoVal = 0

        name_string = getDropData(submissionId)
        clannies_list = name_string.split(",")
        #print(clannies_list)

        # print(self.clannies_list)
        sql_format = f"({','.join(str(clannie) for clannie in clannies_list)})"
        #print(F"SQL FORMAT {sql_format}")

        url = interaction.message.embeds[0].image.url

        ########################################################################################
        ############ calculate points to give
        #############################################################################
        num_split_players = len(clannies_list) + non_clannies
        base_split_amount = math.ceil(drop_value / num_split_players)

        #### trial bonus - check if any trials
        mycursor.execute(
            f"select * from sanity2.users where userId in {str(sql_format)} and rankId = 1"
        )
        sql_trial_list = mycursor.fetchall()
        #print(f"SQL TRIAL LIST {sql_trial_list}")
        #print(sql_trial_list)
        trial_id_list = [id[0] for id in sql_trial_list]
        #print(f"TRAIL ID {trial_id_list}")

        #remove multiplier from certain drops
        if drop_name == "Diary Carry":
            number_of_trials = 0
        else:
            number_of_trials = len(sql_trial_list)

        #multiplier for 1 trial in raid
        if number_of_trials > 0:
            trial_multiplied_amount = base_split_amount * 2
        else:
            trial_multiplied_amount = base_split_amount

        #double points for multiple trials
        if number_of_trials > 1:
            trial_multiplier = 2
        else:
            trial_multiplier = 1

        embed_message = ""
        sql_message = []

        for clannie_id in clannies_list:  ##calculate individual point gain
            # print(clannie_id)
            if int(clannie_id) in trial_id_list:  # user is trial
                # print(f"{clannie_id} is a trial")
                cap = 50
                points = min(base_split_amount*trial_multiplier, cap)

                embed_message += f"<@{clannie_id}>(trial)+`{points}` "
                sql_message.append(f"{clannie_id}*")

            else:
                cap = 200
                points = min(trial_multiplied_amount, cap)

                embed_message += f"<@{clannie_id}>+`{points}` "
                sql_message.append(f"{clannie_id}")

        string_sql_participants = ','.join(sql_message)

        updateDropStatus(submissionId,4,string_sql_participants)

        async with aiohttp.ClientSession() as session:  # creates session
            async with session.get(url) as resp:  # gets image from url
                img = await resp.read()  # reads image from response
                with BytesIO(img) as image:  # converts to file-like object
                    new_image = discord.File(image, "image2.png")

                    embed = discord.Embed.from_dict(embed_dict)
                    embed.set_image(url="attachment://image2.png")
                    if bingoVal == 0:
                        embed.color = discord.Color.yellow()
                    else:
                        embed.color = discord.Color.nitro_pink()

                with BytesIO(img) as newIMG:  # converts to file-like object
                    new_imagest = discord.File(newIMG, "image24.png")
                    newer_embed = discord.Embed.from_dict(embed_dict)
                    newer_embed.set_image(url="attachment://image24.png")
                    newer_embed.color = discord.Color.green()


        #print(embed_message)

        posted_drops_channel = await interaction.guild.fetch_channel(posted_drops)

        embed.add_field(name="Individual points", value=embed_message[0:1023], inline=False)

        view = submissionAcceptor()

        await posted_drops_channel.send(embed=embed, file=new_image, view=view)
        await interaction.message.edit(embed=newer_embed,file=new_imagest,view=None)
        #await interaction.response.send_message("Your drop has been submitted for approval ✅", ephemeral=True)


    @button(label="Edit", custom_id="edit-button-1", style=discord.ButtonStyle.gray, emoji="✏️")
    async def editSubmission(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        submissionId = int(str(embed_dict["title"]).split("- ")[1])
        drop_name = embed_dict["fields"][0]["value"] #gets value from embed
        drop_value = embed_dict["fields"][1]["value"]
        non_clannies = embed_dict["fields"][3]["value"]


        modal = editSubmissionModal(title="Edit drop submission", drop_name=drop_name, drop_value=drop_value, nonclannies=non_clannies, author=self.author)
        await interaction.response.send_modal(modal)


    @button(label="Delete",custom_id="delete-button-1", style=discord.ButtonStyle.danger, emoji="✖️")
    async def removeSubmission(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        submissionId = int(str(embed_dict["title"]).split("- ")[1])
        updateDropStatusONLY(submissionId,5)

        await interaction.message.delete()
        await interaction.response.send_message("your submission has been removed", ephemeral=True)



class acceptorEditSubmissionModal(Modal):  # modal to edit msg
    def __init__(self, drop_name, drop_value, nonclannies, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.add_item(InputText(label="Drop name", value=f"{drop_name}",style=discord.InputTextStyle.short, max_length=100, min_length=1))
        self.add_item(InputText(label="Drop value (number only)", value=f"{drop_value}",style=discord.InputTextStyle.short, max_length=4, min_length=1))
        self.add_item(InputText(label="# of nonclannies (number only)", value=f"{nonclannies}",style=discord.InputTextStyle.short, max_length=3, min_length=1))

    async def callback(self, interaction: discord.Interaction):  # response to modal
        # await interaction.response.send_message(f"{self.children[0].value}")
        drop_name = self.children[0].value #first field value
        drop_value = self.children[1].value #NEED TO UPDATE THE CHANGED DATA!
        nonclannies = self.children[2].value #NEED TO UPDATE THE CHANGED DATA!

        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        submissionId = int(str(embed_dict["title"]).split("- ")[1])
        embed_dict['fields'][0]['value'] = drop_name
        embed_dict['fields'][1]['value'] = int(drop_value)
        embed_dict['fields'][3]['value'] = int(nonclannies)

        url = interaction.message.embeds[0].image.url

        async with aiohttp.ClientSession() as session:  # creates session
            async with session.get(url) as resp:  # gets image from url
                img = await resp.read()  # reads image from response
                with BytesIO(img) as image:  # converts to file-like object
                    new_image = discord.File(image, "image2.png")

                    embed = discord.Embed.from_dict(embed_dict)
                    embed.set_image(url="attachment://image2.png")

        view = submissionAcceptor()

        updated_name = drop_name.replace("'","\\'")
        mycursor.execute(
            f"update sanity2.submissions set value = {drop_value}, notes = '{updated_name}' where id = {submissionId}"
        )
        db.commit()

        await interaction.message.edit(embed=embed,file=new_image,view=view)  # removes button ig
        #await msg_to_edit.delete()  # deletes old msg
        await interaction.response.send_message("Drop submission has been updated", ephemeral=True)


"""
just random modal i used in another bot, didnt change anything yet"""
class editSubmissionModal(Modal):  # modal to edit msg
    def __init__(self, drop_name, drop_value, nonclannies, author, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.author = author
        self.add_item(InputText(label="Drop name", value=f"{drop_name}",style=discord.InputTextStyle.short, max_length=100, min_length=1))
        self.add_item(InputText(label="Drop value (number only)", value=f"{drop_value}",style=discord.InputTextStyle.short, max_length=4, min_length=1))
        self.add_item(InputText(label="# of nonclannies (number only)", value=f"{nonclannies}",style=discord.InputTextStyle.short, max_length=3, min_length=1))

    async def callback(self, interaction: discord.Interaction):  # response to modal
        # await interaction.response.send_message(f"{self.children[0].value}")
        drop_name = self.children[0].value #first field value
        drop_value = self.children[1].value #NEED TO UPDATE THE CHANGED DATA!
        nonclannies = self.children[2].value #NEED TO UPDATE THE CHANGED DATA!

        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        submissionId = int(str(embed_dict["title"]).split("- ")[1])
        embed_dict['fields'][0]['value'] = drop_name
        embed_dict['fields'][1]['value'] = int(drop_value)
        embed_dict['fields'][3]['value'] = int(nonclannies)

        url = interaction.message.embeds[0].image.url

        async with aiohttp.ClientSession() as session:  # creates session
            async with session.get(url) as resp:  # gets image from url
                img = await resp.read()  # reads image from response
                with BytesIO(img) as image:  # converts to file-like object
                    new_image = discord.File(image, "image2.png")

                    embed = discord.Embed.from_dict(embed_dict)
                    embed.set_image(url="attachment://image2.png")

        updated_name = drop_name.replace("'", "\\'")
        mycursor.execute(
            f"update sanity2.submissions set value = {drop_value}, notes = '{updated_name}' where Id = {submissionId}"
        )
        db.commit()

        view = submissionButtons(self.author)
        await interaction.message.edit(embed=embed,file=new_image,view=view)  # removes button ig
        #await msg_to_edit.delete()  # deletes old msg
        await interaction.response.send_message("Drop submission has been updated", ephemeral=True)


class Submit(commands.Cog):
    def __init__(self, bot):
        self.client = bot


    #bingocheck = bingoModeCheck()[1] #check if bingo turned on in DB
    #print(bingocheck)
    #if bingocheck == 0: #normal
    @discord.slash_command(guild_ids=testingservers, name="submit", description="submit your drops")
    async def submit(self, ctx: discord.ApplicationContext,
                     drop_name: discord.Option(str, "Submit drop name", autocomplete=drop_searcher),
                     drop_value: discord.Option(int, "ONLY rounded Millions - Greater of GE or pinned values", min_value=0, max_value=10000),
                     tag_clannies_here: discord.Option(str, "Mention the participants (only from sanity)",max_length=850),
                     imgur_url: discord.Option(str, "Put imgur url here! - only need to do imgur OR attachment",
                                               required=False),
                     image: discord.Option(discord.Attachment, "Attach image here - only need to do imgur OR attachment",
                                           required=False),
                     non_clannies: discord.Option(int, "How many non-clannies were split", min_value=0, max_value=100,default=0, required=False),
                     extra_note : discord.Option(str, "Add any notes that could help council (KC, scale whatever)", max_length=300, required=False)):
        """ submit big loots """
        img_counter = 0

        clannies = tag_clannies_here

        if image:
            img_counter += 1
        if imgur_url:
            img_counter += 1

        if not non_clannies:
            non_clannies = 0

        if img_counter > 0:
            clannies_list = discord.utils.raw_mentions(clannies) #gets @ tagged users in clannies field
            #print("WE GUCCI STEP 1")

            if len(clannies_list) > 0:
                # check if item drop value has a minimum
                new_drop_value = checkItemValueDrop(drop_name, drop_value)
                if new_drop_value > drop_value:
                    await ctx.send(
                        f"{ctx.author.mention} the drop value has been updated from {drop_value} to {new_drop_value} (min value from pins). If this is a mistake, edit the submission before accepting")
                    drop_value = new_drop_value

                #print("WE GUCCI STEP 2")
                sql_format = f"({','.join(str(clannie) for clannie in clannies_list)})"

                mycursor.execute(
                    f"select * from sanity2.users where userId in {str(sql_format)}"
                )
                sql_clannies_list = mycursor.fetchall()

                clannies_names = ', '.join([tupleObj[1] for tupleObj in sql_clannies_list])
                #clannies_ids_list = [tupleObj[0] for tupleObj in sql_clannies_list]
                clannies_ids_list_str = [str(tupleObj[0]) for tupleObj in sql_clannies_list]
                string_sql_participants = ",".join(clannies_ids_list_str)
                #print(clannies_ids_list)
                #sql_format = f"({','.join(str(clannie) for clannie in clannies_list)})"

                #### check if image or imgur url
                if image:
                    if str(image.content_type).startswith(("image")):
                        url = str(image)
                        image = discord.File(BytesIO(await image.read()), filename="image.png")
                    else:  # attachment not ping format)
                        await ctx.respond(f"Attachment must be an image (.jpg, .png, .jpeg, .webp or some shit)",ephemeral=True)

                if imgur_url:
                    url = str(imgur_url)
                    image = await imgurUrlSubmission(imgur_url, ctx)


                dbId = insert_drop_into_submissions(userId=ctx.author.id, typeId=1, status=1,
                                                    participants=string_sql_participants,
                                                    value=drop_value, imageUrl=url, submittedDate=datetime.datetime.now(), notes=drop_name)



                embed = greenDropsEmbed(title=f"**{ctx.author.display_name}** drop submission - {dbId}", drop_name=drop_name, drop_value=drop_value, clannies=clannies_names, nonClannies=non_clannies, extra_note=extra_note) # image=image
                embed.color = discord.Color.blue()

                view = submissionButtons(ctx.author)

                await ctx.respond(embed=embed,ephemeral=False,file=image, view=view)

                #waits 30s and checks if user sent submission for approval
                await asyncio.sleep(30)  #send message if drop not submitted or deleted
                status = getSubmissionStatus(dbId)
                if status == 1:
                    await ctx.send(f"{ctx.author.mention} press the green button if the submission looks ok 👍")



            else: #clannies tagged = 0
                await ctx.respond(f"please tag the members in the raid like **{ctx.author.mention}**, instead of using text", ephemeral=True)
        else:
            await ctx.respond(f"You need to either choose imgur URL or attach a file! https://i.imgur.com/JYYjQIb.png", delete_after=15)


    @discord.slash_command(guild_ids=testingservers, name="bingo_submit", description="submit your BINGO drops")
    async def bingo_submit(self, ctx: discord.ApplicationContext,
                     drop_name: discord.Option(str, "Submit drop name", autocomplete=bingo_drop_searcher),
                     drop_value: discord.Option(int, "ONLY rounded Millions - Greater of GE or pinned values",
                                                min_value=0, max_value=10000),
                     tag_clannies_here: discord.Option(str, "Mention the participants (only from sanity)",max_length=850),
                     imgur_url: discord.Option(str, "Put imgur url here! - only need to do imgur OR attachment", required=False),
                     image: discord.Option(discord.Attachment, "Attach image here - only need to do imgur OR attachment", required=False),
                     non_clannies: discord.Option(int, "How many non-clannies", min_value=0, max_value=100,
                                                  default=0, required=False),
                     extra_note : discord.Option(str, "Add any notes that could help council (KC, scale whatever)", max_length=300, required=False)):
        """ submit big bingo loots """

        clannies = tag_clannies_here
        #bingo difference
        #1. drop_names load
        #2. check if item choosen is from dropdown and the "else"
        #3. embed.add_field(name="Bingo",value="yup")

        drop_names = get_bingo_drop_names()

        img_counter = 0

        if image:
            img_counter += 1
        if imgur_url:
            img_counter += 1

        if not non_clannies:
            non_clannies = 0

        if drop_name in [str(drop) for drop in drop_names]:
            if img_counter > 0:
                clannies_list = discord.utils.raw_mentions(clannies)  # gets @ tagged users in clannies field
                # print("WE GUCCI STEP 1")

                if len(clannies_list) > 0:
                    #check if item drop value has a minimum
                    new_drop_value = checkItemValueDrop(drop_name, drop_value)
                    if new_drop_value > drop_value:
                        await ctx.send(
                            f"{ctx.author.mention} the drop value has been updated from {drop_value} to {new_drop_value} (min value from pins). If this is a mistake, edit the submission before accepting")
                        drop_value = new_drop_value

                    # print("WE GUCCI STEP 2")
                    sql_format = f"({','.join(str(clannie) for clannie in clannies_list)})"

                    mycursor.execute(
                        f"select * from sanity2.users where userId in {str(sql_format)}"
                    )
                    sql_clannies_list = mycursor.fetchall()

                    clannies_names = ', '.join([tupleObj[1] for tupleObj in sql_clannies_list])
                    # clannies_ids_list = [tupleObj[0] for tupleObj in sql_clannies_list]
                    clannies_ids_list_str = [str(tupleObj[0]) for tupleObj in sql_clannies_list]
                    string_sql_participants = ",".join(clannies_ids_list_str)
                    # print(clannies_ids_list)
                    # sql_format = f"({','.join(str(clannie) for clannie in clannies_list)})"

                    #### check if image or imgur url
                    if image:
                        if str(image.content_type).startswith(("image")):
                            url = str(image)
                            image = discord.File(BytesIO(await image.read()), filename="image.png")
                        else:  # attachment not ping format)
                            await ctx.respond(f"Attachment must be an image (.jpg, .png, .jpeg, .webp or some shit)",
                                              ephemeral=True)

                    if imgur_url:
                        url = str(imgur_url)
                        image = await imgurUrlSubmission(imgur_url, ctx)

                    dbId = insert_drop_into_submissions(userId=ctx.author.id, typeId=1, status=1,
                                                        participants=string_sql_participants,
                                                        value=drop_value, imageUrl=url,
                                                        submittedDate=datetime.datetime.now(), notes=drop_name)

                    embed = greenDropsEmbed(title=f"**{ctx.author.display_name}** drop submission - {dbId}",
                                            drop_name=drop_name, drop_value=drop_value, clannies=clannies_names,
                                            nonClannies=non_clannies, extra_note=extra_note)  # image=image
                    embed.color = discord.Color.nitro_pink()
                    embed.add_field(name="Bingo", value="yup")

                    view = submissionButtons(ctx.author)

                    await ctx.respond(embed=embed, ephemeral=False, file=image, view=view)

                    # waits 30s and checks if user sent submission for approval
                    await asyncio.sleep(30)  # send message if drop not submitted or deleted
                    status = getSubmissionStatus(dbId)
                    if status == 1:
                        await ctx.send(f"{ctx.author.mention} press the green button if the submission looks ok 👍")



                else:  # clannies tagged = 0
                    await ctx.respond(
                        f"please tag the members in the raid like **{ctx.author.mention}**, instead of using text",
                        ephemeral=True)
            else:
                await ctx.respond(f"You need to either choose imgur URL or attach a file! https://i.imgur.com/JYYjQIb.png" , delete_after=15)
        else:  # not drop from bingo_items list
            await ctx.respond("Make sure to pick a drop from the dropdown",
                              ephemeral=True)

def setup(bot):
    bot.add_cog(Submit(bot))

