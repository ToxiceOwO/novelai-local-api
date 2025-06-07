#!/usr/bin/env python3
"""
启动 NovelAI 队列服务器
"""

import uvicorn
import sys
import os

def main():
    """启动服务器"""
    print("启动 NovelAI 请求队列服务器...")
    print("服务器将运行在: http://localhost:8000")
    print("API 文档: http://localhost:8000/docs")
    print("队列状态: http://localhost:8000/queue/status")
    print("\n按 Ctrl+C 停止服务器")
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动服务器时发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
