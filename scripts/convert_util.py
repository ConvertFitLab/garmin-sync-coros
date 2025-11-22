import logging
logger = logging.getLogger(__name__)
import requests
import zipfile
import os
#  压缩成zip
def make_zip(target_zip_file_path, source_dir):
    try:
        with zipfile.ZipFile(target_zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arcname=arcname)
    except Exception as err:
        print(err)
        logging.warning(f"compress zip {source_dir} fail: {err}")
    print(f"compress to {target_zip_file_path} success.")

#  转换提交
def upload_zip_to_convert(zip_file_path):
    try:
        url = "http://127.0.0.1:9000/convertViaServer"
        files = {'zip_file': open(zip_file_path, 'rb')}
        data = {
            'address': 'jinicgood@163.com',
            'type': 'fit',
            'destination': 'fit',
            'payment': 'wechat',
            'paid': 0,
            'recordMode': 'test',
            'convertMode': '1'
        }

        response = requests.post(url, files=files, data=data)
        response_data = response.json()
        print('convertResponse', response_data)

    except Exception as err:
        print(err)
        # db.updateExceptionDownloadStatus(activity_id, 'garmin')
        # logger.warning(f"download garmin to server ${activity_id} exception.")


