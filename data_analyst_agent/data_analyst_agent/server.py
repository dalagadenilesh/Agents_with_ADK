from fastmcp import FastMCP, Client
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import sqlite
from sqlalchemy import Table, MetaData, create_engine
from google.cloud.sql.connector import Connector
import sqlalchemy
from typing import List, Dict
from typing import List, Dict
from decimal import Decimal
import os


mcp_server = FastMCP()
connector = Connector()

db_name = os.getenv('database_name')
username = os.getenv('username')
db_pass = os.getenv('db_passward')
connection_name = os.getenv('connection_name')


engine = sqlalchemy.create_engine(
    "mysql+pymysql://", 
    creator = lambda: connector.connect(
        connection_name,
        "pymysql",
        user = username,
        password = db_pass,
        db = db_name,
    ),
)

@mcp_server.tool
def greeting_tool(name: str):
    """Generates a personalized greeting.

    Args:
        name: name of the person to greet
    
    returns: A greeting string

    """

    return f"Hello {name}, Nice to meet you."

@mcp_server.tool
def get_sql_table_schema():
    '''Get get schema of all tables present in database'''
    inspector = sqlalchemy.inspect(engine)
    
    context = ""
    for table_name in inspector.get_table_names():
        context += f"""TABLE: {table_name}\n\tColumns"""
        columns = inspector.get_columns(table_name)

        for c in columns:
            comment = f"Column of Table {table_name} which is of type {c['type']}"

            if c['comment']:
                comment = c['comment'] + comment

            context += f"""\n\t\t- {c['name']}\n\t\t\tType : {c['type']}\n\t\t\tdefault: {c['default']}\n\t\t\tcomment:  {comment}\n\t\t\tnullable: {c['nullable']}\n\n\t\t"""
          
        context += f"""\n\tPrimary-key:"""
        for key, value in inspector.get_pk_constraint(table_name).items():
            context += f"""{key}: {value}"""
        context += f"""\n\tforeign-keys: {inspector.get_foreign_keys(table_name)}\n\n\n"""
 
    return context

@mcp_server.tool
def validate_query(query: str) -> str:
    """
    Validate Sql Query against databse without Fetching data.
    
    Args:
     query: Sql Query to check its valdity against database.
    
    Returns:
     result - Query validation error
    """
    query_text = query.split('\n', 1)[-1].strip()

    conn = engine.connect()
    result = "No Error"
    try:
        sql_result = conn.execute(sqlalchemy.text(f"Explain {query_text}"))
    except Exception as e:
        result =  str(e)

    return result


@mcp_server.tool
def get_sql_data(query: str) -> str:
    """
    Executes a raw SQL query to fetch data from the database.

    Args:
        query: The complete SQL query string to execute.
    
    Returns:
        json data
    """
    from decimal import Decimal
    import json

    query_text = query.split('\n', 1)[-1].strip()

    # 2. Execute the query
    with engine.connect() as conn:
        sql_result = conn.execute(sqlalchemy.text(query_text)).mappings().all()

    final_result = []
    for row in sql_result:
        processed_row = {}
        for k, v in row.items():
            # Convert Decimal to float for generic numeric handling
            if isinstance(v, Decimal):
                processed_row[k] = float(v)
            else:
                processed_row[k] = v
        final_result.append(processed_row)
    
        # Return the List[Dict] as specified in the function signature
    return json.dumps(final_result, indent = 2)


if __name__=='__main__':
    mcp_server.run(transport = 'stdio')
