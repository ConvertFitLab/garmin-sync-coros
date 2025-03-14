import logging
import os
from enum import Enum, auto

import garth

from garmin_url_dict import GARMIN_URL_DICT
from config import SYNC_CONFIG, GARMIN_FIT_DIR

logger = logging.getLogger(__name__)


class GarminClient:
    def __init__(self, email, password, auth_domain):
        self.auth_domain = auth_domain
        self.email = email
        self.password = password
        self.garthClient = garth

    ## 登录装饰器
    def login(func):
        def ware(self, *args, **kwargs):
            try:
                garth.client.username
            except Exception:
                logger.warning("Garmin is not logging in or the token has expired.")
                if self.auth_domain and str(self.auth_domain).upper() == "CN":
                    self.garthClient.configure(domain="garmin.cn")
                self.garthClient.login(self.email, self.password)
            return func(self, *args, **kwargs)

        return ware

    @login
    def download(self, path, **kwargs):
        return self.garthClient.download(path, **kwargs)

    @login
    def connectapi(self, path, **kwargs):
        return self.garthClient.connectapi(path, **kwargs)

    ## 获取运动
    def getActivities(self, start: int, limit: int):
        params = {"start": str(start), "limit": str(limit)}
        activities = self.connectapi(path=GARMIN_URL_DICT["garmin_connect_activities"], params=params)
        return activities;

    ## 获取所有运动
    def getAllActivities(self):
        all_activities = []
        start = 0
        # 起始同步时间
        sync_start_time_ts = int(SYNC_CONFIG["GARMIN_START_TIME"]) if SYNC_CONFIG["GARMIN_START_TIME"].strip() else 0
        while True:
            # 当start超过10000时接口请求返回http 400
            # if start >= 10000:
            #     return all_activities
            activityInfoList = self.getActivities(start=start, limit=100)
            activityList = []
            for activityInfo in activityInfoList:
                beginTimestamp = activityInfo["beginTimestamp"]
                if beginTimestamp < sync_start_time_ts:
                    if len(activityList) > 0:
                        all_activities.extend(activityList)
                    return all_activities
                activityList.append(activityInfo)
            if len(activityList) > 0:
                all_activities.extend(activityList)
            else:
                return all_activities
            start += 100

    ## 下载原始格式的运动
    def downloadFitActivity(self, activity):
        download_fit_activity_url_prefix = GARMIN_URL_DICT["garmin_connect_fit_download"]
        download_fit_activity_url = f"{download_fit_activity_url_prefix}/{activity}"
        response = self.download(download_fit_activity_url)
        return response

    @login
    def upload_activity(self, activity_path: str):
        """Upload activity in fit format from file."""
        # This code is borrowed from python-garminconnect-enhanced ;-)

        file_base_name = os.path.basename(activity_path)
        file_extension = file_base_name.split(".")[-1]
        allowed_file_extension = (
                file_extension.upper() in ActivityUploadFormat.__members__
        )

        if allowed_file_extension:
            files = {
                "file": (file_base_name, open(activity_path, "rb" or "r")),
            }
            url = GARMIN_URL_DICT["garmin_connect_upload"]
            return self.garthClient.client.post("connectapi", url, files=files, api=True)
        else:
            pass

    @login
    def upload_activity_via_file(self, file, file_base_name):
        files = {
            "file": (file_base_name, file),
        }
        url = GARMIN_URL_DICT["garmin_connect_upload"]
        return self.garthClient.client.post("connectapi", url, files=files, api=True)

    @login
    def upload_to_coros(self, corosClient, db):
        all_activities = self.getAllActivities()
        if all_activities == None or len(all_activities) == 0:
            logger.warning("has no garmin activities.")
            exit()
        for activity in all_activities:
            activity_id = activity["activityId"]
            db.saveActivity(activity_id, 'garmin')

        un_sync_id_list = db.getUnSyncActivity('garmin')
        if un_sync_id_list == None or len(un_sync_id_list) == 0:
            logger.warning("has no un sync garmin activities.")
            exit()
        logger.warning(f"has {len(un_sync_id_list)} un sync garmin activities.")
        for un_sync_id in un_sync_id_list:
            try:
                file = self.downloadFitActivity(un_sync_id)
                file_path = os.path.join(GARMIN_FIT_DIR, f"{un_sync_id}.zip")
                with open(file_path, "wb") as fb:
                    fb.write(file)
                    logger.warning(f"loaded garmin {un_sync_id} {file_path}.")
                logger.warning(f"uploading garmin {un_sync_id} {file_path}.")
                upload_result = corosClient.uploadActivity(file_path)

                if upload_result == '0000':
                    db.updateSyncStatus(un_sync_id, 'garmin')
                    logger.warning(f"sync garmin to coros {un_sync_id} {file_path} success.")
            except Exception as err:
                print(err)
                db.updateExceptionSyncStatus(un_sync_id, 'garmin')
                logger.warning(f"sync garmin ${un_sync_id} exception.")

    @login
    def download_to_local(self):
        all_activities = self.getAllActivities()
        if all_activities == None or len(all_activities) == 0:
            logger.warning("has no garmin activities.")
            exit()
        for activity in all_activities:
            activity_id = activity["activityId"]
            try:
                file = self.downloadFitActivity(activity_id)
                file_path = os.path.join(GARMIN_FIT_DIR, f"{activity_id}.zip")
                with open(file_path, "wb") as fb:
                    fb.write(file)
                    logger.warning(f"loaded garmin {activity_id} {file_path}.")
            except Exception as err:
                print(err)


class ActivityUploadFormat(Enum):
    FIT = auto()
    GPX = auto()
    TCX = auto()

class GarminNoLoginException(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, status):
        """Initialize."""
        super(GarminNoLoginException, self).__init__(status)
        self.status = status
