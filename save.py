import cameraUrl
import cameraList
from concurrent.futures import ProcessPoolExecutor  # 关键修正点
import concurrent
import cv2
import os
from datetime import datetime
import time
import signal
from contextlib import suppress

# 常量定义
WORKERS = 60  # 根据系统资源调整
INTERVAL = 20  # 抓取间隔(秒)
OUTPUT_DIR = "/opt/frames"


def signal_handler(sig, frame):
    print("\n捕获到Ctrl+C, 正在清理资源...")
    exit(0)


signal.signal(signal.SIGINT, signal_handler)


def get_camera_urls():
    """获取最新摄像头列表和URL"""
    cameraList.main()  # 更新摄像头列表
    pairs = [(key, cameraUrl.main(key)) for key in cameraList.tinydict.keys()]
    valid = [(code, url) for code, url in pairs if isinstance(url, str) and url]
    invalid_count = len(pairs) - len(valid)
    if invalid_count:
        print(f"过滤掉 {invalid_count} 个无效URL")
    return valid


def capture_single_frame(rtsp_url, camera_code):
    """捕获单帧并立即释放资源"""
    cap = cv2.VideoCapture(rtsp_url)
    try:
        if not cap.isOpened():
            print(f"[{camera_code}] 无法打开视频流")
            return None, camera_code

        # 设置超时（单位：毫秒）
        cap.set(cv2.CAP_PROP_POS_MSEC, 5000)
        ret, frame = cap.read()

        if not ret:
            print(f"[{camera_code}] 读取帧失败")
            return None, camera_code

        return frame, camera_code
    except Exception as e:
        print(f"[{camera_code}] 捕获异常: {str(e)}")
        return None, camera_code
    finally:
        cap.release()


def save_frame_task(args):
    """保存帧的独立任务"""
    if not args or not isinstance(args, tuple):
        return
    frame, camera_code = args
    if frame is None:
        return

    try:
        timestamp = datetime.now()
        time_dir = timestamp.strftime("%Y%m%d%H%M")
        output_dir = os.path.join(OUTPUT_DIR, time_dir)

        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        filename = f"{camera_code}_{timestamp.strftime('%Y%m%d%H%M%S')}.jpg"
        output_path = os.path.join(output_dir, filename)
        cv2.imwrite(output_path, frame)
        print(f"[{camera_code}] 保存成功: {filename}")
    except Exception as e:
        print(f"[{camera_code}] 保存失败: {str(e)}")


def batch_capture():
    """批量捕获任务"""
    cameras = get_camera_urls()
    print(f"本次需处理 {len(cameras)} 个摄像头")

    with ProcessPoolExecutor(max_workers=WORKERS) as executor:  # 使用正确导入的类
        # 第一阶段：并行捕获帧
        capture_futures = {executor.submit(capture_single_frame, url, code): code for code, url in cameras}

        # 第二阶段：并行保存结果
        save_futures = []
        for future in concurrent.futures.as_completed(capture_futures):
            code = capture_futures[future]
            try:
                result = future.result()
            except Exception as e:
                print(f"[{code}] 捕获阶段异常: {str(e)}")
                continue
            if not result or not isinstance(result, tuple):
                print(f"[{code}] 捕获结果为空或格式错误")
                continue
            frame, camera_code = result
            if frame is not None:
                save_futures.append(executor.submit(save_frame_task, (frame, camera_code)))

        # 等待所有保存任务完成
        for future in concurrent.futures.as_completed(save_futures):
            with suppress(Exception):
                future.result()


def main():
    """主循环控制器"""
    while True:
        cycle_start = time.time()

        try:
            batch_capture()
        except Exception as e:
            print(f"批量捕获异常: {str(e)}")

        # 精确间隔控制
        elapsed = time.time() - cycle_start
        sleep_time = max(INTERVAL - elapsed, 0)
        print(f"本轮完成，耗时 {elapsed:.2f}s，下次执行在 {sleep_time:.2f}s 后")
        time.sleep(sleep_time)


if __name__ == '__main__':
    # 初始化输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    main()
