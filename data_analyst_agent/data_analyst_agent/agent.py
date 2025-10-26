

from google.adk.agents import LlmAgent, Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams, StdioServerParameters, StdioConnectionParams
from . import prompt
import os
from typing import List, Dict
from decimal import Decimal
from google.adk.tools.agent_tool import AgentTool
from .sub_agents.data_extraction_agent import data_extraction
from .sub_agents.sql_query_genrator import nl2sql_agent



TARGET_FOLDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "./agetfolder")
os.makedirs(TARGET_FOLDER_PATH, exist_ok=True) 



root_agent = LlmAgent(
    name = "data_analyst_agent",
    model = "gemini-2.5-pro",
    instruction = prompt.SQ_CODE_GENRATOR,
    tools = [
      McpToolset(
            connection_params = StdioConnectionParams(
                server_params = StdioServerParameters(
                    command = 'npx',
                    args = [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        os.path.abspath(TARGET_FOLDER_PATH),
                    ],
                ),
            ),
        )
   ],
   sub_agents = [nl2sql_agent, data_extraction]
)