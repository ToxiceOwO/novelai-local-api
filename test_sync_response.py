#!/usr/bin/env python3
"""
测试同步响应功能
"""

import asyncio
import aiohttp
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def test_sync_response():
    """测试同步响应功能"""
    print("=== 测试同步响应功能 ===")
    
    async with aiohttp.ClientSession() as session:
        # 测试单个同步请求
        print("\n1. 测试单个同步请求:")
        params = {
            "prompt": "1girl, beautiful anime style",
            "seed": 1000,
            "model": "Anime_v45_Full"
        }
        
        start_time = time.time()
        print(f"发送请求时间: {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            async with session.get(f"{BASE_URL}/generate/img/priv", params=params) as resp:
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"响应时间: {datetime.now().strftime('%H:%M:%S')}")
                print(f"总耗时: {duration:.1f}秒")
                print(f"状态码: {resp.status}")
                
                if resp.status == 200:
                    content_type = resp.headers.get('content-type', 'unknown')
                    content_length = resp.headers.get('content-length', 'unknown')
                    print(f"内容类型: {content_type}")
                    print(f"内容大小: {content_length} bytes")
                    print("✅ 同步请求成功！")
                    
                    # 保存图像以验证
                    with open(f"test_sync_result.png", "wb") as f:
                        async for chunk in resp.content.iter_chunked(8192):
                            f.write(chunk)
                    print("图像已保存为 test_sync_result.png")
                    
                elif resp.status == 423:
                    print("❌ 队列已满")
                else:
                    error_text = await resp.text()
                    print(f"❌ 请求失败: {error_text}")
                    
        except Exception as e:
            print(f"❌ 请求异常: {e}")

async def test_concurrent_sync_requests():
    """测试并发同步请求"""
    print("\n=== 测试并发同步请求 ===")
    
    async def make_request(session, index):
        params = {
            "prompt": f"1girl, test concurrent {index}",
            "seed": 2000 + index,
            "model": "Anime_v45_Full"
        }
        
        start_time = time.time()
        print(f"请求 {index} 开始: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        
        try:
            async with session.get(f"{BASE_URL}/generate/img/priv", params=params) as resp:
                end_time = time.time()
                duration = end_time - start_time
                
                print(f"请求 {index} 完成: {datetime.now().strftime('%H:%M:%S.%f')[:-3]} (耗时: {duration:.1f}s)")
                
                if resp.status == 200:
                    content_length = resp.headers.get('content-length', 'unknown')
                    print(f"  ✅ 成功，大小: {content_length} bytes")
                    return True
                elif resp.status == 423:
                    print(f"  ❌ 队列已满")
                    return False
                else:
                    error_text = await resp.text()
                    print(f"  ❌ 失败: {error_text}")
                    return False
                    
        except Exception as e:
            print(f"  ❌ 异常: {e}")
            return False
    
    # 并发发送3个请求
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(3):
            task = asyncio.create_task(make_request(session, i + 1))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        success_count = sum(results)
        print(f"\n并发测试结果: {success_count}/{len(results)} 成功")

async def test_queue_overflow():
    """测试队列溢出"""
    print("\n=== 测试队列溢出 ===")
    
    async def make_quick_request(session, index):
        params = {
            "prompt": f"overflow test {index}",
            "seed": 3000 + index,
            "model": "Anime_v45_Full"
        }
        
        try:
            async with session.get(f"{BASE_URL}/generate/img/priv", params=params) as resp:
                if resp.status == 200:
                    return "success"
                elif resp.status == 423:
                    return "queue_full"
                else:
                    return "error"
        except Exception:
            return "exception"
    
    async with aiohttp.ClientSession() as session:
        # 快速发送大量请求
        tasks = []
        for i in range(15):  # 超过队列限制
            task = asyncio.create_task(make_quick_request(session, i + 1))
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        success_count = results.count("success")
        queue_full_count = results.count("queue_full")
        error_count = results.count("error")
        exception_count = results.count("exception")
        
        print(f"溢出测试结果:")
        print(f"  成功: {success_count}")
        print(f"  队列满: {queue_full_count}")
        print(f"  错误: {error_count}")
        print(f"  异常: {exception_count}")

async def main():
    """主函数"""
    print("开始测试同步响应功能...")
    print("请确保服务器正在运行在 http://localhost:8000")
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 测试同步响应
        await test_sync_response()
        
        # 等待一段时间
        await asyncio.sleep(2)
        
        # 测试并发同步请求
        await test_concurrent_sync_requests()
        
        # 等待一段时间
        await asyncio.sleep(2)
        
        # 测试队列溢出
        await test_queue_overflow()
        
        print(f"\n测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=== 所有测试完成 ===")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())
