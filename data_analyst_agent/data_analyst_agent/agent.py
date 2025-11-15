

from google.adk.agents import LlmAgent, Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams, StdioServerParameters, StdioConnectionParams
from . import prompt
import os
from typing import List, Dict
from decimal import Decimal
from google.adk.agents import FunctionTool
from google.adk.tools.agent_tool import AgentTool
from google.adk.agents import LlmAgent, Agent, LoopAgent, SequentialAgent
from decimal import Decimal
from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext
from typing import Optional
import google.genai.types as types
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
import warnings
import asyncio
from google.adk.runners import Runner
from toon import encode, decode

warnings.filterwarnings("ignore", category=UserWarning, module=".*google\\.adk.*")

TARGET_FOLDER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "./agetfolder")
os.makedirs(TARGET_FOLDER_PATH, exist_ok=True) 

session_service = InMemorySessionService()
artifact_service = InMemoryArtifactService()


user = os.environ.get('username')
db_pass = os.environ.get('db_passward')
connection = os.environ.get('connection_name')
db_name = os.environ.get('database_name')


toolset = McpToolset(
  connection_params = StdioConnectionParams(
                    server_params = StdioServerParameters(
                        command = 'python',
                        args = [os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")],
                        env = {"username": user,
                                "db_passward": db_pass,
                                "connection_name": connection,
                                "database_name": db_name
                                }
                    ),
                    timeout = 20,
  ),
)

fileserver_mcp_tool = McpToolset(
            connection_params = StdioConnectionParams(
                server_params = StdioServerParameters(
                    command = 'npx',
                    args = [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        os.path.abspath(TARGET_FOLDER_PATH),
                    ],
                ),
                timeout = 20,
            ),
        )


async def save_master_data_tool(text:str, tool_context: ToolContext):
    """
    Tool to Save Database table Schema content in artifact

    Args:
        text - Database table schema
    
    Returns:
        None
    """
    filename = 'schema.txt'

    
    report_artifact = types.Part.from_bytes(
    data = text.encode("utf-8"),
    mime_type = "application/json")

    version = await tool_context.save_artifact(
        filename = filename,
        artifact = report_artifact
    )
    tool_context.state['table_schema_filename'] = filename

    return {'status': "success", 'message': f'table scahema saved to {filename}'}


async def load_master_data_tool(tool_context: ToolContext, table_names: List[str] = None):

    """Loads the complete, raw content of the database schema from artifact.

    Args:
        table_names (List[str], default None): table name to get table scahma

    Returns:
        str: Full database schema content
    """
    spec = {"delimiter": "\t", "strict": True, "lengthMarker": "#"}
    filename = tool_context.state.get('table_schema_filename')
    report_artifact = await tool_context.load_artifact(filename = filename)

    if report_artifact.inline_data and report_artifact.inline_data.data:
        text = report_artifact.inline_data.data.decode("utf-8")
    
    if not table_names:
        return text
    
    if isinstance(table_names, List) and len(table_names) > 0:
        try:
            json_data = decode(text, spec)
            
            schema = {}
            for table in table_names:
                schema[table] = json_data.get(table)
            
            return encode(schema, spec)
        
        except:
            pass
    
    return text




def exit_loop(tool_context: ToolContext):
  """Call this function ONLY when the No Error in generated sql query, signaling the iterative process should end."""
  tool_context.actions.escalate = True
  return {}

def get_sql_table_schema_wrapper(text: str, tool_context: ToolContext):
    """this tool is to save extracted schema text in session state
    Args:
        text : table Schama text to save
    Returns:

    """
    tool_context.state['table_schema'] = text

get_sql_table_schema_wrapper_tool = FunctionTool(get_sql_table_schema_wrapper)
load_schema_table_tool = FunctionTool(load_master_data_tool)
save_schema_table_tool = FunctionTool(save_master_data_tool)

query_generator = Agent(
    name = 'sql_query_generator',
    model = "gemini-2.5-pro",
    description = 'You are an expert SQL query generator. Your sole function is to translate user requests into accurate, optimized SQL queries. Only output the SQL query itself, unless the user explicitly asks for an explanation.',
    instruction = """
    Your Job is to Generate an accurate SQL Query from the user statement, {{NL_Query}}, using the available Database Table Schema.
    
    ** Workflow **

    1.  Check the state variable ** {{table_schema_filename}} **.
    2.  If ** {{table_schema_filename}} ** is exactly "No Schema File":
        - Call `get_sql_table_schema` to retrieve the database table schema.
        - Then, immediately call `save_schema_table_tool` to save that schema as an artifact.
    
    3.  Invoke `load_schema_table_tool` without table_names and the user statement ** {{NL_Query}} ** to generate the SQL query.
    4.  **Constraint:** Do not assume any tables or columns. Use only the objects explicitly available in the schema.
    5.  **Self-Correction:** After generation, perform a syntax and logic error analysis on the query. Correct any issues, ensuring column names are **not** quoted.

    ** Agent Output Requirement **
    * You must output Generated SQL query. Do not add introductions or explanations.
    """,
    output_key = 'SQL_Query',
    tools = [
        toolset, get_sql_table_schema_wrapper_tool
    ]
)


query_critix = Agent(
    name = 'sql_query_validator_agent',
    model = "gemini-2.5-pro",
    description = """A specialized validation engine that executes a given SQL query against the database to diagnose and report any execution faults (errors).""",
    instruction = """
    Your Job is to validate SQL Query, {{SQL_Query}} using 'validate_query' tool.
    After receiving the tool's output (which will be 'No Error' or an error message string), **you MUST output ONLY the exact content of the tool's result string** as your final answer.
    Do not add any explanations, prefixes, or conversational text.
    """,
    output_key = 'Query_validations',
    tools = [
        toolset]
)


query_modifier_agent = Agent(
    name = 'sql_query_modifier',
    model = "gemini-2.5-pro",
    description = """A **Diagnostic Resolution Module (DRM)** instantiated for the domain of Structured Query Language (SQL).
    Its function is the **algorithmic validation, error diagnosis, and syntactic/semantic remediation** of submitted SQL assets against provided execution environment feedback.""",
    instruction = """
    If **{{Query_validations}}** is **exactly** "No Error", do **not** process any further steps, Your only action is to output only the state variable {{SQL_Query}} and then terminate your reasoning by calling exit_loop tool.
    
    Your job is to analyze a previously generated SQL query, {{SQL_Query}}, and validation results, {{Query_validations}}, then output a corrected SQL query.

    **Available Context:**
    * **User Statement:** {{NL_Query}}
    * **Ground Truth Schema:** Invoke `load_schema_table_tool` tool with required table_names.
    * **Prior SQL Query:** {{SQL_Query}}
    * **Query Validation Feedback:** {{Query_validations}}
    
    Analyze SQL Query Context and Use Only tables from **Query Validation Feedback** which are needed to proceed.
    
    **Procedure:**

    **1. Root Cause Analysis (Process Only If Error Exists):**
    * **CRITICAL STEP:** Compare the **Prior SQL Query** against the **Ground Truth Schema** and the **Query Validation Feedback**.
    * Identify the exact table/column mismatch, syntax error, or logical error that caused the validation to fail.

    **2. Query Refinement:**
    * Generate the **Refined SQL Query** by making the **minimal necessary alteration** to the **Prior SQL Query** to resolve the root cause identified in Step 1.
    * The refined query **must** comply with the Ground Truth Schema and satisfy the User Statement.

    **3. Final Action:**
    * If you believe the Refined SQL Query is correct and addresses the validation feedback, **output only the Refined SQL Query text.**
    * Do not include any explanations, introductions, or conversational text.
    
""",
   output_key = 'SQL_Query',
   tools = [toolset,
       exit_loop]
)


sql_modifier = LoopAgent(
    name = 'query_modifier',
    sub_agents = [query_critix, query_modifier_agent],
    max_iterations = 2
)

def check_initial_intent(callback_context: CallbackContext, **kwargs):
    if callback_context.user_content and callback_context.user_content.parts:
        initial_text = callback_context.user_content.parts[0].text
        callback_context.state['NL_Query'] = initial_text
    
    if callback_context.state.get('table_schema', ""):
        pass
    else:
        callback_context.state['table_schema'] = 'No Table Schema'


nl2sql_agent = SequentialAgent(
    name = 'nl_to_sql',
    description = """A multi-step agent designed for robust SQL query generation. It first creates a raw SQL query from natural language and then
    passes that query to an internal modifier sub-agent for validation, optimization, and correction before final execution or display.
    Use for complex or potentially ambiguous data requests."""
    sub_agents = [query_generator, sql_modifier],
    before_agent_callback = check_initial_intent
)


data_extraction = Agent(
    name = 'data_extractor',
    model = "gemini-2.5-pro",
    description = """
    This agent's primary function is to run the existing SQL query (e.g., SELECT, INSERT, UPDATE) against the database, retrieve the resulting data,
    and then perform any necessary post-processing or saving operations (e.g., saving to a file, returning the final result to the user).
    Do not call this agent for query generation or correction; call it only for execution.""",
    
    instruction = """You are an Experxt Sql Developer. Your Job is to Extract data from database using {{SQL_Query}} query.
    Use get_sql_data tool to fetch data from database.
    """,
    output_key = 'SQL_DATA',
    tools = [
        toolset, fileserver_mcp_tool
    ]
)

def session_init(callback_context: CallbackContext, **kwargs): 
    callback_context.state['invocation_message'] = callback_context.user_content.parts[0].text

root_agent = LlmAgent(
   name = 'data_analyst_agent',
   model = "gemini-2.5-pro",
   description = 'You are an SQL Expert assisting on SQL Query generation and data data extraction.',
   instruction = """

    You are the primary router agent. Your sole function is to analyze the user's request, {{invocation_message}}, and determine the appropriate specialized agent to handle the task.

    1.  **If the user is asking for the generation of a database query, SQL analysis, or a new report template,** you must delegate the task to the **'nl2sql_agent'** agent.
    2.  **If the user is asking for data retrieval, to execute a query, or explicitly asking to save, export, or download data,** you must delegate the task to the **'data_extraction'** agent.
    3.  **If the request is a general greeting, conversation, or irrelevant to SQL/data,** do not delegate or call any tools. You will handle the conversational response.

    Your output must be clear and direct, either a conversational response or a structured call to the delegation tool.
  
   """,
   
   sub_agents = [nl2sql_agent, data_extraction],
   before_agent_callback = session_init
)


runner = Runner(
    agent = root_agent,
    app_name = "DaT-a-NaLySt",
    session_service = session_service,
    artifact_service = artifact_service # Provide the service instance here
)