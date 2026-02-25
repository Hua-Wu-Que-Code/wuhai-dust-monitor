import helpers_new as hp
import get_images as gi
import os
import re
import torch
from pathlib import Path
from torchvision.transforms import transforms
from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large
import asyncio
import json
import websockets
from datetime import datetime
from flask import Flask, send_from_directory
import threading
import pandas as pd
from decimal import Decimal
from torchvision.models.segmentation import deeplabv3_resnet50
from PIL import Image, ImageOps
from datetime import datetime, timedelta
import numpy as np

# 全局变量，用于存储最后推送时间
last_push_time = {}
INTERNAL_IP = "192.168.1.37"
# Flask 应用程序，用于提供 HTTP 访问
app = Flask(__name__)

# 静态文件路由：公开存储图片的目录
@app.route('/polvo/<path:filename>')
def serve_image(filename):
    print("进入静态文件路由，开始处理图片请求")
    result = send_from_directory('/opt/frames/output/polvo', filename)
    print("静态文件路由处理完成，返回图片")
    return result

def start_http_server():
    print("开始启动 Flask 服务器")
    print(f"Flask 服务器启动中，外部访问地址为 http://218.21.241.214:11006 (内部监听 {INTERNAL_IP}:11005)")
    app.run(host=INTERNAL_IP, port=11005, debug=False, use_reloader=False)

