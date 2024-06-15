from discord.ext import commands
import datetime
import requests
import b2sdk.v2 as b2
from io import BytesIO

##backblaze connection
info = b2.InMemoryAccountInfo()
b2_api = b2.B2Api(info)
application_key_id = "2e6e7f484114"
application_key = "005c2bb5aeff1f1d5d6c1ce931e535bb12f4e45515"
b2_api.authorize_account("production", application_key_id, application_key)
bucket = b2_api.get_bucket_by_id("22de363e576fe41884a10114")

async def uploadfile(url, filename):
    icon = requests.get(url)
    bytes = BytesIO(icon.content)
    readable = bytes.read()
    uploaded_file = bucket.upload_bytes(data_bytes=readable, file_name=filename)
    #print(uploaded_file)
    print("UploadedFile - test")
    friendly_urL = f"https://f005.backblazeb2.com/file/sanityimages/{filename}"
    return friendly_urL


def utc_time():
    now = datetime.datetime.utcnow()
    formatted = now.strftime("%H:%M %d-%b")


    return f"UTC: {formatted}"


def format_thousands(number):
    number = f"{number:,}"

    return number

def get_scale_text_reverse(scale : str):
    if scale == "Solo":
        return 1
    elif scale == "Duo":
        return 2
    elif scale == "Trio":
        return 3
    else:
        return int(scale.replace("-man",""))

def get_scale_text(scale:int):
    if scale == 1:
        return "Solo"
    elif scale == 2:
        return "Duo"
    elif scale == 3:
        return "Trio"
    else:
        return f"{scale}-man"

def get_diary_difficulty(difficulty : int):
    if difficulty == 1:
        return "Easy"
    elif difficulty == 2:
        return "Medium"
    elif difficulty == 3:
        return "Hard"
    elif difficulty == 4:
        return "Elite"
    elif difficulty == 5:
        return "Master"
    else:
        return "Unknown"


class CoreUtil(commands.Cog):
    def __init__(self, bot):
        self.client = bot


def setup(bot):
    bot.add_cog(CoreUtil(bot))


