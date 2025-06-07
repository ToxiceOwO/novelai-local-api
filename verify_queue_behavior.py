#!/usr/bin/env python3
"""
验证队列行为脚本 - 确认请求在队列中等待并按顺序处理
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

async def verify_sequential_processing():
    """验证请求按顺序处理，每个请求等待前一个完成"""
    print("=== 验证顺序处理机制 ===")
    
    async with aiohttp.ClientSession() as session:
        # 1. 清空队列确保干净的测试环境
        try:
            async with session.delete(f"{BASE_URL}/queue/clear") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"队列已清空: {result}")
        except:
            print("清空队列失败，继续测试...")
        
        # 2. 快速提交3个请求
        print("\n快速提交3个请求...")
        request_data = []
        
        for i in range(3):
            params = {
                "prompt": f"1girl, beautiful, request_{i+1}",
                "seed": 1000 + i,
                "model": "Anime_v45_Full"
            }
            
            submit_time = time.time()
            
            async with session.get(f"{BASE_URL}/generate/img/priv", params=params) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    request_data.append({
                        'id': result['request_id'],
                        'submit_time': submit_time,
                        'index': i + 1
                    })
                    print(f"请求 {i+1} 提交: {result['request_id'][:8]}... (状态: {result['status']})")
                else:
                    print(f"请求 {i+1} 提交失败: HTTP {resp.status}")
        
        # 3. 检查初始队列状态
        async with session.get(f"{BASE_URL}/queue/status") as resp:
            status = await resp.json()
            print(f"\n初始队列状态: {json.dumps(status, indent=2)}")
        
        # 4. 监控处理顺序
        print("\n=== 监控处理顺序 ===")
        processing_order = []
        completion_order = []
        
        while len(completion_order) < len(request_data):
            for req in request_data:
                if req['id'] in [c['id'] for c in completion_order]:
                    continue
                
                async with session.get(f"{BASE_URL}/status/{req['id']}") as resp:
                    if resp.status == 200:
                        status_info = await resp.json()
                        current_status = status_info['status']
                        current_time = time.time()
                        
                        # 记录开始处理的请求
                        if current_status == 'processing':
                            if req['id'] not in [p['id'] for p in processing_order]:
                                processing_order.append({
                                    'id': req['id'],
                                    'index': req['index'],
                                    'start_time': current_time,
                                    'wait_time': current_time - req['submit_time']
                                })
                                print(f"🔄 请求 {req['index']} 开始处理 (等待了 {current_time - req['submit_time']:.1f}秒)")
                        
                        # 记录完成的请求
                        elif current_status in ['completed', 'failed']:
                            if req['id'] not in [c['id'] for c in completion_order]:
                                completion_order.append({
                                    'id': req['id'],
                                    'index': req['index'],
                                    'completion_time': current_time,
                                    'total_time': current_time - req['submit_time'],
                                    'status': current_status
                                })
                                status_emoji = "✅" if current_status == 'completed' else "❌"
                                print(f"{status_emoji} 请求 {req['index']} {current_status} (总耗时 {current_time - req['submit_time']:.1f}秒)")
            
            # 显示当前队列状态
            async with session.get(f"{BASE_URL}/queue/status") as resp:
                queue_status = await resp.json()
                print(f"队列状态: 队列中{queue_status['queue_size']}个, 处理中: {queue_status['is_processing']}")
            
            await asyncio.sleep(2)
        
        # 5. 分析结果
        print("\n=== 处理顺序分析 ===")
        print("处理开始顺序:")
        for i, proc in enumerate(processing_order):
            print(f"  {i+1}. 请求 {proc['index']} (等待 {proc['wait_time']:.1f}秒)")
        
        print("\n完成顺序:")
        for i, comp in enumerate(completion_order):
            print(f"  {i+1}. 请求 {comp['index']} ({comp['status']}, 总耗时 {comp['total_time']:.1f}秒)")
        
        # 6. 验证顺序性
        processing_indices = [p['index'] for p in processing_order]
        completion_indices = [c['index'] for c in completion_order if c['status'] == 'completed']
        
        is_sequential = processing_indices == sorted(processing_indices)
        print(f"\n顺序处理验证: {'✅ 通过' if is_sequential else '❌ 失败'}")
        print(f"处理顺序: {processing_indices}")
        print(f"完成顺序: {completion_indices}")

async def verify_queue_waiting():
    """验证队列等待机制"""
    print("\n=== 验证队列等待机制 ===")
    
    async with aiohttp.ClientSession() as session:
        # 提交一个请求并立即检查状态变化
        params = {
            "prompt": "1girl, waiting test",
            "seed": 2000,
            "model": "Anime_v45_Full"
        }
        
        submit_time = time.time()
        
        async with session.get(f"{BASE_URL}/generate/img/priv", params=params) as resp:
            result = await resp.json()
            request_id = result['request_id']
            print(f"提交请求: {request_id[:8]}...")
        
        # 快速检查状态变化
        status_history = []
        for i in range(20):  # 检查20次，每次间隔1秒
            async with session.get(f"{BASE_URL}/status/{request_id}") as resp:
                status_info = await resp.json()
                current_time = time.time()
                
                status_entry = {
                    'time': current_time,
                    'elapsed': current_time - submit_time,
                    'status': status_info['status']
                }
                status_history.append(status_entry)
                
                print(f"T+{status_entry['elapsed']:.1f}s: {status_entry['status']}")
                
                if status_info['status'] in ['completed', 'failed']:
                    break
                    
                await asyncio.sleep(1)
        
        # 分析状态变化
        print(f"\n状态变化分析:")
        queued_time = None
        processing_time = None
        completion_time = None
        
        for entry in status_history:
            if entry['status'] == 'queued' and queued_time is None:
                queued_time = entry['elapsed']
            elif entry['status'] == 'processing' and processing_time is None:
                processing_time = entry['elapsed']
            elif entry['status'] in ['completed', 'failed'] and completion_time is None:
                completion_time = entry['elapsed']
        
        if queued_time is not None:
            print(f"  排队阶段: 0s - {processing_time or completion_time:.1f}s")
        if processing_time is not None:
            print(f"  处理阶段: {processing_time:.1f}s - {completion_time:.1f}s")
            print(f"  实际处理时间: {completion_time - processing_time:.1f}s")
        if completion_time is not None:
            print(f"  总耗时: {completion_time:.1f}s")

async def main():
    """主函数"""
    print("开始验证队列行为...")
    print("请确保服务器正在运行在 http://localhost:8000")
    print(f"测试开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 验证顺序处理
        await verify_sequential_processing()
        
        # 等待一段时间
        await asyncio.sleep(3)
        
        # 验证队列等待
        await verify_queue_waiting()
        
        print(f"\n测试完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=== 验证完成 ===")
        
    except Exception as e:
        print(f"验证过程中发生错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())
