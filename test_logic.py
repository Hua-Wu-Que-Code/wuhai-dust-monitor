import pandas as pd
from datetime import datetime
import json

def test_push_logic():
    # 模拟输入数据
    nombre_base = "c6169330baf44c638f9f837d54266988"  # 用户指定的 Code
    device_name = "测试设备" # 初始值，会被Excel覆盖
    dust_status = "Dust"     # 模拟检测到灰尘
    marked_conf = 99999.0    # 模拟置信度
    file_path = f"http://218.21.241.214:11009/polvo/test/{nombre_base}_polvo.png"
    
    # 模拟全局变量
    last_push_time = {}
    
    print(f"[-] 开始测试，使用 Code: {nombre_base}")
    print("[-] 跳过图片处理和 AI 模型检测，直接模拟检测结果为 'Dust'")

    # --- 以下逻辑复用自 web.py ---
    
    try:
        cameras_file = "cameras2.xlsx"
        # 检查文件是否存在
        import os
        if not os.path.exists(cameras_file):
            print(f"[!] 错误: 找不到文件 {cameras_file}")
            return

        print(f"[-] 读取 Excel 文件: {cameras_file}")
        df = pd.read_excel(cameras_file)
        
        # 1. 根据 Code 查找 Name
        name_result = df.loc[df["Code"] == nombre_base, "Name"]
        
        if name_result.empty:
            print(f"[!] 未找到匹配的设备名称 (Code: {nombre_base})")
            return
        else:
            device_name = name_result.values[0]
            print(f"[+] 找到设备名称: {device_name}")

            # 2. 根据 Name 查找 国标ID (注意：不再查找设备ID)
            id_file = "cameras2.xlsx"
            # 模拟 web.py 中的读取逻辑
            df_id = pd.read_excel(id_file, dtype={"国标ID": str})
            # 仅查询国标ID
            id_result = df_id.loc[df_id["Name"] == device_name, ["国标ID"]]
            
            if id_result.empty:
                print(f"[!] 设备名称 '{device_name}' 在表格中未找到对应的国标ID")
                gb_id = None
                return
            else:
                # 获取国标ID
                gb_id = id_result.values[0][0]
                device_name = device_name.strip().lower()

                # 处理国标ID格式
                if gb_id is not None:
                    # 检查是否为 NaN
                    if pd.isna(gb_id): 
                         gb_id = None
                    elif "." in str(gb_id):
                        gb_id = "{:.0f}".format(float(gb_id))
                
                print(f"[+] 获取到国标ID: {gb_id}")

                # 构造响应消息
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                response = {
                    "name_result": '灰尘测试TEST',
                    "deviceId": nombre_base,  # 使用 Code 作为 deviceId
                    "gbId": gb_id,
                    'eventTime': current_time,
                    'captureTime': current_time,
                    'type': dust_status,
                    'pictureUrl': file_path,
                    "conf": float(marked_conf),
                    'level': 3
                }
                
                print("\n[=] 最终构造的推送消息如下:")
                print(json.dumps(response, indent=4, ensure_ascii=False))
                
                # 验证字段类型
                print("\n[?] 字段类型检查:")
                print(f" - deviceId 类型: {type(response['deviceId'])} (应为 str)")
                print(f" - gbId 类型: {type(response['gbId'])} (应为 str)")

    except Exception as e:
        print(f"[!] 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_push_logic()
