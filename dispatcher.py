import os
import asyncio
import subprocess
from typing import TypedDict, Annotated, Sequence, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import StateGraph, END
from qdrant_client import QdrantClient

from ssh_armorer import SSHArmorer

load_dotenv()

# 1. SETUP CLIENTS
llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    api_key=os.getenv("OPENROUTER_API_KEY") or "",
    base_url="https://openrouter.ai/api/v1"
)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=os.getenv("OPENROUTER_API_KEY") or "",
    base_url="https://openrouter.ai/api/v1"
)

qdrant = QdrantClient(url="http://localhost:6333")

# Server mapping
SERVERS = {
    "thecontroller": "localhost",
    "moonbot2": "165.245.132.82",
    "factory-floor": "165.245.134.252",
    "klume-dev-server": "165.245.128.251"
}

class AgentState(TypedDict):
    messages: Annotated[list, lambda x, y: x + y]
    context: str
    route_decision: str

# --- PYDANTIC MODELS FOR NATIVE TOOL CALLING ---

class RouteDecision(BaseModel):
    """Decide where to route the user's request based on their intent."""
    route: str = Field(
        description="Must be exactly one of: 'ssh_worker', 'health_worker', 'logs_worker', or 'FINISH'. "
                    "Use 'ssh_worker' for ALL requests to check server state, install software, run commands, or fix issues. "
                    "Use 'FINISH' only for general advice or greetings."
    )

class SSHCommand(BaseModel):
    """Extract the target server and the necessary Linux command to fulfill the user's request."""
    server: str = Field(
        description=f"The target server name. Must be one of: {', '.join(SERVERS.keys())}"
    )
    command: str = Field(
        description="The exact Linux command to run. Always prepend 'sudo ' for system-level commands like apt-get, systemctl, docker, etc."
    )

# 2. THE MEMORY TOOL (Search Qdrant)
def query_memory(query: str):
    print(f"🧠 Searching Factory Memory for: '{query}'...", flush=True)
    try:
        vector = embeddings.embed_query(query)
        results = qdrant.query_points(
            collection_name="factory_memory",
            query=vector,
            limit=2
        )
        context = "\n".join([point.payload['content'] for point in results.points])
        print(f"📦 Found {len(results.points)} memory chunks", flush=True)
        return context if context else "No relevant past memories found."
    except Exception as e:
        print(f"❌ Memory search error: {e}", flush=True)
        return f"Memory search failed: {e}"

# 3. THE UPDATED SUPERVISOR WITH TOOL CALLING
def supervisor_node(state: AgentState):
    print("\n🎯 Supervisor Node activated (Tool Calling Mode)", flush=True)

    last_message = [m for m in state["messages"] if isinstance(m, HumanMessage)][-1].content

    # FAST PATH: Direct routing for known commands
    if last_message.startswith("/logs"):
        return {"route_decision": "logs_worker", "context": "Direct command routing"}

    if last_message.startswith("/ssh"):
        parts = last_message.split()
        if len(parts) < 3:
            return {"route_decision": "FINISH", "context": "SSH validation failed", "messages": [AIMessage(content="Usage: /ssh <server> <command>")]}
        server_name = parts[1].lower()
        if server_name not in SERVERS:
            return {"route_decision": "FINISH", "context": "SSH validation failed", "messages": [AIMessage(content=f"Unknown server: {server_name}")]}
        return {"route_decision": "ssh_worker", "context": "Direct command routing"}

    # Pull context from Qdrant
    memory_context = query_memory(last_message)

    system_prompt = SystemMessage(content=f"""
    You are the Master Dispatcher for a non-technical user managing a fleet of servers.
    Your ONLY job is to route the request to the correct worker.
    
    Available servers: {', '.join(SERVERS.keys())}
    """)

    # NATIVE STRUCTURED OUTPUT CALL
    llm_with_tools = llm.with_structured_output(RouteDecision)
    try:
        response = llm_with_tools.invoke([system_prompt] + state["messages"])
        route = response.route
    except Exception as e:
        print(f"⚠️ Routing Tool Failed: {e}. Defaulting to FINISH.", flush=True)
        route = "FINISH"

    # Enforce strict routing names
    if route not in ["ssh_worker", "health_worker", "logs_worker", "FINISH"]:
        route = "FINISH"

    print(f"🔀 Decision: {route}", flush=True)

    # If routing to FINISH, provide a friendly answer
    if route == "FINISH":
        answer_prompt = SystemMessage(content=f"""
        You are a friendly, conversational assistant helping a non-technical user (a truck driver) manage their servers. You have general AI knowledge about server management.
        
        PAST ACTIONS KNOWLEDGE:
        {memory_context}

        RULES:
        1. Answer their question naturally and clearly.
        2. If they ask about past events, use the PAST ACTIONS KNOWLEDGE. If there is no relevant past knowledge, just say "I don't recall any recent actions for that."
        3. If they ask for advice (e.g., "How do I host a website?"), answer them using your general AI knowledge! Explain the steps very simply, and offer to do the first step for them.
        4. NEVER use technical jargon like "memory context", "logs", "SSH", "commands", or "terminal".
        5. If you explain a past action, explain it simply (e.g., "I fixed a permission issue on moonbot2").
        6. NEVER tell the user to run commands like "/ssh" or use a terminal. Always offer to perform the actions for them.
        7. Keep your answers brief, friendly, and non-technical.
        """)
        answer_response = llm.invoke([answer_prompt] + state["messages"])
        return {"route_decision": route, "context": memory_context, "messages": [AIMessage(content=answer_response.content)]}

    return {"route_decision": route, "context": memory_context}

