import argparse
import asyncio
import os
import sys

from app.agent.manus import Manus
from app.logger import logger


async def run_cli():
    """运行命令行交互模式"""
    agent = Manus()
    while True:
        try:
            prompt = input("Enter your prompt (or 'exit'/'quit' to quit): ")
            prompt_lower = prompt.lower()
            if prompt_lower in ["exit", "quit"]:
                logger.info("Goodbye!")
                break
            if not prompt.strip():
                logger.warning("Skipping empty prompt.")
                continue
            logger.warning("Processing your request...")
            await agent.run(prompt)
        except KeyboardInterrupt:
            logger.warning("Goodbye!")
            break


def run_web():
    """启动Web应用"""
    # 使用子进程执行web_run.py
    import uvicorn

    # 确保目录结构存在
    from web_run import check_websocket_dependencies, ensure_directories

    ensure_directories()

    if not check_websocket_dependencies():
        logger.error("退出应用。请安装必要的依赖后重试。")
        return 1

    logger.info("🚀 OpenManus Web 应用正在启动...")
    logger.info("访问 http://localhost:8000 开始使用")

    # 设置环境变量以启用自动打开浏览器
    os.environ["AUTO_OPEN_BROWSER"] = "1"

    # 在当前进程中启动Uvicorn服务器
    uvicorn.run("app.web.app:app", host="0.0.0.0", port=8000)
    return 0


def main():
    """主程序入口，解析命令行参数决定运行模式"""
    parser = argparse.ArgumentParser(description="OpenManus - AI助手")
    parser.add_argument("--web", action="store_true", help="以Web应用模式运行（默认为命令行模式）")

    args = parser.parse_args()

    try:
        if args.web:
            # 启动Web模式
            logger.info("启动Web应用模式...")
            # Directly call run_web without asyncio.run() since uvicorn has its own event loop
            return run_web()
        else:
            # 启动CLI模式
            logger.info("启动命令行交互模式...")
            asyncio.run(run_cli())
    except KeyboardInterrupt:
        logger.warning("程序已退出")
    except Exception as e:
        logger.error(f"程序异常退出: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
