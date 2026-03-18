#!/usr/bin/env python3
"""
SSH Armorer Agent - MCP Client for SSH Key Permission Fixes

This agent diagnoses and fixes SSH key permission issues by migrating keys
from /root/ to the appropriate user's home directory when running as non-root.
"""

import asyncio
import subprocess
import os
import re
import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple


class SSHArmorer:
    """
    SSH Armorer Agent - MCP Client with private memory server.
    
    Spawns its own MCP Memory Server to log SSH resolution events
    separately from the main nanobot memory.
    """
    
    def __init__(self):
        """Initialize SSH Armorer with private MCP Memory Server."""
        self.memory_file_path = "/root/ssh_agent_memory.json"
        self.mcp_process: Optional[subprocess.Popen] = None
        self.mcp_client = None
        
    async def start_memory_server(self) -> bool:
        """
        Spawn private MCP Memory Server.
        
        Returns:
            bool: True if server started successfully
        """
        try:
            env = os.environ.copy()
            env["MEMORY_FILE_PATH"] = self.memory_file_path
            
            self.mcp_process = subprocess.Popen(
                ["npx", "-y", "@modelcontextprotocol/server-memory"],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give server time to start
            await asyncio.sleep(2)
            
            if self.mcp_process.poll() is None:
                print(f"✅ MCP Memory Server started with MEMORY_FILE_PATH={self.memory_file_path}")
                return True
            else:
                print(f"❌ MCP Memory Server failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Error starting MCP Memory Server: {e}")
            return False
    
    async def stop_memory_server(self):
        """Stop the private MCP Memory Server."""
        if self.mcp_process:
            self.mcp_process.terminate()
            await asyncio.sleep(1)
            if self.mcp_process.poll() is None:
                self.mcp_process.kill()
            print("✅ MCP Memory Server stopped")
    
    def diagnose_ssh_permission_issue(self, error_message: str, service: str) -> Optional[Dict]:
        """
        Diagnose SSH permission issue based on error message and service.
        
        Args:
            error_message: Error string (e.g., 'Permission denied', 'no such identity')
            service: Service name to check process user for
            
        Returns:
            Dict with diagnosis info or None if no issue found
        """
        # Check if error indicates permission issue
        permission_keywords = ['permission denied', 'no such identity', 'could not open', 'access denied']
        if not any(keyword in error_message.lower() for keyword in permission_keywords):
            return None
        
        # Find effective process user
        process_user = self._get_process_user(service)
        if not process_user:
            print(f"❌ Could not determine process user for service: {service}")
            return None
        
        # Check if running as non-root but trying to access /root/ keys
        # This is a heuristic - we'd need the actual key path in a real scenario
        # For now, we'll assume the issue if user != root
        
        diagnosis = {
            'error_message': error_message,
            'service': service,
            'process_user': process_user,
            'is_non_root': process_user != 'root',
            'requires_key_migration': process_user != 'root'
        }
        
        return diagnosis
    
    def _get_process_user(self, service: str) -> Optional[str]:
        """
        Find the effective user running a service.

        Args:
            service: Service name to search for
            
        Returns:
            Username or None if not found
        """
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return None
            
            # Parse ps aux output
            for line in result.stdout.split('\n'):
                if service.lower() in line.lower():
                    # ps aux format: USER PID %CPU %MEM VSZ RSS TTY STAT START TIME COMMAND
                    parts = line.split()
                    if len(parts) >= 1:
                        return parts[0]
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting process user: {e}")
            return None
    
    def fix_ssh_key_permissions(self, diagnosis: Dict, key_path: str) -> bool:
        """
        Fix SSH key permissions by migrating key to user's home directory.
        
        Args:
            diagnosis: Diagnosis dict from diagnose_ssh_permission_issue
            key_path: Current path to the SSH key (e.g., /root/.ssh/id_rsa)
            
        Returns:
            bool: True if fix was successful
        """
        process_user = diagnosis['process_user']
        
        if process_user == 'root':
            print("ℹ️  Running as root, no key migration needed")
            return True
        
        # Validate key path
        if not os.path.exists(key_path):
            print(f"❌ Key path does not exist: {key_path}")
            return False
        
        # Key Migration Sequence
        try:
            # 1. Create directory: /home/<Process_User>/.ssh
            user_ssh_dir = f"/home/{process_user}/.ssh"
            subprocess.run(
                ['mkdir', '-p', user_ssh_dir],
                check=True,
                timeout=10
            )
            print(f"✅ Created directory: {user_ssh_dir}")
            
            # 2. Copy key to new .ssh directory
            key_filename = os.path.basename(key_path)
            new_key_path = os.path.join(user_ssh_dir, key_filename)
            subprocess.run(
                ['cp', key_path, new_key_path],
                check=True,
                timeout=10
            )
            print(f"✅ Copied key: {key_path} -> {new_key_path}")
            
            # 3. Ownership: chown -R <Process_User>:<Process_User>
            subprocess.run(
                ['chown', '-R', f'{process_user}:{process_user}', user_ssh_dir],
                check=True,
                timeout=10
            )
            print(f"✅ Set ownership: {process_user}:{process_user} on {user_ssh_dir}")
            
            # 4. Permissions: chmod 700 on directory, 600 on key
            subprocess.run(['chmod', '700', user_ssh_dir], check=True, timeout=10)
            subprocess.run(['chmod', '600', new_key_path], check=True, timeout=10)
            print(f"✅ Set permissions: 700 on dir, 600 on key")
            
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error during key migration: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
    async def log_resolution_to_memory(self, service: str, old_path: str, new_path: str):
        """
        Log successful resolution to private MCP memory.
        
        Args:
            service: Service name that was fixed
            old_path: Original key path
            new_path: New key path after migration
        """
        try:
            # Create entity in memory
            entity_data = {
                "name": "SSH_Resolution_Log",
                "entityType": "SSH_Fix_Event",
                "observations": [
                    f"Fixed {service} permissions by migrating key from {old_path} to {new_path} on {datetime.now().isoformat()}."
                ]
            }
            
            # Write to memory file directly (simulating MCP create_entities)
            memory_data = {}
            if os.path.exists(self.memory_file_path):
                with open(self.memory_file_path, 'r') as f:
                    memory_data = json.load(f)
            
            if "entities" not in memory_data:
                memory_data["entities"] = []
            
            memory_data["entities"].append(entity_data)
            
            with open(self.memory_file_path, 'w') as f:
                json.dump(memory_data, f, indent=2)
            
            print(f"✅ Logged resolution to {self.memory_file_path}")
            
        except Exception as e:
            print(f"❌ Error logging to memory: {e}")
    
    async def run_diagnosis_and_fix(self, error_message: str, service: str, key_path: str) -> bool:
        """
        Complete workflow: diagnose and fix SSH permission issue.

        Args:
            error_message: Error string from SSH attempt
            service: Service name experiencing the issue
            key_path: Path to SSH key that needs fixing

        Returns:
            bool: True if issue was diagnosed and fixed
        """
        print(f"\n🔍 Diagnosing SSH permission issue for {service}...")

        # Step 1: Diagnose
        diagnosis = self.diagnose_ssh_permission_issue(error_message, service)
        if not diagnosis:
            print("ℹ️  No SSH permission issue detected")
            return False

        print(f"📋 Diagnosis: {json.dumps(diagnosis, indent=2)}")

        if not diagnosis['requires_key_migration']:
            print("ℹ️  No key migration required")
            return False

        # Step 2: Fix
        print(f"\n🔧 Fixing SSH key permissions...")
        success = self.fix_ssh_key_permissions(diagnosis, key_path)

        if success:
            # Step 3: Log to memory
            user_ssh_dir = f"/home/{diagnosis['process_user']}/.ssh"
            new_key_path = os.path.join(user_ssh_dir, os.path.basename(key_path))
            await self.log_resolution_to_memory(service, key_path, new_key_path)
            print(f"\n✅ SSH permission issue resolved for {service}")
            return True
        else:
            print(f"\n❌ Failed to fix SSH permission issue for {service}")
            return False

    def execute_command(self, server_ip: str, command: str, timeout: int = 30) -> Tuple[bool, str]:
        """
        Execute a command on a remote server via SSH.

        Args:
            server_ip: IP address or hostname of the target server
            command: Command to execute on the remote server
            timeout: Command timeout in seconds

        Returns:
            Tuple[bool, str]: (success, output) where success is True if command succeeded
        """
        ssh_cmd = f"ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o ConnectTimeout=10 moon2vex@{server_ip} '{command}'"

        try:
            result = subprocess.run(
                ssh_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                return (True, result.stdout)
            else:
                return (False, f"Command failed with exit code {result.returncode}\nStdout: {result.stdout}\nStderr: {result.stderr}")

        except subprocess.TimeoutExpired:
            return (False, f"Command timed out after {timeout} seconds")
        except Exception as e:
            return (False, f"Error executing command: {str(e)}")

    async def diagnose_and_fix(self, user_input: str) -> str:
        """
        Parse user input and execute the requested SSH command or diagnostic.

        Args:
            user_input: User command string (format: "/ssh <server> <command>")

        Returns:
            str: Result message to return to the user
        """
        parts = user_input.split()
        if len(parts) < 3:
            return "Usage: /ssh <server> <command>\nExample: /ssh moonbot2 apt-get update\nExample: /ssh factory-floor systemctl restart nginx"

        server_name = parts[1].lower()
        command = " ".join(parts[2:])

        # Server mapping (matching dispatcher.py)
        SERVERS = {
            "thecontroller": "localhost",
            "moonbot2": "165.245.132.82",
            "factory-floor": "165.245.134.252",
            "klume-dev-server": "165.245.128.251",
            "akex": "129.212.181.112"
        }

        if server_name not in SERVERS:
            return f"Unknown server: {server_name}\nAvailable servers: {', '.join(SERVERS.keys())}"

        server_ip = SERVERS[server_name]
        print(f"🔧 Executing command on {server_name} ({server_ip}): {command}")

        success, output = self.execute_command(server_ip, command)

        if success:
            return f"✅ Command executed successfully on {server_name}:\n\n```\n{output}\n```"
        else:
            return f"❌ Failed to execute command on {server_name}:\n\n```\n{output}\n```"


async def main():
    """Main entry point for SSH Armorer agent."""
    print("🛡️  SSH Armorer Agent Starting...")
    
    # Initialize agent
    armorer = SSHArmorer()
    
    # Start private memory server
    await armorer.start_memory_server()
    
    try:
        # Example usage (would be called by external system in production)
        # error_msg = "Permission denied (publickey)"
        # service = "ansible"
        # key_path = "/root/.ssh/id_rsa"
        # await armorer.run_diagnosis_and_fix(error_msg, service, key_path)
        
        print("✅ SSH Armorer Agent ready. Waiting for diagnosis requests...")
        print("   Use: await armorer.run_diagnosis_and_fix(error_message, service, key_path)")
        
        # Keep running
        while True:
            await asyncio.sleep(60)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down SSH Armorer Agent...")
    finally:
        await armorer.stop_memory_server()


if __name__ == "__main__":
    asyncio.run(main())
