import os
import sys

import urllib3
import json
import hashlib
import logging

from config import SYNC_CONFIG, COROS_FIT_DIR
import re
import time

# 1. 获取当前文件 (aa.py) 的绝对路径
# 2. os.path.dirname() 获取它所在的目录 (a/ 的绝对路径)
# 3. 再一次 os.path.dirname() 获取项目根目录 (my_project/ 的绝对路径)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 4. 将项目根目录添加到 Python 的模块搜索路径中
sys.path.append(project_root)
import convert_util

logger = logging.getLogger(__name__)

class CorosClient:
    
    def __init__(self, email, password) -> None:
        
        self.email = email
        self.password = password
        self.req = urllib3.PoolManager()
        self.accessToken = None
        self.userId = None
    
    ## 登录接口
    def login(self):
        
        login_url = "https://teamcnapi.coros.com/account/login"

        login_data = {
            "account": self.email,
            "pwd": hashlib.md5(self.password.encode()).hexdigest(),  ##MD5加密密码
            "accountType": 2,
        }
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.39 Safari/537.36",
            "referer": "https://trainingcn.coros.com/",
            "origin": "https://trainingcn.coros.com/",
        }

        login_body = json.dumps(login_data)
        response = self.req.request('POST', login_url, body=login_body, headers=headers)

        login_response = json.loads(response.data)
        login_result = login_response["result"]
        if login_result != "0000":
            raise CorosLoginError("高驰登录异常，异常原因为：" + login_response["message"])

        accessToken = login_response["data"]["accessToken"]
        userId = login_response["data"]["userId"]
        self.accessToken = accessToken
        self.userId = userId

    ## 上传运动
    def uploadActivity(self, file_path):
        ## 判断Token 是否为空
        if self.accessToken == None:
            self.login()

        upload_url = "https://teamcnapi.coros.com/activity/fit/import"

        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.39 Safari/537.36",
            "referer": "https://trainingcn.coros.com/",
            "origin": "https://trainingcn.coros.com/",
            "accesstoken": self.accessToken,
        }

        with open(file_path, 'rb') as f:
            file_data = f.read()
        try:
            response = self.req.request(
                method='POST',
                url=upload_url,
                fields={'sportData': (os.path.basename(file_path), file_data),
                        "jsonParameter": """{"source":1,"timezone":32}"""},
                headers=headers
            )
            upload_response = json.loads(response.data)
            upload_result = upload_response["result"]
            return upload_result
        except Exception as err:
            exit()

    ## 登录装饰器
    def loginCheck(func):
        def ware(self, *args, **kwargs):
            ## 判断Token 是否为空
            if self.accessToken == None:
                self.login()

            return func(self, *args, **kwargs)

        return ware

    def getHeaders(self):
        headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.39 Safari/537.36",
            "referer": "https://trainingcn.coros.com/",
            "origin": "https://trainingcn.coros.com/",
            "accesstoken": self.accessToken,
        }
        return headers

    ## 获取下载链接
    @loginCheck
    def getDownloadUrl(self, labelId,  sportType, fileType = 4):
        down_url = f'https://teamcnapi.coros.com/activity/detail/download?labelId={labelId}&sportType={sportType}&fileType=4'
        try:
            response = self.req.request(
                method='POST',
                url=down_url,
                fields={},
                headers=self.getHeaders()
            )
            down_response = json.loads(response.data)
            if down_response.get("data") and down_response["data"]["fileUrl"]:
                return down_response["data"]["fileUrl"]
            else:
                return None
        except Exception as err:
            exit()

    ## 下载
    @loginCheck
    def download(self, url):
        try:
            response = self.req.request(
                method='GET',
                url=url,
                fields={},
                headers=self.getHeaders()
            )
            return response
        except Exception as err:
            exit()

    ## 获取运动
    @loginCheck
    def getActivities(self, pageNumber: int, pageSize: int):

        listUrl = f'https://teamcnapi.coros.com/activity/query?size={str(pageSize)}&pageNumber={str(pageNumber)}&modeList='

        try:
            response = self.req.request(
                method='GET',
                url=listUrl,
                fields={},
                headers=self.getHeaders()
            )
            responseData = json.loads(response.data)
            data = responseData.get('data', {})
            dataList = data.get('dataList', [])
            return dataList
        except Exception as err:
            exit()

    ## 获取所有运动
    def getAllActivities(self):
        all_urlList = []
        pageNumber = 1
        # 起始同步时间
        sync_start_time_ts = int(SYNC_CONFIG["COROS_START_TIME"]) if SYNC_CONFIG["COROS_START_TIME"].strip() else 0
        while True:
            logger.warning(f"get coros activities of pageNumber {pageNumber}.")
            activityInfoList = self.getActivities(pageNumber=pageNumber, pageSize=100)
            urlList = []
            for activityInfo in activityInfoList:
                labelId = activityInfo["labelId"]
                sportType = activityInfo["sportType"]
                startTime = int(f"{activityInfo['startTime']}000")
                # 同步起始时间之前的历史纪录不再查询及同步
                if startTime < sync_start_time_ts:
                    if len(urlList) > 0:
                        all_urlList.extend(urlList)
                    return all_urlList
                
                activityDownloadUrl = self.getDownloadUrl(labelId, sportType)
                if (activityDownloadUrl):
                    urlList.append((labelId, activityDownloadUrl, startTime)) # 已元祖形式存储
            if len(urlList) > 0:
                all_urlList.extend(urlList)
            else:
                return all_urlList
            pageNumber += 1
        
    @staticmethod
    def find_url_from_id(list, id):
        for item in list:
            if item[0] == id:
                return item[1]
        return None

    def uploadToGarmin(self, garminClient, db):
        all_activities = self.getAllActivities()
        if all_activities is None or len(all_activities) == 0:
            logger.warning("has no coros activities.")
            exit()
        logger.warning(f"has {len(all_activities)} all activities.")
        for activity in all_activities:
            activity_id = activity[0]
            db.saveActivity(activity_id, 'coros')

        un_sync_id_list = db.getUnSyncActivity('coros')
        if un_sync_id_list is None or len(un_sync_id_list) == 0:
            logger.warning("has no un sync coros activities.")
            exit()
        logger.warning(f"has {len(un_sync_id_list)} un sync coros activities.")

        ts_str = re.sub(r'(\.\d*)?', '', str(time.time())) + '000'
        user_download_path = os.path.join(COROS_FIT_DIR, f"fit_{ts_str}_coros_download")
        print('download to', user_download_path)
        if not os.path.exists(user_download_path):
            os.makedirs(user_download_path)

        for un_sync_id in un_sync_id_list:
            try:
                download_url = self.find_url_from_id(all_activities, str(un_sync_id))
                if download_url is None:
                    # 未找到对应的下载链接也视为同步
                    logger.warning(f"coros ${un_sync_id} download url missing.")
                    continue 
                
                fileResponse = self.download(download_url)
                file_path = os.path.join(user_download_path, f"{un_sync_id}.fit")
                with open(file_path, "wb") as fb:
                    fb.write(fileResponse.data)
                
                try:
                    logger.warning(f"uploading coros ${un_sync_id} {file_path}.")
                    upload_result = garminClient.upload_activity(file_path)
                    if upload_result.status_code == 202:
                        logging.warning(f"Upload coros {un_sync_id} to garmin success.")
                        self.update_db_status(db, un_sync_id)
                except Exception as e:
                    # 解析上传失败原因，比如是否是因为重复
                    try:
                        responseData = json.loads(e.error.response.text)
                        messages = responseData['detailedImportResult']['failures'][0]['messages']
                        code = messages[0]['code']
                        content = messages[0]['content']
                        logging.warning(f"Upload coros {un_sync_id} to garmin fail: {code}:{content}")
                        if '202' == str(code):
                            self.update_db_status(db, un_sync_id)
                    except Exception as e:
                        logging.warning(f"Upload coros {un_sync_id} to garmin error inside: {e}")
            except Exception as err:
                print(err)
                logging.warning(f"download coros {un_sync_id} activity fail: {err}")
    # 更新数据库同步状态            
    @staticmethod
    def update_db_status(db, un_sync_id):
        try:
            db.updateSyncStatus(un_sync_id, 'coros')
            logger.warning(f"sync coros ${un_sync_id} success.")
        except Exception as err:
            print(err)
            db.updateExceptionSyncStatus(un_sync_id, 'coros')
            logger.warning(f"sync coros ${un_sync_id} exception.")

    def upload_to_convert(self, db):
        all_activities = self.getAllActivities()
        if all_activities is None or len(all_activities) == 0:
            logger.warning("has no coros activities.")
            exit()
        logger.warning(f"has {len(all_activities)} all activities.")
        for activity in all_activities:
            activity_id = activity[0]
            db.saveActivity(activity_id, 'coros')

        un_download_id_list = db.getUnDownloadActivity('coros')
        if un_download_id_list is None or len(un_download_id_list) == 0:
            logger.warning("has no un download coros activities.")
            exit()
        logger.warning(f"has {len(un_download_id_list)} un download coros activities.")

        ts_str = re.sub(r'(\.\d*)?', '', str(time.time())) + '000'
        user_download_path = os.path.join(COROS_FIT_DIR, f"fit_{ts_str}_coros_download")
        print('download to', user_download_path)
        if not os.path.exists(user_download_path):
            os.makedirs(user_download_path)

        for un_download_id in un_download_id_list:
            try:
                download_url = self.find_url_from_id(all_activities, str(un_download_id))
                if download_url is None:
                    # 未找到对应的下载链接也视为同步
                    logger.warning(f"coros ${un_download_id} download url missing.")
                    continue

                fileResponse = self.download(download_url)
                file_path = os.path.join(user_download_path, f"{un_download_id}.fit")
                with open(file_path, "wb") as fb:
                    fb.write(fileResponse.data)

                self.update_download_status(db, un_download_id)
            except Exception as err:
                print(err)
                logging.warning(f"download coros {un_download_id} activity fail: {err}")

        #  压缩
        zip_file_path = f"{user_download_path}/all.zip"
        convert_util.make_zip(zip_file_path, user_download_path)
        # 转换
        convert_util.upload_zip_to_convert(zip_file_path)
        print('download_to_convert over', user_download_path);

    # 更新数据库同步状态
    @staticmethod
    def update_download_status(db, un_download_id):
        try:
            db.updateDownloadStatus(un_download_id, 'coros')
            logger.warning(f"download coros ${un_download_id} success.")
        except Exception as err:
            print(err)
            db.updateExceptionDownloadStatus(un_download_id, 'coros')
            logger.warning(f"download coros ${un_download_id} exception.")
                


class CorosLoginError(Exception):

    def __init__(self, status):
        """Initialize."""
        super(CorosLoginError, self).__init__(status)
        self.status = status

class CorosActivityUploadError(Exception):

    def __init__(self, status):
        """Initialize."""
        super(CorosActivityUploadError, self).__init__(status)
        self.status = status
