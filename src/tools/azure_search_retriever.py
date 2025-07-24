import os
import re

import logging
logging.basicConfig(level=logging.INFO)
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

class AzureSearch_nlq_sql_db:
    """Class to connect to Azure search AI"""
 
    def __init__(self):
        self.key = os.getenv("AZURE_AI_KEY")
        self.endpoint = os.getenv("AZURE_AI_ENDPOINT")
        self.index_name = os.getenv("AZURE_AI_INDEX_NAME")
        self.embed_deployment = os.getenv("AZURE_AI_MODEL_NAME")
        
        self.credential = AzureKeyCredential(self.key)
        self.search_client, self.llm = self.get_vectordb()
 
    def get_vectordb(self):
        """Get vector db connection"""
        search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
        
        llm = AzureOpenAIEmbeddings(
            azure_deployment=self.embed_deployment,
        )
        
        return search_client, llm
    
    def invoke_index(self, query):
        """Search the index for similar SQL examples"""
        # Generate embedding for the query
        embedding = self.llm.embed_query(text=query)
        
        # Create a vector query
        vector_query = VectorizedQuery(
            vector=embedding, 
            k_nearest_neighbors=5, 
            fields="embedding", 
            exhaustive=True
        )
 
        # Search using both text and vector
        results = self.search_client.search(  
            search_text=query,  
            vector_queries=[vector_query],
            select=["question", "sql", "explanation"],
            top=2
        )
 
        # Format the results
        formatted_examples = []
        for i, result in enumerate(results, 1):
            formatted_examples.append(
                f"Example {i}:\n"
                f"Question: {result['question']}\n"
                f"SQL: {result['sql']}\n"
                f"Explanation: {result.get('explanation', '')}\n"
            )
        
        if not formatted_examples:
            return "No similar SQL examples found."
            
        return "\n".join(formatted_examples)

azure_search = AzureSearch_nlq_sql_db()


@tool
def retrieve_sql_examples(query: str) -> str:
    """Retrieve similar SQL examples that match the user's question using Azure AI Search.
    This tool finds SQL patterns for complex analytical queries like year-over-year comparisons.
    """
    try:
        logging.info(f"retrieve_sql_examples called with query: {query}")
        results=azure_search.invoke_index(query)
        logging.info(f"Azure Search returned examples: {results}")
        return results

    except Exception as e:
        return f"Error retrieving SQL examples: {str(e)}"