# 4. SSH WORKER WITH TOOL CALLING

def format_ssh_response(server_name: str, command: str, success: bool, output: str) -> str:
    format_prompt = SystemMessage(content=f"""
You are a friendly, conversational assistant for a non-technical user (a truck driver). Explain what you did and the results in extremely simple, everyday English.

RULES:
1. NEVER use the word "command", "script", "bash", or "terminal". Frame everything as "tasks", "checks", or "actions" you performed.
2. NEVER mention technical jargon like "exit code", "bash line 1", "127", "stdout", "stderr", or "error". 
3. If software isn't installed, just simply say "Docker isn't installed yet" or "That software is missing." Do NOT say "the task failed."
4. Use simple bullet points (•) for the things you checked.
5. Use these status indicators:
   - ✅ for success (e.g., "Docker is installed")
   - ⚠️ for things that are missing or need attention (e.g., "Docker is missing")
   - ❌ for clear issues, but explain them simply without technical words (e.g., "I couldn't reach the server")
6. End with a brief, easy-to-understand summary in plain English.
7. Always clearly state if you need the user's permission to fix the issue or install something (e.g., "Would you like me to install Docker for you?").

Now format this result:
Server: {server_name}
Command: {command}
Exit Success: {success}
Output:
{output}
""")

    response = llm.invoke([format_prompt])
    return response.content

async def ssh_worker_node(state: AgentState):
    print("🔧 SSH Worker Node activated (Tool Calling Mode)", flush=True)
    armorer = SSHArmorer()
    last_message = [m for m in state["messages"] if isinstance(m, HumanMessage)][-1].content

    server_name = None
    command = None

    if last_message.startswith("/ssh"):
        parts = last_message.split()
        if len(parts) >= 3:
            server_name = parts[1].lower()
            command = " ".join(parts[2:])
    else:
        # NATIVE STRUCTURED OUTPUT CALL
        extract_prompt = SystemMessage(content=f"""
        You are a system tool that extracts the target server and the necessary Linux command from the user's natural language request.
        Available servers: {', '.join(SERVERS.keys())}
        """)
        llm_with_tools = llm.with_structured_output(SSHCommand)
        try:
            response = llm_with_tools.invoke([extract_prompt, HumanMessage(content=last_message)])
            server_name = response.server.lower()
            command = response.command
        except Exception as e:
            print(f"❌ SSH Extraction Tool Failed: {e}", flush=True)
            return {"messages": [AIMessage(content=f"⚠️ I'm not entirely sure which server or action you meant. Available servers are: {', '.join(SERVERS.keys())}")], "sender": "ssh_worker"}

    # Validate
    if not server_name or not command:
        return {"messages": [AIMessage(content="⚠️ I couldn't determine the server or action.")], "sender": "ssh_worker"}
    if server_name not in SERVERS:
        return {"messages": [AIMessage(content=f"⚠️ Unknown server: {server_name}. Available servers: {', '.join(SERVERS.keys())}")], "sender": "ssh_worker"}

    # Execute
    server_ip = SERVERS[server_name]
    print(f"🔧 Executing command on {server_name} ({server_ip}): {command}", flush=True)

    try:
        success, output = armorer.execute_command(server_ip, command)
        formatted_response = format_ssh_response(server_name, command, success, output)
        return {"messages": [AIMessage(content=formatted_response)], "sender": "ssh_worker"}
    except Exception as e:
        return {"messages": [AIMessage(content=f"⚠️ Could not complete the task on {server_name}: {str(e)}")], "sender": "ssh_worker"}

