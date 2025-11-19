import os
import time
import argparse
import logging

logger = logging.getLogger(__name__)
# 此处无需填值，方便后面的for in根据这里的key从环境变量里面取值即可
SYNC_CONFIG = {
    'SOURCE': 'GARMIN',
    'GARMIN_EMAIL': '',
    'GARMIN_PASSWORD': '',
    'GARMIN_AUTH_DOMAIN': '',
    "GARMIN_START_TIME": '',
    "COROS_EMAIL": '',
    "COROS_PASSWORD": '',
    "COROS_START_TIME": '',
    "DB_NAME": 'activity.db'
}


def get_argv():
    parser = argparse.ArgumentParser()
    parser.add_argument("SOURCE", help="模式", default="GARMIN")
    parser.add_argument("--GARMIN_EMAIL", default="")  #  可选参数以--开头
    parser.add_argument("--GARMIN_PASSWORD", default="")
    parser.add_argument("--GARMIN_AUTH_DOMAIN", default="")
    parser.add_argument("--GARMIN_START_TIME", default="")
    parser.add_argument("--COROS_EMAIL", default="")
    parser.add_argument("--COROS_PASSWORD", default="")
    parser.add_argument("--COROS_START_TIME", default="")
    parser.add_argument("--DB_NAME", default="")
    return parser.parse_args()


argv = get_argv()
# 首先读取 命令行参数，再取面板变量 或者 github action 运行变量
for k in SYNC_CONFIG:
    if argv.__dict__.get(k):
        SYNC_CONFIG[k] = argv.__dict__.get(k)
        logger.warning(f"fill config value {k} = {str(SYNC_CONFIG[k])} from argv")
    elif os.getenv(k):
        SYNC_CONFIG[k] = os.getenv(k)
        logger.warning(f"fill config value {k} = {len(SYNC_CONFIG[k])} from env")

# getting content root directory
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)

GARMIN_FIT_DIR = os.path.join(parent, "garmin-fit")
COROS_FIT_DIR = os.path.join(parent, "coros-fit")

DB_DIR = os.path.join(parent, "db")
