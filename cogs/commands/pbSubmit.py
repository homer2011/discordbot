import discord
from discord.ext import commands
from discord.ui import View, Modal, InputText, Button, button
from ..handlers.DatabaseHandler import testingservers, get_bosses, mycursor, get_channel, insert_Personal_Best,update_Personal_best, insert_audit_Logs, accept_decline_personalBest
from ..handlers.EmbedHandler import embedVariable
from ..util.CoreUtil import get_scale_text, uploadfile
from .dropSubmit import imgurUrlSubmission
import aiohttp
from discord.commands import option
from io import BytesIO
import datetime
import asyncio

def getPbStatus(submissionId):
    mycursor.execute(
        f"select status from sanity2.personalbests where submissionId = {submissionId}"
    )
    data = mycursor.fetchall()
    if len(data) > 0:
        return data[0][0]
    else:
        return 0

def getPBSubmissionStatus(id):
    mycursor.execute(
        f"select status from sanity2.personalbests where submissionId = {id}"
    )
    status = mycursor.fetchall()[0][0]

    return status

async def boss_searcher(ctx : discord.AutocompleteContext):
    """
        Returns a list of matching DROPS from the DROPS table list."""
    boss_names, boss_ids = get_bosses()

    #print(ctx.options.values())

    return [
        boss for boss in boss_names if (ctx.value.lower() in boss.lower())
    ]

