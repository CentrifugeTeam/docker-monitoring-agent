import asyncio
from src.agent import DockerAgent

async def main():
  agent = DockerAgent()
  await agent.run()

if __name__ == "__main__":
  asyncio.run(main())
