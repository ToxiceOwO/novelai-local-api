#!/usr/bin/env python3
"""
NovelAI 队列系统使用示例
"""

import requests
import time

BASE_URL = "http://localhost:8000"

def sync_example():
    """同步请求示例 - 推荐方式"""
    print("=== 同步请求示例 ===")
    
    params = {
        "prompt": "1girl, beautiful anime style, masterpiece",
        "seed": 1000,
        "model": "Anime_v45_Full"
    }
    
    print("发送同步请求...")
    start_time = time.time()
    
    try:
        response = requests.get(f"{BASE_URL}/generate/img/priv", params=params)
        end_time = time.time()
        
        print(f"响应时间: {end_time - start_time:.1f}秒")
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            # 保存图像
            with open("sync_result.png", "wb") as f:
                f.write(response.content)
            print("✅ 图像已保存为 sync_result.png")
            
        elif response.status_code == 423:
            print("❌ 队列已满，请稍后重试")
        else:
            print(f"❌ 请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def async_example():
    """异步请求示例"""
    print("\n=== 异步请求示例 ===")
    
    params = {
        "prompt": "1girl, cute anime style, high quality",
        "seed": 2000,
        "model": "Anime_v45_Full"
    }
    
    # 1. 提交请求
    print("提交异步请求...")
    try:
        response = requests.get(f"{BASE_URL}/generate/img/async", params=params)
        
        if response.status_code == 200:
            result = response.json()
            request_id = result["request_id"]
            print(f"请求已提交，ID: {request_id[:8]}...")
            
            # 2. 轮询状态
            print("等待处理完成...")
            while True:
                status_response = requests.get(f"{BASE_URL}/status/{request_id}")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"状态: {status_data['status']}")
                    
                    if status_data['status'] in ['completed', 'failed']:
                        break
                        
                time.sleep(2)
            
            # 3. 获取结果
            if status_data['status'] == 'completed':
                result_response = requests.get(f"{BASE_URL}/result/{request_id}")
                if result_response.status_code == 200:
                    with open("async_result.png", "wb") as f:
                        f.write(result_response.content)
                    print("✅ 图像已保存为 async_result.png")
                else:
                    print(f"❌ 获取结果失败: {result_response.text}")
            else:
                print(f"❌ 请求处理失败")
                
        elif response.status_code == 423:
            print("❌ 队列已满，请稍后重试")
        else:
            print(f"❌ 提交请求失败: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def check_queue_status():
    """检查队列状态"""
    print("\n=== 队列状态 ===")
    
    try:
        response = requests.get(f"{BASE_URL}/queue/status")
        if response.status_code == 200:
            status = response.json()
            print(f"队列中请求数: {status['queue_size']}/{status['max_queue_size']}")
            print(f"正在处理: {status['is_processing']}")
            if status['current_request_id']:
                print(f"当前处理请求: {status['current_request_id'][:8]}...")
        else:
            print(f"❌ 获取队列状态失败: {response.text}")
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def main():
    """主函数"""
    print("NovelAI 队列系统使用示例")
    print("请确保服务器正在运行在 http://localhost:8000")
    print("=" * 50)
    
    # 检查队列状态
    check_queue_status()
    
    # 同步请求示例（推荐）
    sync_example()
    
    # 等待一段时间
    time.sleep(2)
    
    # 异步请求示例
    async_example()
    
    # 最终检查队列状态
    check_queue_status()
    
    print("\n=" * 50)
    print("示例完成！")

if __name__ == "__main__":
    main()
