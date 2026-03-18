import asyncio
from ssh_armorer import SSHArmorer

async def run_inspection():
    print("Starting Real Pre-Trip Inspection...")
    # 1. Turn on the agent
    agent = SSHArmorer()
    await agent.start_memory_server()

    # 2. Feed it a real scenario with existing key
    print("\nHanding task to agent...")
    await agent.run_diagnosis_and_fix(
        error_message="Permission denied (publickey)",
        service="semaphore",
        key_path="/root/.ssh/id_rsa"  # Real key path
    )

    # 3. Shut down
    await agent.stop_memory_server()
    print("\nInspection Complete.")

asyncio.run(run_inspection())
