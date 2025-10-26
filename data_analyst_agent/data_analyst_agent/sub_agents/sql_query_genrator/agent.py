from google.adk.agents import LlmAgent, Agent, LoopAgent, SequentialAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams, StdioServerParameters, StdioConnectionParams
import os
from decimal import Decimal
from google.adk.tools.tool_context import ToolContext



QUERY_VALIDATION = 'Query_validations'
SQL_QUERY_VAR = 'SQL_Query'
SQL_DATA_VAR = 'SQL_Query'


def exit_loop(tool_context: ToolContext):
  """Call this function ONLY when the No Error in generated sql query, signaling the iterative process should end."""
  print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
  tool_context.actions.escalate = True
  return {}


query_generator = Agent(
    name = 'sql_query_generator',
    model = "gemini-2.5-pro",
    description = 'You are an expert SQL query generator. Your sole function is to translate user requests into accurate, optimized SQL queries. Only output the SQL query itself, unless the user explicitly asks for an explanation.',
    instruction = """Your Job is to Generate SQL Query from user statement using available Database Table Schema.
    
    Use get_sql_table_schema tool to get schema for tables available in database.
    Analyze table schema and user statement.
    Do not assume any tables and columns. Use available tables and their columns only to generate SQL query from user statement.
    
    Genrate SQL Query.
    Output *only* the SQL query text. Do not add introductions or explanations.
    """,
    output_key = 'SQL_Query',
    tools = [
        McpToolset(
            connection_params = StreamableHTTPConnectionParams(
               url = 'http://127.0.0.1:5050/mcp/',
            ),
            tool_filter = ['get_sql_table_schema']
        )]
)





query_critix = Agent(
    name = 'sql_query_validator_agent',
    model = "gemini-2.5-pro",
    description = """A specialized validation engine that executes a given SQL query against the database to diagnose and report any execution faults (errors).""",
    instruction = """
    Your task is to process the user's input {{SQL_Query}}, treating it as a raw SQL query. You **must** use the available tool, 'validate_query', to attempt execution.
    """,
    output_key = 'Query_validations',
    tools = [
        McpToolset(
            connection_params = StreamableHTTPConnectionParams(
               url = 'http://127.0.0.1:5050/mcp/',
            ),
           tool_filter = ['validate_query']
       )]
)




query_modifier_agent = Agent(
    name = 'sql_query_modifier',
    model = "gemini-2.5-pro",
    description = """A **Diagnostic Resolution Module (DRM)** instantiated for the domain of Structured Query Language (SQL).
    Its function is the **algorithmic validation, error diagnosis, and syntactic/semantic remediation** of submitted SQL assets against provided execution environment feedback.""",
    instruction = """
    If {{Query_validations}} is *exactly* No Error then YOU MUST CALL exit_loop function. Do Not output any text.
    ELSE 
    
    Stage 1: Invoke the custom tool get_sql_table_schema to retrieve the definitive, current database schema. This output serves as the Ground Truth for all subsequent SQL operations.
    Stage 2: **Schema Mapping** and **Root Cause Identification**
        Compare the structure of the previously generated {{SQL_Query}} against the Ground Truth Schema retrieved in Stage 1.
        Analyze {{Query_validations}}, previously generated {{SQL_Query}} and Ground Truth Schema retrieved in Stage 1 to perform root cause Analysis.
    
    Stage 4: Refinement and Output Synthesis
        Generate the Refined/Modified SQL Query by minimally altering the prior query to achieve compliance with the Ground Truth Schema retrieved in Stage 1.
    *output* only refined/modified sql query. 
    Do not add explainations. Either output refined/modified sql query or calls exit_loop function.
""",
   output_key = 'SQL_Query',
   tools = [McpToolset(
           connection_params = StreamableHTTPConnectionParams(
               url = 'http://127.0.0.1:5050/mcp/',
           ),
           tool_filter = ['get_sql_table_schema']
       ),
       exit_loop]
)



sql_modifier = LoopAgent(
    name = 'query_modifier',
    sub_agents = [query_critix, query_modifier_agent],
    max_iterations = 2
)


nl2sql_agent = SequentialAgent(
    name = 'nl_to_sql',
    description = 'You are important assistant agent which genrate SQL query from user statement.',
    sub_agents = [query_generator, sql_modifier]
)