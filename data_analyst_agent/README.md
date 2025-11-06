
# Data Analyst Agent with ADK

## Overview

The Data Analyst Agent is an intelligent multi-stage system designed to bridge the gap between natural language queries and data-driven insights.
It enables users to express analytical questions in plain English and receive automatically generated SQL queries, retrieved results, and visual interpretations — all within a unified agent pipeline.

This agent integrates schema-aware SQL generation, secure data retrieval, artifact storage, and interactive data visualization capabilities, making it a complete AI-powered data analysis assistant.



## Key Features

#### 🗣️ Natural Language to SQL Query Generation
Converts user-provided analytical statements into optimized SQL queries.
The agent uses schema-guided reasoning to ensure all queries strictly align with actual database tables and columns.

#### 🧩 Schema-Based Text-to-SQL Generation
The agent never assumes schema details — it dynamically retrieves and interprets table schemas before generating SQL queries, ensuring accuracy and safety across databases.

#### 🗄️ MCP Server Tools for Database Retrieval
Implements MCP server-integrated tools for executing SQL queries, fetching table data, and interacting securely with the database.

#### 💾 MCP FileServer for Data Storage
Retrieved schemas, query results, and generated insights are stored as artifacts using an MCP FileServer, enabling persistent state management and inter-agent communication.

#### 📊 Plotly Visualization Tool
Transforms tabular data into meaningful visual insights using Plotly, generating graphs and charts that complement analytical summaries.

