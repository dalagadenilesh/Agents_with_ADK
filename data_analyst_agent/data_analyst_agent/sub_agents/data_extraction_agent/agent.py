
from google.adk.agents import LlmAgent, Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams, StdioServerParameters, StdioConnectionParams
import os
# from pydantic import BaseModel, Field
from typing import List, Dict
from decimal import Decimal
from google.adk.tools.agent_tool import AgentTool


data_extraction = Agent(
    name = 'data_extractor',
    model = "gemini-2.5-pro",
    description = "You are helpful assitant to extract data from database.",
    instruction = """You are an Experxt Sql Developer. Your Job is to Extract data from database using {{SQL_Query}} query.
    Use get_sql_data tool to fetch data from database.
    """,
    output_key = 'SQL_DATA',
    tools = [
        McpToolset(
           connection_params = StreamableHTTPConnectionParams(
               url = 'http://127.0.0.1:5050/mcp/',
           ),
           tool_filter = ['greet', 'get_sql_data']
        )
    ]
)