#!/usr/bin/env python3
"""
测试脚本：验证 NovelAI 请求队列功能
"""

import asyncio
import aiohttp
import json
import time

BASE_URL = "http://localhost:8000"

async def test_queue_functionality():
    """测试队列功能 - 验证5-10秒请求处理时间"""
    async with aiohttp.ClientSession() as session:
        print("=== 测试队列功能（5-10秒请求处理时间验证）===")

        # 1. 检查队列状态
        print("\n1. 检查初始队列状态:")
        async with session.get(f"{BASE_URL}/queue/status") as resp:
            status = await resp.json()
            print(f"队列状态: {json.dumps(status, indent=2)}")

        # 2. 提交多个请求来测试队列等待
        print("\n2. 提交多个请求测试队列等待:")
        request_ids = []
        submit_times = []

        for i in range(3):
            params = {
                "prompt": f"1girl, anime style, test image {i+1}",
                "seed": i + 1000,
                "model": "Anime_v45_Full"
            }

            submit_time = time.time()
            submit_times.append(submit_time)

            try:
                async with session.get(f"{BASE_URL}/generate/img/priv", params=params) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        request_ids.append(result["request_id"])
                        print(f"请求 {i+1} 提交成功: {result['request_id'][:8]}...")
                        print(f"  提交时间: {time.strftime('%H:%M:%S', time.localtime(submit_time))}")
                    elif resp.status == 423:
                        print(f"请求 {i+1} 被拒绝: 队列已满")
                    else:
                        print(f"请求 {i+1} 失败: HTTP {resp.status}")
            except Exception as e:
                print(f"请求 {i+1} 异常: {e}")

        # 3. 检查队列状态
        print("\n3. 检查提交后的队列状态:")
        async with session.get(f"{BASE_URL}/queue/status") as resp:
            status = await resp.json()
            print(f"队列状态: {json.dumps(status, indent=2)}")

        # 4. 持续监控请求状态直到完成
        print("\n4. 持续监控请求状态（验证队列等待和处理时间）:")
        completed_requests = {}

        while len(completed_requests) < len(request_ids):
            for i, request_id in enumerate(request_ids):
                if request_id in completed_requests:
                    continue

                try:
                    async with session.get(f"{BASE_URL}/status/{request_id}") as resp:
                        if resp.status == 200:
                            status_data = await resp.json()
                            current_status = status_data['status']
                            current_time = time.time()

                            print(f"请求 {i+1} ({request_id[:8]}...): {current_status}")
                            print(f"  当前时间: {time.strftime('%H:%M:%S', time.localtime(current_time))}")
                            print(f"  等待时长: {current_time - submit_times[i]:.1f}秒")

                            if current_status == 'completed':
                                completed_requests[request_id] = {
                                    'completion_time': current_time,
                                    'total_time': current_time - submit_times[i]
                                }
                                print(f"  ✅ 请求完成！总耗时: {current_time - submit_times[i]:.1f}秒")

                                # 尝试获取结果
                                try:
                                    async with session.get(f"{BASE_URL}/result/{request_id}") as result_resp:
                                        if result_resp.status == 200:
                                            content_length = result_resp.headers.get('content-length', 'unknown')
                                            print(f"  📷 图像结果可用，大小: {content_length} bytes")
                                        else:
                                            print(f"  ❌ 获取结果失败: HTTP {result_resp.status}")
                                except Exception as e:
                                    print(f"  ❌ 获取结果异常: {e}")

                            elif current_status == 'failed':
                                completed_requests[request_id] = {
                                    'completion_time': current_time,
                                    'total_time': current_time - submit_times[i],
                                    'failed': True
                                }
                                print(f"  ❌ 请求失败！总耗时: {current_time - submit_times[i]:.1f}秒")

                        else:
                            print(f"状态查询失败: HTTP {resp.status}")
                except Exception as e:
                    print(f"状态查询异常: {e}")

            if len(completed_requests) < len(request_ids):
                print(f"\n等待中... ({len(completed_requests)}/{len(request_ids)} 完成)")
                await asyncio.sleep(3)  # 每3秒检查一次

        # 5. 总结结果
        print("\n=== 测试结果总结 ===")
        for i, request_id in enumerate(request_ids):
            if request_id in completed_requests:
                result = completed_requests[request_id]
                status = "失败" if result.get('failed') else "成功"
                print(f"请求 {i+1}: {status}, 总耗时: {result['total_time']:.1f}秒")

        print("\n=== 队列功能测试完成 ===")

async def test_queue_overflow():
    """测试队列溢出功能"""
    async with aiohttp.ClientSession() as session:
        print("\n=== 测试队列溢出 ===")
        
        # 快速提交大量请求来测试队列溢出
        success_count = 0
        rejected_count = 0
        
        for i in range(15):  # 提交15个请求，超过队列限制
            params = {
                "prompt": f"overflow test {i+1}",
                "seed": i + 2000,
                "model": "Anime_v45_Full"
            }
            
            try:
                async with session.get(f"{BASE_URL}/generate/img/priv", params=params) as resp:
                    if resp.status == 200:
                        success_count += 1
                        print(f"请求 {i+1}: 成功提交")
                    elif resp.status == 423:
                        rejected_count += 1
                        print(f"请求 {i+1}: 队列已满，被拒绝")
                    else:
                        print(f"请求 {i+1}: HTTP {resp.status}")
            except Exception as e:
                print(f"请求 {i+1} 异常: {e}")
        
        print(f"\n结果: 成功提交 {success_count} 个请求, 拒绝 {rejected_count} 个请求")
        
        # 检查最终队列状态
        async with session.get(f"{BASE_URL}/queue/status") as resp:
            status = await resp.json()
            print(f"最终队列状态: {json.dumps(status, indent=2)}")

async def main():
    """主函数"""
    print("开始测试 NovelAI 请求队列...")
    print("请确保服务器正在运行在 http://localhost:8000")
    
    try:
        # 测试基本队列功能
        await test_queue_functionality()
        
        # 等待一段时间
        await asyncio.sleep(5)
        
        # 测试队列溢出
        await test_queue_overflow()
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())
