import base64
import json
import time
import uuid
import hmac  # hex-based message authentication code 哈希消息认证码
import hashlib  # 提供了很多加密的算法
import requests
import urllib3

base_url = "https://192.168.1.201:442"  # 可以正常访问的IP地址
api_get_address_url = "/artemis/api/resource/v1/cameras"
appKey = "29356955"
appSecret = "YaI4ieVr8zUXMVkesrtz"
http_method = "POST"
print("正在获取摄像头列表...")
def sign(key, value):
    temp = hmac.new(key.encode(), value.encode(), digestmod=hashlib.sha256)
    return base64.b64encode(temp.digest()).decode()


x_ca_nonce = str(uuid.uuid4())
x_ca_timestamp = str(int(round(time.time()) * 1000))
sign_str = "POST\n*/*\napplication/json" + "\nx-ca-key:" + appKey + "\nx-ca-nonce:" + \
           x_ca_nonce + "\nx-ca-timestamp:" + x_ca_timestamp + "\n" + \
           api_get_address_url

signature = sign(appSecret, sign_str)

headers = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "x-ca-key": appKey,  # appKey，即 AK
    "x-ca-signature-headers": "x-ca-key,x-ca-nonce,x-ca-timestamp",
    "x-ca-signature": signature,  # 需要计算得到的签名，此处通过后台得到
    "x-ca-timestamp": x_ca_timestamp,  # 时间戳
    "x-ca-nonce": x_ca_nonce  # UUID，结合时间戳防重复
}

body = {
    "pageNo": 3,
    "pageSize": 122
}

url = base_url + api_get_address_url
urllib3.disable_warnings()
results = requests.post(url, data=json.dumps(body), headers=headers, verify=False)

body = {
    "pageNo": 3,
    "pageSize":int(results.json()['data']['total'] /3)
}
results = requests.post(url, data=json.dumps(body), headers=headers, verify=False)
camera_codes = []
camera_name = []
tinydict = {}
def main():
    print("正在获取摄像头列表...")
    print(results.json()['data']['total'])
    for i in range(int(results.json()['data']['total']/3)):
        camera_index_code = results.json()['data']['list'][i]['cameraIndexCode']
        camera_codes.append(camera_index_code)
        camera_index_name = results.json()['data']['list'][i]['cameraName']
        camera_name.append(camera_index_name)
        tinydict[camera_index_code] = camera_index_name
    print("摄像头列表获取成功")

if __name__ == "__main__":
    main()
