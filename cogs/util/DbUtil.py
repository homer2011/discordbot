from discord.ext import commands
import pandas as pd
from ..handlers.DatabaseHandler import mycursor, db

class OtherUtil(commands.Cog):
    def __init__(self, bot):
        self.client = bot


    """@commands.command() #inserts data from local excel file to db
    async def insertShitTodb(self, ctx):
        #Sync from sheets with local file
        if ctx.author.id == 228143014168625153:
            data = pd.read_excel(r'Sanity Ranks v2.xlsx')
            df = pd.DataFrame(data, columns=["Name","Total","Join date", "Main RSN", "Alt RSN"])

            names = df['Name'].unique()

            #print(names)
            placeholderId = 1
            for name in names:
                if not str(name) == "nan":
                    #points = (df.loc[df['Name'] == name, 'Total'].sum())
                    try:
                        points = df.loc[df['Name'] == name].iloc[0]['Total']
                    except:
                        print(F"POINT ERROR ON {name} =============")
                        points = 0
                    join_date = df.loc[df['Name'] == name].iloc[0]['Join date']
                    if str(join_date) == "nan" or str(join_date) == "NaT" or str(join_date) == "None" or not join_date:
                        join_date = None
                    else:
                        join_date = str(join_date)
                        join_date = f"'{join_date.replace('/','-')}'"

                    if name:

                        main_rsn = df.loc[df['Name'] == name].iloc[0]['Main RSN']
                        if str(main_rsn) == "nan":
                            main_rsn = None
                        alt_rsn =df.loc[df['Name'] == name].iloc[0]['Alt RSN']
                        if str(alt_rsn) == "nan":
                            alt_rsn == None
                        test = f"{name} has {points} points, join date {join_date}, main rsn = {main_rsn} alt rsn = {alt_rsn}"
                        print(test)
                        mycursor.execute(
                            f"select * from sanity2.users where displayName like '{name}'"
                        )
                        table = mycursor.fetchall()

                        temp_id = 105
                        print("===============================")
                        print(name)
                        if len(table) == 0: #user not in table: aka retired
                            try:
                                mycursor.execute(
                                    "INSERT INTO sanity2.users (userId, displayName, mainRSN, altRSN, rankId, points, isActive, leaveDate, referredBy, birthday) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                    (temp_id, name, main_rsn, alt_rsn, 0, points, 0, None, None, None))
                                db.commit()
                            except:
                                print(f"{name} SUX ASS")

                        elif len(table) == 1: #user in table
                            try:
                                mycursor.execute(
                                    f"update sanity2.users set points = {points} where displayName like '{name}'"
                                )
                            except:
                                print("POINTS BROKEN")

                            try:
                                mycursor.execute(
                                    f"update sanity2.users set joinDate = {join_date} where displayName like '{name}'"
                                )
                            except:
                                print("JOIN DATE BROKEN")

                            try:
                                mycursor.execute(
                                    f"update sanity2.users set mainRSN = '{main_rsn}' where displayName like '{name}'"
                                )
                            except:
                                print("MAIN RSN BROKEN")

                            try:
                                mycursor.execute(
                                    f"update sanity2.users set altRSN = '{alt_rsn}' where displayName like '{name}'"
                                )
                            except:
                                print("ALT RSN BROKEN")



                            db.commit()
                        else:
                            print(f"something with with {name}")

                        temp_id += 1

            await ctx.send("xD")"""



def setup(bot):
    bot.add_cog(OtherUtil(bot))