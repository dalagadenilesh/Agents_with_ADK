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
import json
from toon import encode, decode

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
    table_scahema = {}

    inspector = sqlalchemy.inspect(engine)
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        
        column_dict = []
        
        for c in columns:
            column_dict.append({'name': c['name'],
                                    'type': c['type'],
                                    'default': c['default'],
                                    'nullable': c['nullable']})
        pk = inspector.get_pk_constraint(table_name)
        fk = inspector.get_foreign_keys(table_name)  
        
        table_scahema[table_name] = {
            'table name': table_name,
            "columns": column_dict,
            "primary_key": pk,
            "foreign_keys": fk}
    return encode(table_scahema, {"delimiter": "\t", "strict": True, "lengthMarker": "#"})

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
