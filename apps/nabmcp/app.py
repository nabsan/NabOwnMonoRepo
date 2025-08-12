import asyncio
import os
import json
import subprocess
import glob
from typing import List, Dict, Any, Union
from contextlib import AsyncExitStack
import gradio as gr
from gradio.components.chatbot import ChatMessage
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import requests
from dotenv import load_dotenv

load_dotenv()

# Ollama configuration
#OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
#OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
#OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))  # 5 minutes default
#OLLAMA_HOST = "http://host.docker.internal:11434"
OLLAMA_HOST = "http://172.21.32.1:11434"
OLLAMA_MODEL =  "llama3:latest"
OLLAMA_TIMEOUT = 3000  # 5 minutes default

# Event loop setup
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

class MCPClientWrapper:
    def __init__(self):
        self.sessions = {}  # Multiple sessions for different servers
        self.exit_stacks = {}  # Multiple exit stacks
        self.all_tools = []  # Combined tools from all servers
        self.server_tools = {}  # Tools organized by server

    def connect_multiple_servers(self, server_directory: str = "server") -> str:
        """Connect to multiple MCP servers in the specified directory"""
        return loop.run_until_complete(self._connect_multiple_servers(server_directory))

    async def _connect_multiple_servers(self, server_directory: str) -> str:
        """Asynchronously connect to multiple MCP servers"""
        # Clean up existing connections
        for exit_stack in self.exit_stacks.values():
            if exit_stack:
                await exit_stack.aclose()
        
        self.sessions.clear()
        self.exit_stacks.clear()
        self.all_tools.clear()
        self.server_tools.clear()

        # Find all Python files in the server directory
        import glob
        import os
        print(server_directory)
        if not os.path.exists(server_directory):
            return f"❌ Server directory '{server_directory}' not found."
        
        server_files = glob.glob(os.path.join(server_directory, "*.py"))
        
        if not server_files:
            return f"❌ No Python files found in '{server_directory}' directory."

        connected_servers = []
        failed_servers = []

        for server_path in server_files:
            server_name = os.path.basename(server_path)
            
            try:
                # Create exit stack for this server
                exit_stack = AsyncExitStack()
                self.exit_stacks[server_name] = exit_stack

                server_params = StdioServerParameters(
                    command="python",
                    args=[server_path],
                    env={
                        "PYTHONIOENCODING": "utf-8",
                        "PYTHONUNBUFFERED": "1"
                    }
                )

                stdio_transport = await exit_stack.enter_async_context(
                    stdio_client(server_params)
                )

                session = await exit_stack.enter_async_context(
                    ClientSession(stdio_transport[0], stdio_transport[1])
                )

                await session.initialize()

                # Get tools for this server
                tools_response = await session.list_tools()
                server_tools = tools_response.tools

                # Store session and tools
                self.sessions[server_name] = session
                self.server_tools[server_name] = server_tools
                self.all_tools.extend(server_tools)

                tool_names = [tool.name for tool in server_tools]
                connected_servers.append(f"  📁 {server_name}: {', '.join(tool_names)}")

            except Exception as e:
                failed_servers.append(f"  ❌ {server_name}: {str(e)}")
                # Clean up failed connection
                if server_name in self.exit_stacks:
                    try:
                        await self.exit_stacks[server_name].aclose()
                    except:
                        pass
                    del self.exit_stacks[server_name]

        # Build result message
        result_parts = []
        
        if connected_servers:
            result_parts.append("✅ Successfully connected to MCP servers:")
            result_parts.extend(connected_servers)
            result_parts.append(f"\n📊 Total tools available: {len(self.all_tools)}")
        
        if failed_servers:
            result_parts.append("\n⚠️ Failed to connect to some servers:")
            result_parts.extend(failed_servers)

        if not connected_servers:
            return "❌ Failed to connect to any MCP servers."

        return "\n".join(result_parts)

    def connect(self, server_path: str) -> str:
        """Connect to a single MCP server (for backward compatibility)"""
        if server_path == "server" or server_path.endswith("/"):
            # If directory is specified, use multiple server connection
            return self.connect_multiple_servers(server_path.rstrip("/"))
        else:
            # Single server connection
            return loop.run_until_complete(self._connect_single_server(server_path))

    async def _connect_single_server(self, server_path: str) -> str:
        """Connect to a single MCP server"""
        # Clean up existing connections
        for exit_stack in self.exit_stacks.values():
            if exit_stack:
                await exit_stack.aclose()
        
        self.sessions.clear()
        self.exit_stacks.clear()
        self.all_tools.clear()
        self.server_tools.clear()

        server_name = os.path.basename(server_path)
        
        try:
            exit_stack = AsyncExitStack()
            self.exit_stacks[server_name] = exit_stack

            is_python = server_path.endswith('.py')
            command = "python" if is_python else "node"
            
            server_params = StdioServerParameters(
                command=command,
                args=[server_path],
                env={
                    "PYTHONIOENCODING": "utf-8",
                    "PYTHONUNBUFFERED": "1"
                }
            )

            stdio_transport = await exit_stack.enter_async_context(
                stdio_client(server_params)
            )

            session = await exit_stack.enter_async_context(
                ClientSession(stdio_transport[0], stdio_transport[1])
            )

            await session.initialize()

            # Get available tools
            tools_response = await session.list_tools()
            tools = tools_response.tools

            self.sessions[server_name] = session
            self.server_tools[server_name] = tools
            self.all_tools = tools

            tool_names = [tool.name for tool in tools]
            return f"✅ Connected to MCP server successfully.\nServer: {server_name}\nAvailable tools: {', '.join(tool_names)}"

        except Exception as e:
            return f"❌ Connection error: {str(e)}"

    def call_ollama(self, messages: List[Dict[str, str]]) -> str:
        """Call Ollama to generate response with progress indication"""
        try:
            payload = {
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9
                }
            }
            
            print(f"🤖 Calling Ollama at {OLLAMA_HOST} with model {OLLAMA_MODEL}")
            print(f"⏱️  Timeout set to {OLLAMA_TIMEOUT} seconds")
            
            # Use a longer timeout for remote Ollama servers
            response = requests.post(
                f"{OLLAMA_HOST}/api/chat",
                #f"{OLLAMA_HOST}/v1/chat/completions",
                json=payload,
                timeout=OLLAMA_TIMEOUT,
                headers={
                    'Content-Type': 'application/json',
                    'Connection': 'keep-alive'
                }
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("message", {}).get("content", "Failed to get response.")
            
            print(f"✅ Ollama response received ({len(content)} characters)")
            return content
            
        except requests.exceptions.Timeout as e:
            error_msg = f"⏰ Ollama response timeout after {OLLAMA_TIMEOUT} seconds. The model might be processing a complex request or the server is under heavy load. Please try again or consider using a smaller model."
            print(f"❌ Timeout error: {e}")
            return error_msg
            
        except requests.exceptions.ConnectionError as e:
            error_msg = f"🔌 Cannot connect to Ollama at {OLLAMA_HOST}. Please check if Ollama is running and accessible."
            print(f"❌ Connection error: {e}")
            return error_msg
            
        except requests.exceptions.RequestException as e:
            error_msg = f"📡 Communication error with Ollama: {str(e)}"
            print(f"❌ Request error: {e}")
            return error_msg
            
        except Exception as e:
            error_msg = f"💥 Unexpected error occurred: {str(e)}"
            print(f"❌ Unexpected error: {e}")
            return error_msg

    def process_message(self, message: str, history: List[List[str]]) -> tuple:
        """Process message and generate response"""
        if not self.sessions:
            # Return in [user_message, assistant_message] format
            new_history = history + [[message, "Please connect to MCP server(s) first."]]
            return new_history, ""

        # Show processing message immediately
        processing_history = history + [[message, "🤖 Processing your request... This may take a moment for complex queries."]]
        
        try:
            # Convert history to internal format for processing
            internal_history = []
            for chat_pair in history:
                if len(chat_pair) >= 2:
                    internal_history.append({"role": "user", "content": chat_pair[0]})
                    internal_history.append({"role": "assistant", "content": chat_pair[1]})

            new_messages = loop.run_until_complete(self._process_query(message, internal_history))
            
            # Extract assistant response
            assistant_response = new_messages[0]["content"] if new_messages else "Sorry, I couldn't generate a response."
            
            # Return in Gradio chatbot format: [[user_msg, assistant_msg], ...]
            new_history = history + [[message, assistant_response]]
            return new_history, ""
            
        except Exception as e:
            error_response = f"❌ Error processing your request: {str(e)}"
            new_history = history + [[message, error_response]]
            return new_history, ""

    async def _process_query(self, message: str, history: List[Dict[str, Any]]):
        """Asynchronously process query"""
        # Convert history to Ollama message format
        ollama_messages = []
        
        # Add system message with all available tools
        system_msg = """You are a helpful AI assistant. Use available tools when necessary.
Available tools: """ + ", ".join([f"{tool.name}: {tool.description}" for tool in self.all_tools])
        
        ollama_messages.append({"role": "system", "content": system_msg})
        
        # Add conversation history
        for msg in history:
            role = msg.get("role")
            content = msg.get("content")
            
            if role in ["user", "assistant"] and content:
                ollama_messages.append({"role": role, "content": content})

        # Add current message
        ollama_messages.append({"role": "user", "content": message})

        # Check if tools are needed (simple heuristic)
        tools_needed = await self._check_if_tools_needed(message)
        
        if tools_needed:
            # Execute tools
            tool_results = await self._execute_tools(message)
            if tool_results:
                enhanced_message = f"{message}\n\nTool execution results:\n{tool_results}"
                ollama_messages[-1]["content"] = enhanced_message

        # Generate response with Ollama
        response = self.call_ollama(ollama_messages)
        
        return [{"role": "assistant", "content": response}]

    async def _check_if_tools_needed(self, message: str) -> bool:
        """Check if message requires tools"""
        # Enhanced keyword-based detection for multiple servers including RAG
        tool_keywords = {
            "disk": ["disk", "space", "usage", "storage", "capacity", "free", "drive", "volume"],
            "os": ["os", "operating system", "system", "platform", "version", "cpu", "memory", "process", "rhel"],
            "system": ["system", "resource", "performance", "uptime", "boot"],
            "rag": ["search", "find", "document", "rag", "knowledge", "information", "lookup", "query", "answer", "question"]
        }
        
        message_lower = message.lower()
        for tool_type, keywords in tool_keywords.items():
            if any(keyword.lower() in message_lower for keyword in keywords):
                return True
        return False

    async def _execute_tools(self, message: str) -> str:
        """Execute appropriate tools from all connected servers"""
        results = []
        message_lower = message.lower()
        
        # Iterate through all servers and their tools
        for server_name, session in self.sessions.items():
            server_tools = self.server_tools.get(server_name, [])
            
            for tool in server_tools:
                try:
                    tool_executed = False
                    
                    # Disk-related tools
                    if ("disk" in tool.name.lower() and 
                        any(keyword in message_lower for keyword in ["disk", "space", "usage", "storage", "capacity", "free"])):
                        
                        result = await session.call_tool(tool.name, {})
                        results.append(f"[{server_name}] {tool.name}: {result.content[0].text if result.content else 'No result'}")
                        tool_executed = True
                        
                    # OS and system-related tools
                    elif (("os" in tool.name.lower() or "system" in tool.name.lower() or "process" in tool.name.lower()) and 
                          any(keyword in message_lower for keyword in ["os", "operating", "system", "platform", "version", "cpu", "memory", "process", "rhel", "resource", "uptime"])):
                        
                        result = await session.call_tool(tool.name, {})
                        results.append(f"[{server_name}] {tool.name}: {result.content[0].text if result.content else 'No result'}")
                        tool_executed = True
                    
                    # RHEL-specific tools
                    elif ("rhel" in tool.name.lower() and 
                          any(keyword in message_lower for keyword in ["rhel", "red hat", "linux", "version", "release"])):
                        
                        result = await session.call_tool(tool.name, {})
                        results.append(f"[{server_name}] {tool.name}: {result.content[0].text if result.content else 'No result'}")
                        tool_executed = True
                    
                    # RAG-related tools
                    elif (("rag" in tool.name.lower() or "search" in tool.name.lower() or "answer" in tool.name.lower()) and 
                          any(keyword in message_lower for keyword in ["search", "find", "document", "rag", "knowledge", "information", "lookup", "query", "answer", "question"])):
                        
                        # For RAG search and answer tools, pass the message as query/question
                        if "search" in tool.name.lower():
                            result = await session.call_tool(tool.name, {"query": message})
                        elif "answer" in tool.name.lower():
                            result = await session.call_tool(tool.name, {"question": message})
                        else:
                            result = await session.call_tool(tool.name, {})
                        
                        results.append(f"[{server_name}] {tool.name}: {result.content[0].text if result.content else 'No result'}")
                        tool_executed = True
                    
                    # Collection info tools
                    elif ("collection" in tool.name.lower() or "info" in tool.name.lower()) and \
                         any(keyword in message_lower for keyword in ["collection", "info", "status", "statistics"]):
                        
                        result = await session.call_tool(tool.name, {})
                        results.append(f"[{server_name}] {tool.name}: {result.content[0].text if result.content else 'No result'}")
                        tool_executed = True
                    
                    # Generic system info if user asks for "everything" or "all info"
                    elif any(phrase in message_lower for phrase in ["everything", "all info", "complete", "full", "detailed"]):
                        result = await session.call_tool(tool.name, {})
                        results.append(f"[{server_name}] {tool.name}: {result.content[0].text if result.content else 'No result'}")
                        tool_executed = True
                        
                except Exception as e:
                    results.append(f"[{server_name}] Error in {tool.name}: {str(e)}")
        
        return "\n\n".join(results) if results else ""

# Create MCP client instance
mcp_client = MCPClientWrapper()

def create_interface():
    """Create Gradio interface"""
    
    with gr.Blocks(title="nabmcp2 - MCP Host with Ollama", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🤖 nabmcp2 - MCP Host with Ollama")
        gr.Markdown("Chat interface combining on-premise Ollama with MCP servers")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## MCP Server Connection")
                server_path = gr.Textbox(
                    label="MCP Server Path",
                    value="server",
                    placeholder="Enter 'server' for all servers, or specific file like 'server/mcp_disk_usage.py'"
                )
                connect_btn = gr.Button("Connect", variant="primary")
                connection_status = gr.Textbox(
                    label="Connection Status",
                    interactive=False,
                    max_lines=3
                )
                
                gr.Markdown("### Configuration")
                gr.Markdown(f"**Ollama Host:** {OLLAMA_HOST}")
                gr.Markdown(f"**Ollama Model:** {OLLAMA_MODEL}")
                gr.Markdown(f"**Timeout:** {OLLAMA_TIMEOUT}s")
                
                # Display image
                gr.Image("images/robo.jpg", label="AI Assistant", show_label=False, height=200)
            
            with gr.Column(scale=2):
                gr.Markdown("## Chat")
                chatbot = gr.Chatbot(
                    height=500,
                    label="Conversation History",
                    avatar_images=("images/m_.jpeg", "images/robo.jpg")
                )
                
                with gr.Row():
                    msg = gr.Textbox(
                        label="Message",
                        placeholder="Type your message here...",
                        scale=4
                    )
                    send_btn = gr.Button("Send", variant="primary", scale=1)
                
                clear_btn = gr.Button("Clear History", variant="secondary")

        # Event handlers
        connect_btn.click(
            fn=mcp_client.connect,
            inputs=[server_path],
            outputs=[connection_status]
        )
        
        send_btn.click(
            fn=mcp_client.process_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        )
        
        msg.submit(
            fn=mcp_client.process_message,
            inputs=[msg, chatbot],
            outputs=[chatbot, msg]
        )
        
        clear_btn.click(
            fn=lambda: ([], ""),
            outputs=[chatbot, msg]
        )

    return demo

if __name__ == "__main__":
    # Check Ollama connection
    try:
        print(f"🔍 Checking Ollama connection at {OLLAMA_HOST} (timeout: {OLLAMA_TIMEOUT}s)...")
        response = requests.get(f"{OLLAMA_HOST}/api/version", timeout=10)
        version_info = response.json()
        print(f"✅ Ollama connection successful: {OLLAMA_HOST}")
        print(f"   Version: {version_info.get('version', 'unknown')}")
        
        # Check if model is available
        try:
            models_response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
            models_data = models_response.json()
            model_names = [model['name'] for model in models_data.get('models', [])]
            
            if OLLAMA_MODEL in model_names:
                print(f"✅ Model '{OLLAMA_MODEL}' is available")
            else:
                print(f"⚠️  Model '{OLLAMA_MODEL}' not found. Available models: {', '.join(model_names)}")
                print(f"   Consider pulling the model: ollama pull {OLLAMA_MODEL}")
                
        except Exception as model_check_error:
            print(f"⚠️  Could not check available models: {model_check_error}")
            
    except Exception as e:
        print(f"⚠️  Ollama connection warning: {e}")
        print("Please ensure Ollama is running and accessible.")
        print(f"   Test with: curl {OLLAMA_HOST}/api/version")
    
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )