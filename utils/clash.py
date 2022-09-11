import os
import coc
from datetime import datetime
from datetime import timedelta
import pytz
utc = pytz.utc

from dotenv import load_dotenv
load_dotenv()

COC_EMAIL = os.getenv("COC_EMAIL")
COC_PASSWORD = os.getenv("COC_PASSWORD")
DB_LOGIN = os.getenv("DB_LOGIN")
LINK_API_USER = os.getenv("LINK_API_USER")
LINK_API_PW = os.getenv("LINK_API_PW")

from disnake import utils

import certifi
ca = certifi.where()

import motor.motor_asyncio
client = motor.motor_asyncio.AsyncIOMotorClient(DB_LOGIN)
import disnake


def create_weekends():
    weekends = []
    for x in range(0, 7):

        now = datetime.utcnow().replace(tzinfo=utc)
        now = now - timedelta(x * 7)
        current_dayofweek = now.weekday()
        if (current_dayofweek == 4 and now.hour >= 7) or (current_dayofweek == 5) or (current_dayofweek == 6) or (
                current_dayofweek == 0 and now.hour < 7):
            if current_dayofweek == 0:
                current_dayofweek = 7
            fallback = current_dayofweek - 4
            raidDate = (now - timedelta(fallback)).date()
            weekends.append(str(raidDate))
        else:
            forward = 4 - current_dayofweek
            raidDate = (now + timedelta(forward)).date()
            weekends.append(str(raidDate))
    return weekends