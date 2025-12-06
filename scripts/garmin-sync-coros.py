import os
import sys
import logging
import asyncio
logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.split(os.path.abspath(__file__))[0]  # 当前目录
garmin_path = CURRENT_DIR + os.path.sep + 'garmin'
coros_path = CURRENT_DIR + os.path.sep + 'coros'
sys.path.append(garmin_path)
sys.path.append(coros_path)

from config import SYNC_CONFIG, DB_DIR, GARMIN_FIT_DIR, COROS_FIT_DIR
from garmin.garmin_client import GarminClient
from activity_db import ActivityDB
from coros.coros_client import CorosClient


def init(activity_db):
    ## 判断RQ数据库是否存在
    print(os.path.join(DB_DIR, activity_db.db_name))
    if not os.path.exists(os.path.join(DB_DIR, activity_db.db_name)):
        ## 初始化建表
        activity_db.initDB()
    if not os.path.exists(GARMIN_FIT_DIR):
        os.mkdir(GARMIN_FIT_DIR)
    if not os.path.exists(COROS_FIT_DIR):
        os.mkdir(COROS_FIT_DIR)


def getClient():
    ## db 名称
    db_name = SYNC_CONFIG["DB_NAME"]
    ## 建立DB链接
    activity_db = ActivityDB(db_name)
    ## 初始化DB位置和下载文件位置
    init(activity_db)

    PUSH_TOKEN = SYNC_CONFIG["PUSH_TOKEN"]

    GARMIN_EMAIL = SYNC_CONFIG["GARMIN_EMAIL"]
    GARMIN_PASSWORD = SYNC_CONFIG["GARMIN_PASSWORD"]
    GARMIN_AUTH_DOMAIN = SYNC_CONFIG["GARMIN_AUTH_DOMAIN"]
    garminClient = GarminClient(GARMIN_EMAIL, GARMIN_PASSWORD, GARMIN_AUTH_DOMAIN, PUSH_TOKEN)

    COROS_EMAIL = SYNC_CONFIG["COROS_EMAIL"]
    COROS_PASSWORD = SYNC_CONFIG["COROS_PASSWORD"]
    corosClient = CorosClient(COROS_EMAIL, COROS_PASSWORD, PUSH_TOKEN)

    return garminClient, corosClient, activity_db


# 将佳明运动记录导入到高驰
def garmin_to_cors():
    garminClient, corosClient, db = getClient()
    garminClient.upload_to_coros(corosClient, db)

# 将佳明运动记录保存下载到本地
def garmin_to_local():
    garminClient, corosClient, db = getClient()
    garminClient.download_to_local()

# 将佳明运动记录保存下载后转换
def garmin_to_convert():
    garminClient, corosClient, db = getClient()
    garminClient.download_to_convert(db)

# 将高驰运动记录导入到佳明
def coros_to_garmin():
    garminClient, corosClient, db = getClient()
    corosClient.uploadToGarmin(garminClient, db)

# 将高驰运动记录保存下载后转换
def coros_to_convert():
    garminClient, corosClient, db = getClient()
    corosClient.upload_to_convert(db)


if __name__ == "__main__":
    # 未配置第一个参数则默认按照GARMIN模式运行
    source = SYNC_CONFIG["SOURCE"]
    logger.warning(f"data source: {str(source)}")
    if source == 'COROS':
        coros_to_garmin()
    elif source == 'COROS2CONVERT':
        coros_to_convert()
    elif source == 'GARMIN2LOCAL':
        garmin_to_local()
    elif source == 'GARMIN2CONVERT':
        garmin_to_convert()
    else:
        garmin_to_cors()