class pbsubmissionAcceptor(View):  # for council / drop acceptors etc in #posted-drops
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

    @button(label="Accept pb", custom_id="acceptor-accept-button-2" ,style=discord.ButtonStyle.green, emoji="✅")
    async def acceptPb(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        now = datetime.datetime.now()
        submissionId = int(str(embed_dict["title"]).split("- ")[1])

        mycursor.execute(
            f"select members from sanity2.personalbests where submissionId = {submissionId}"
        )
        table = mycursor.fetchall()[0][0]
        #print(table)

        boss_name = embed_dict["fields"][0]["value"]
        scale = int(embed_dict["fields"][1]["value"])
        time = embed_dict["fields"][2]["value"]
        insert_audit_Logs(interaction.user.id,7,now,f"{boss_name}:{scale}:{time}",table)

        user_id = interaction.user.id

        accept_decline_personalBest(submissionId=submissionId,reviewedBy=user_id,reviewedDate=now,status=2)

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

        await interaction.message.edit(view=None)



    @button(label="Decline", custom_id="acceptor-decline-button-2", style=discord.ButtonStyle.danger, emoji="✖️")
    async def removePbSubmission(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        submissionId = int(str(embed_dict["title"]).split("- ")[1])
        now = datetime.datetime.now()
        user_id = interaction.user.id

        mycursor.execute(
            f"select members from sanity2.personalbests where submissionId = {submissionId}"
        )
        table = mycursor.fetchall()[0][0]
        #print(table)

        boss_name = embed_dict["fields"][0]["value"]
        scale = int(embed_dict["fields"][1]["value"])
        time = embed_dict["fields"][2]["value"]
        insert_audit_Logs(interaction.user.id, 3, now, f"{boss_name}:{scale}:{time}", table)

        insert_audit_Logs(interaction.user.id, 3, now, f"{boss_name}:{scale}:{time}", table)
        accept_decline_personalBest(submissionId=submissionId,reviewedBy=user_id,reviewedDate=now,status=3)

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
            "select discordRoleId,name from sanity2.roles where adminCommands = 1"
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

    @button(label="Looks good (Click here to send it to #posted-pbs)", style=discord.ButtonStyle.green, emoji="✅")
    async def submbitpb(self, button: Button, interaction: discord.Interaction):
        posted_drops = get_channel("posted-pbs")

        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        submissionId = int(str(embed_dict["title"]).split("- ")[1])

        url = interaction.message.embeds[0].image.url

        async with aiohttp.ClientSession() as session:  # creates session
            async with session.get(url) as resp:  # gets image from url
                img = await resp.read()  # reads image from response
                with BytesIO(img) as image:  # converts to file-like object
                    new_image = discord.File(image, "image2.png")

                    embed = discord.Embed.from_dict(embed_dict)
                    embed.set_image(url="attachment://image2.png")
                    embed.color = discord.Color.yellow()

        fileName = f"pb-{interaction.user.id}-{submissionId}-{str(datetime.datetime.now())}.png"
        img_url = str(await uploadfile(url, fileName)).replace(" ", "%20")
        update_Personal_best(submissionId=submissionId, status=1,imageUrl=img_url)


        posted_drops_channel = await interaction.guild.fetch_channel(posted_drops)

        view = pbsubmissionAcceptor()

        await posted_drops_channel.send(embed=embed, file=new_image, view=view)

        async with aiohttp.ClientSession() as session:  # creates session
            async with session.get(url) as resp:  # gets image from url
                img = await resp.read()  # reads image from response
                with BytesIO(img) as image:  # converts to file-like object
                    new_image2 = discord.File(image, "image3.png")

                    embed = discord.Embed.from_dict(embed_dict)
                    embed.set_image(url="attachment://image3.png")
                    embed.color = discord.Color.green()

        await interaction.message.edit(view=None, embed=embed, file=new_image2)
        await interaction.response.send_message("Your pb has been submitted for approval ✅", ephemeral=True)
        #await interaction.message.delete()


    @button(label="Delete", style=discord.ButtonStyle.danger, emoji="✖️")
    async def removeSubmission(self, button: Button, interaction: discord.Interaction):
        channel = interaction.message.channel
        msg_to_edit = await channel.fetch_message(interaction.message.id)
        for embed in msg_to_edit.embeds:
            embed_dict = embed.to_dict()

        submissionId = int(str(embed_dict["title"]).split("- ")[1])

        update_Personal_best(submissionId=submissionId, status=5)

        await interaction.message.delete()
        await interaction.response.send_message("your submission has been removed", ephemeral=True)

class PbSubmit(commands.Cog):
    def __init__(self, bot):
        self.client = bot

    @discord.slash_command(guild_ids=testingservers, name="pbsubmission", description="submit your pbs")
    async def pbSubmission(self, ctx: discord.ApplicationContext,
                     boss: discord.Option(str, "Boss or raid name",autocomplete=boss_searcher),
                     scale : discord.Option(int, "How many peeps (1 if solo)", min_value=1, max_value=100),
                     clannies : discord.Option(str, "Participants",max_length=850),
                     time_minutes: discord.Option(int, "Minutes as \"24\" from 24:30.6", min_value=0, max_value=520),
                     time_seconds : discord.Option(int, "Seconds as \"30\" from 24:30.6", min_value=0, max_value=59),
                     time_miliseconds : discord.Option(int, "Miliseconds as \"6\" or \"60\" from 24:30.6", min_value=0, max_value=80),
                     imgur_url: discord.Option(str, "Put imgur url here! - only need to do imgur OR attach",required=False),
                     image: discord.Option(discord.Attachment,"Attach image here - only need to do imgur OR attach", required=False),
                     extra_note : discord.Option(str, "Add any notes that could help council (KC, scale whatever)", max_length=300, required=False)):

        #drop_submissions_id = get_channel("drop-submissions")
        #if ctx.channel.id == drop_submissions_id: #only allow drops in correct channel
        #print(str(image))
        await ctx.defer()

        img_counter = 0

        if image:
            img_counter += 1
        if imgur_url:
            img_counter += 1


        if img_counter > 0:
            #potential errors
            # 1. boss name not chosen from list -> check if boss in db, return db id or error
            # 2. scale != number of clannies -> check -> return error

            boss_names, boss_ids = get_bosses()
            clannies_id_list = discord.utils.raw_mentions(clannies)
            #print(clannies_id_list)
            #check if @ mentions are in clan
            if len(clannies_id_list) > 0:
                sql_format = f"({','.join(str(clannie) for clannie in clannies_id_list)})"

                mycursor.execute(
                    f"select * from sanity2.users where userId in {str(sql_format)}"
                )
                sql_clannies_list = mycursor.fetchall()

                clannies_names = ', '.join([tupleObj[1] for tupleObj in sql_clannies_list]) #discord display names
                clannies_ids_list = [tupleObj[0] for tupleObj in sql_clannies_list]
                clannies_ids_list.sort()
                sql_format_ids = ','.join([str(id) for id in clannies_ids_list])

                if boss in boss_names:
                    bossId = boss_ids[boss_names.index(boss)]

                    if len(clannies_ids_list) == scale:
                        ##format time
                        if len(str(time_minutes)) == 1:
                            time_minutes = f"0{time_minutes}"
                        if len(str(time_seconds)) == 1:
                            time_seconds = f"0{time_seconds}"
                        if len(str(time_miliseconds)) == 1:
                            time_miliseconds = f"{time_miliseconds}0"


                        formatted_time = f"{time_minutes}:{time_seconds}.{time_miliseconds}"

                        if image:
                            image_upload_url = image.url
                        else:
                            image_upload_url = imgur_url



                        submissionId = insert_Personal_Best(ctx.author.id, sql_format_ids, bossId, 4, scale,
                                                            formatted_time, datetime.datetime.now(), image_upload_url)

                        if image:
                            if str(image.content_type).startswith(("image")):
                                image = discord.File(BytesIO(await image.read()), filename="image.png")
                            else:  # attachment not ping format)
                                await ctx.respond(
                                    f"Attachment must be an image (.jpg, .png, .jpeg, .webp or some shit)",
                                    ephemeral=True)

                        if imgur_url:
                            image = await imgurUrlSubmission(imgur_url, ctx)


                        view = submissionButtons(ctx.author)

                        embed = embedVariable(f"{ctx.author.display_name} pb submission - {submissionId}", discord.Colour.green() ,("Boss",f"{boss}"),("Scale", scale), ("Time", formatted_time), ("Clannies", clannies_names), ("Extra note",extra_note))
                        embed.color = discord.Color.yellow()

                        await ctx.respond(embed=embed, file=image,view=view, ephemeral=False)

                        await asyncio.sleep(25)  # send message if drop not submitted or deleted
                        status = getPBSubmissionStatus(submissionId)
                        if status == 4:
                            await ctx.send(
                                f"{ctx.author.mention} press the green button if the submission looks ok 👍")

                    else:
                        await ctx.respond(f"Scale `{scale}` does not match for members: `{clannies_names}`", ephemeral=True)
                else: #boss not select from dropdown
                    await ctx.respond(f"{str(boss).replace('@','')} is not on the downdrop list! Make sure to pick a boss from the list",ephemeral=True)
            else:
                await ctx.respond(f"You have to **mention** participants in clannies field like {ctx.author.mention}", ephemeral=True)
        else:
            await ctx.respond(f"You need to either choose imgur URL or attach a file! https://i.imgur.com/JYYjQIb.png", delete_after=15)




def setup(bot):
    bot.add_cog(PbSubmit(bot))