# WebSocket 处理函数
async def handler(websocket):
    global device_id, gb_id, device_name, last_push_time

    last_heartbeat_time = datetime.now()

    try:
        print("WebSocket 处理函数开始运行，等待接收消息")
        while True:
            print("开始等待接收 WebSocket 消息")
            message = await websocket.recv()
            print(f"接收到 WebSocket 消息: {message}")
            started_processing = False
            if message == '1':
                now = datetime.now()
                if now.hour < 7 or now.hour >= 20:
                    print(f"当前时间 {now.strftime('%H:%M:%S')} 不在运行时间段（07:00 - 20:00），跳过处理。")
                    continue

                print("接收到心跳消息，更新最后心跳时间并回复")
                last_heartbeat_time = datetime.now()
                await websocket.send('1')
                if not started_processing:
                    print("开始处理图片，获取当前时间信息")
                    started_processing = True
                    dd, hh, mm = gi.get_today_str()
                    sub_directory = dd + '-' + str(hh).zfill(2) + '-' + str(mm).zfill(2)
                    dt = datetime.strptime(sub_directory, "%Y-%m-%d-%H-%M")
                    sub_directory = dt.strftime("%Y%m%d%H%M" + '/')
                    print(f"当前子目录为: {sub_directory}，开始获取图片")
                    gi.get_images(sub_directory)
                    print("图片获取完成，开始加载模型")
                    model = deeplabv3_resnet50(weights=None, progress=True, num_classes=1, aux_loss=None)
                    direccion_modelo = "/home/owner/DustDetection-main/src/Pretrained/"
                    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
                    model.load_state_dict(
                        torch.load(direccion_modelo + 'Model_100_t1withdust_807_wuyanchen_xitongwubao.pth',
                                   map_location=torch.device(device)))
                    model.eval()
                    model.to(device)
                    print("模型加载完成，开始定义图像转换操作")
                    img_transform = transforms.Compose([
                        transforms.Resize((256, 256)),
                        transforms.ToTensor(),
                        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
                    ])
                    print("图像转换操作定义完成，开始遍历图片目录")
                    dir_root = '/opt/frames/'
                    dir_path = os.path.join(dir_root, sub_directory)
                    if not os.path.isdir(dir_path):
                        candidates = [d for d in os.listdir(dir_root) if len(d) == 12 and d.isdigit() and os.path.isdir(os.path.join(dir_root, d))]
                        if candidates:
                            latest = sorted(candidates, reverse=True)[0] + '/'
                            print(f"目录不存在: {dir_path}，使用最近目录 {latest}")
                            sub_directory = latest
                            dir_path = os.path.join(dir_root, sub_directory)
                        else:
                            print(f"目录不存在且无可用目录: {dir_path}")
                            continue
                    directory = os.fsencode(dir_path)
                    for file in os.listdir(directory):
                        filename = os.fsdecode(file)
                        nombre, _ = filename.split('.')
                        print(f"开始处理图片: {filename}")
                        original = Image.open("/opt/frames/" + sub_directory + filename)

                        # 判断图像是否为灰度图（模式为L）或颜色差异很小的伪灰图
                        if original.mode == 'L':
                            print(f"{filename} 是灰度图，跳过处理")
                            continue
                        else:
                            original_np = np.array(original.convert("RGB"))
                            r, g, b = original_np[:, :, 0], original_np[:, :, 1], original_np[:, :, 2]
                            threshold = 15  # 控制灰图判定的灵敏度，数值越大越宽松

                            if (np.mean(np.abs(r - g)) < threshold and
                                    np.mean(np.abs(g - b)) < threshold and
                                    np.mean(np.abs(r - b)) < threshold):
                                print(f"{filename} 是伪彩灰图，跳过处理")
                                continue


                        Path('/opt/frames/output/original/' + sub_directory).mkdir(parents=True, exist_ok=True)
                        original.save('/opt/frames/output/original/' + sub_directory + nombre + '_original.png')
                        print("原始图片保存完成，开始识别灰尘")
                        polvo, mask, marked = hp.identificar_polvo(original, model, img_transform)
                        Path('/opt/frames/output/polvo/' + sub_directory).mkdir(parents=True, exist_ok=True)
                        polvo.save('/opt/frames/output/polvo/' + sub_directory + nombre + '_polvo.png')
                        dust_status = 'Dust' if marked[0] >= 30000.0 else 'No dust'
                        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        file_path = f"http://218.21.241.214:11006/polvo/{sub_directory}{nombre}_polvo.png"
                        print(f"图片处理完成，灰尘状态: {dust_status}")
                        if dust_status == 'Dust':
                            print("检测到灰尘，开始保存灰尘图片并查找设备信息")
                            dust_folder = Path('/home/owner/DustDetection-main/src/Dustraising/' + sub_directory)
                            dust_folder.mkdir(parents=True, exist_ok=True)
                            dust_image_path = dust_folder / (nombre + '_original.png')
                            original.save(dust_image_path)
                            nombre_base = nombre.split('_')[0]
                            cameras_file = "cameras2.xlsx"
                            df = pd.read_excel(cameras_file)
                            name_result = df.loc[df["Code"] == nombre_base, "Name"]
                            if name_result.empty:
                                print("未找到匹配的设备名称")
                            else:
                                device_name = name_result.values[0]
                                id_file = "cameras2.xlsx"
                                df_id = pd.read_excel(id_file, dtype={"国标ID": str})
                                # 仅查询国标ID，不再查询设备ID
                                id_result = df_id.loc[df_id["Name"] == device_name, ["国标ID"]]
                                if id_result.empty:
                                    print(f"设备名称 '{device_name}' 在 ID.xlsx 中未找到对应的国标ID")
                                    gb_id = None
                                    continue
                                else:
                                    # 只解包出一个值：gb_id
                                    gb_id = id_result.values[0][0]
                                    device_name = device_name.strip().lower()

                                    if gb_id is not None:
                                        if "." in gb_id:
                                            gb_id = "{:.0f}".format(float(gb_id))
                                    # 检查是否已经推送过该国标ID的消息
                                    if gb_id in last_push_time:
                                        # 检查是否已经过了一个小时
                                        if (datetime.now() - last_push_time[gb_id]) < timedelta(hours=1):
                                            print(f"Skipping duplicate message for GB ID: {gb_id}")
                                            continue
                                    # 更新最后推送时间
                                    last_push_time[gb_id] = datetime.now()
                                    response = {
                                        "name_result": device_name,  # 设备名称 (从Excel中根据Code匹配到的Name)
                                        "deviceId": nombre_base,  # 设备 Code (从文件名获取)
                                        "gbId": gb_id,  # 国标 ID (从Excel中获取)
                                        'eventTime': current_time,  # 事件发生时间
                                        'captureTime': current_time,  # 抓拍时间
                                        'type': dust_status,  # 报警类型
                                        'pictureUrl': file_path,  # 图片 URL 地址
                                        "conf": float(marked[0]),  # 置信度
                                        'level': 3  # 报警等级 (固定为3)
                                    }
                                    print(f"准备发送响应消息: {response}")
                                    await websocket.send(json.dumps(response))
                                    print(f"响应消息发送完成: {response}")
            if (datetime.now() - last_heartbeat_time).seconds > 100:
                print("超时时间已到，关闭 WebSocket 连接")
                await websocket.close()
                break
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"WebSocket 连接意外关闭: {e}")
    except Exception as e:
        print(f"发生意外错误: {e}")
    finally:
        print("WebSocket 连接关闭")
        await websocket.close()
        print("连接已成功关闭")

# 启动 WebSocket 服务器
async def start_websocket_server():
    print("开始启动 WebSocket 服务器")
    print(f"WebSocket 服务器启动中，外部访问地址为 ws://218.21.241.214:11008 (内部监听 {INTERNAL_IP}:11007)")
    server = await websockets.serve(handler, INTERNAL_IP, 11007, ping_interval=10, ping_timeout=20)
    await server.wait_closed()

# 同时启动 WebSocket 和 HTTP 服务器
if __name__ == "__main__":
    print("开始启动 HTTP 服务器线程")
    # 启动 HTTP 服务器线程
    http_thread = threading.Thread(target=start_http_server)
    http_thread.start()
    print("HTTP 服务器线程已启动，开始启动 WebSocket 服务器")
    # 启动 WebSocket 服务器
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_websocket_server())
    loop.run_forever()