# 5. HEALTH WORKER
async def health_worker_node(state: AgentState):
    print("🏥 Health Monitor Node activated", flush=True)
    api_cmd = "curl -s -H 'Authorization: Bearer szllsgw7njrkpddu-pqqttbe7acyraykwxfzibyvkdc=' 'https://brain-thecontroller.klumistar.com/api/project/1/tasks?limit=1'"
    try:
        result = subprocess.check_output(api_cmd, shell=True).decode('utf-8')
        if '"status":"success"' in result:
            report = "✅ Factory Status: All systems operational. The last deployment succeeded."
        elif '"status":"running"' in result:
            report = "🔄 Factory Status: A deployment is currently running."
        else:
            report = "⚠️ Notice: The last deployment encountered an issue."
    except Exception as e:
        report = f"⚠️ Notice: Unable to reach the health monitor."
    return {"messages": [AIMessage(content=report)], "sender": "health_worker"}

# 6. LOGS WORKER
async def logs_worker_node(state: AgentState):
    print("📋 Logs Worker Node activated", flush=True)
    last_message = [m for m in state["messages"] if isinstance(m, HumanMessage)][-1].content
    parts = last_message.split()
    if len(parts) < 3:
        return {"messages": [AIMessage(content="Usage: /logs <server> <log_file_or_service>")], "sender": "logs_worker"}
    server_name = parts[1].lower()
    log_target = parts[2]
    if server_name not in SERVERS:
        return {"messages": [AIMessage(content=f"Unknown server: {server_name}")], "sender": "logs_worker"}
    server_ip = SERVERS[server_name]

    if log_target == "syslog":
        ssh_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 moon2vex@{server_ip} 'tail -n 50 /var/log/syslog'"
    else:
        ssh_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 moon2vex@{server_ip} 'journalctl -u {log_target} -n 50 --no-pager'"

    try:
        result = subprocess.check_output(ssh_cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
        return {"messages": [AIMessage(content=f"📋 Latest logs for {log_target} on {server_name}:\n\n```\n{result}\n```")], "sender": "logs_worker"}
    except Exception as e:
        return {"messages": [AIMessage(content=f"⚠️ Could not pull logs from {server_name}.")], "sender": "logs_worker"}

# 7. BUILD THE GRAPH
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("ssh_worker", ssh_worker_node)
workflow.add_node("health_worker", health_worker_node)
workflow.add_node("logs_worker", logs_worker_node)

workflow.set_entry_point("supervisor")
workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["route_decision"],
    {"ssh_worker": "ssh_worker", "health_worker": "health_worker", "logs_worker": "logs_worker", "FINISH": END}
)
workflow.add_edge("ssh_worker", END)
workflow.add_edge("health_worker", END)
workflow.add_edge("logs_worker", END)

graph = workflow.compile()

async def main():
    print("🎛️ Tool-Calling Dispatcher Online.", flush=True)
    user_input = input("\nUser> ")
    result = await graph.ainvoke({"messages": [HumanMessage(content=user_input)]})
    print(f"\n🤖 Dispatcher Response: {result['messages'][-1].content}", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
