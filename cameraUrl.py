import base64
import json
import time
import base64
import json
import time
import uuid
import hmac  # hex-based message authentication code 哈希消息认证码
import hashlib  # 提供了很多加密的算法
import requests
import urllib3


def sign(key, value):
    temp = hmac.new(key.encode(), value.encode(), digestmod=hashlib.sha256)
    return base64.b64encode(temp.digest()).decode()

base_url = "https://192.168.1.201:442"  # 可以正常访问的IP地址
# 注意增加/artemis
api_get_address_url = "/artemis/api/video/v1/cameras/previewURLs"
appKey = "29356955"
appSecret = "YaI4ieVr8zUXMVkesrtz"
http_method = "POST"
x_ca_nonce = str(uuid.uuid4())
x_ca_timestamp = str(int(round(time.time()) * 1000))
# sign_str 的拼接很关键，不然得不到正确的签名
sign_str = "POST\n*/*\napplication/json" + "\nx-ca-key:" + appKey + "\nx-ca-nonce:" + \
           x_ca_nonce + "\nx-ca-timestamp:" + x_ca_timestamp + "\n" + \
           api_get_address_url

signature = sign(appSecret, sign_str)
# print("[INFO] 获取到的签名值为：", signature)
headers = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "x-ca-key": appKey,  # appKey，即 AK
    "x-ca-signature-headers": "x-ca-key,x-ca-nonce,x-ca-timestamp",
    "x-ca-signature": signature,  # 需要计算得到的签名，此处通过后台得到
    "x-ca-timestamp": x_ca_timestamp,  # 时间戳
    "x-ca-nonce": x_ca_nonce  # UUID，结合时间戳防重复
}
url = base_url + api_get_address_url
urllib3.disable_warnings()

def main(item):
    body = {
        "cameraIndexCode": item,
        "streamType": 0,
        "protocol": "rtsp",
        "expand": "streamform=rtp"
    }
    results = requests.post(url, data=json.dumps(body), headers=headers, verify=False)
    camera_url = results.json()['data']['url']
    # print(camera_url)
    return camera_url

if __name__ == "__main__":
    main()