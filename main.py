import asyncio
from pathlib import Path
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from boilerplate import API
from novelai_api.ImagePreset import ImageModel, ImagePreset
import io
from typing import Dict, Any
import uuid
import time

app = FastAPI()
output_dir = Path("results")
output_dir.mkdir(exist_ok=True)

class RequestQueue:
    """请求队列管理器，用于处理 NovelAI 的并发限制"""

    def __init__(self, max_queue_size: int = 10):
        self.max_queue_size = max_queue_size
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.processing = False
        self.current_request_id = None
        self._lock = asyncio.Lock()

    async def add_request(self, request_data: Dict[str, Any]) -> str:
        """添加请求到队列，返回请求ID"""
        request_id = str(uuid.uuid4())
        request_data['request_id'] = request_id
        request_data['timestamp'] = time.time()

        try:
            # 尝试立即放入队列，如果队列满了会抛出异常
            self.queue.put_nowait(request_data)
            return request_id
        except asyncio.QueueFull:
            raise HTTPException(status_code=423, detail="Request queue is full. Please try again later.")

    async def process_requests(self):
        """处理队列中的请求"""
        while True:
            try:
                # 从队列中获取请求
                request_data = await self.queue.get()
                request_id = request_data['request_id']

                async with self._lock:
                    self.processing = True
                    self.current_request_id = request_id

                try:
                    # 处理请求
                    result = await self._process_single_request(request_data)

                    # 更新全局结果存储
                    if request_id in request_results:
                        request_results[request_id]['result'] = result
                        request_results[request_id]['status'] = 'completed'

                except Exception as e:
                    # 更新全局结果存储
                    if request_id in request_results:
                        request_results[request_id]['error'] = str(e)
                        request_results[request_id]['status'] = 'failed'
                    print(f"Request {request_id} failed: {e}")
                finally:
                    # 标记任务完成
                    self.queue.task_done()
                    async with self._lock:
                        self.processing = False
                        self.current_request_id = None

            except Exception as e:
                print(f"Queue processing error: {e}")
                await asyncio.sleep(1)

    async def _process_single_request(self, request_data: Dict[str, Any]) -> bytes:
        """处理单个图像生成请求"""
        prompt = request_data['prompt']
        seed = request_data['seed']
        model = request_data['model']

        try:
            model_enum = getattr(ImageModel, model)
        except AttributeError:
            raise HTTPException(status_code=400, detail="Invalid model name")

        async with API() as api_handler:
            api = api_handler.api
            preset = ImagePreset.from_default_config(model_enum)
            preset.steps = 28
            preset.seed = seed
            preset.resolution = "Normal_Square_v3"
            preset.characters = []

            img_bytes = None
            async for _, img in api.high_level.generate_image(prompt, model_enum, preset):
                img_bytes = img
                break

        if img_bytes is None:
            raise HTTPException(status_code=500, detail="Image generation failed")

        return img_bytes

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            "queue_size": self.queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "is_processing": self.processing,
            "current_request_id": self.current_request_id
        }

# 创建全局队列实例
request_queue = RequestQueue(max_queue_size=10)

# 存储请求结果的字典
request_results: Dict[str, Dict[str, Any]] = {}

@app.on_event("startup")
async def startup_event():
    """应用启动时启动队列处理器和清理任务"""
    asyncio.create_task(request_queue.process_requests())
    asyncio.create_task(cleanup_old_requests())
    print("Request queue processor started")
    print("Request cleanup task started")

async def cleanup_old_requests():
    """定期清理过期的请求结果（超过1小时的请求）"""
    while True:
        try:
            current_time = time.time()
            expired_requests = []

            for request_id, request_info in request_results.items():
                # 清理超过1小时的请求
                if current_time - request_info['timestamp'] > 3600:
                    expired_requests.append(request_id)

            for request_id in expired_requests:
                del request_results[request_id]

            if expired_requests:
                print(f"Cleaned up {len(expired_requests)} expired requests")

        except Exception as e:
            print(f"Cleanup error: {e}")

        # 每10分钟清理一次
        await asyncio.sleep(600)

@app.get("/generate/img/priv")
async def generate_image(
    prompt: str = Query("1girl, 1boy"),
    seed: int = Query(0),
    model: str = Query("Anime_v45_Full")
):
    """提交图像生成请求到队列"""
    request_data = {
        'prompt': prompt,
        'seed': seed,
        'model': model
    }

    # 添加请求到队列
    request_id = await request_queue.add_request(request_data)

    # 存储请求数据以便后续查询
    request_results[request_id] = {
        'status': 'queued',
        'request_data': request_data,
        'timestamp': time.time()
    }

    return {
        "request_id": request_id,
        "status": "queued",
        "message": "Request added to queue. Use /status/{request_id} to check progress.",
        "queue_status": request_queue.get_queue_status()
    }

@app.get("/status/{request_id}")
async def get_request_status(request_id: str):
    """查询请求状态"""
    if request_id not in request_results:
        raise HTTPException(status_code=404, detail="Request not found")

    request_info = request_results[request_id]

    # 检查队列中是否有结果更新
    if request_info['status'] == 'queued':
        # 检查是否正在处理
        if request_queue.current_request_id == request_id:
            request_info['status'] = 'processing'

    return {
        "request_id": request_id,
        "status": request_info['status'],
        "timestamp": request_info['timestamp'],
        "queue_status": request_queue.get_queue_status()
    }

@app.get("/result/{request_id}")
async def get_request_result(request_id: str):
    """获取请求结果"""
    if request_id not in request_results:
        raise HTTPException(status_code=404, detail="Request not found")

    request_info = request_results[request_id]

    if request_info['status'] == 'queued':
        raise HTTPException(status_code=202, detail="Request is still in queue")
    elif request_info['status'] == 'processing':
        raise HTTPException(status_code=202, detail="Request is being processed")
    elif request_info['status'] == 'failed':
        raise HTTPException(status_code=500, detail=f"Request failed: {request_info.get('error', 'Unknown error')}")
    elif request_info['status'] == 'completed':
        if 'result' in request_info:
            return StreamingResponse(io.BytesIO(request_info['result']), media_type="image/png")
        else:
            raise HTTPException(status_code=500, detail="Result not found")
    else:
        raise HTTPException(status_code=500, detail="Unknown request status")

@app.get("/queue/status")
async def get_queue_status():
    """获取队列状态"""
    return request_queue.get_queue_status()

@app.delete("/queue/clear")
async def clear_queue():
    """清空队列（仅用于管理）"""
    # 创建新的队列来替换当前队列
    old_queue = request_queue.queue
    request_queue.queue = asyncio.Queue(maxsize=request_queue.max_queue_size)

    # 清理结果存储
    request_results.clear()

    return {
        "message": "Queue cleared",
        "cleared_requests": old_queue.qsize()
    }
