from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import re
from starlette.responses import StreamingResponse
import json
import asyncio
from src.agents.LangBotAgent import LangBotAgent, Response
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# from src.tools.azure_search_index import initialize_search_index

app = FastAPI(
    title="DigiBook Bot API",
    description="API for querying database with natural language"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class ApiResponse(BaseModel):
    answer: str
    sql_query: Optional[str] = None
    reframed_query: Optional[str] = None
    ba_analysis: Optional[str] = None
    suggested_questions: Optional[List[str]] = None
    is_chitchat: bool = False
    query_result: Optional[str] = None 

agent = LangBotAgent()

def extract_message_content(chunk):
    if isinstance(chunk, dict):
        if 'supervisor' in chunk and 'structured_response' in chunk['supervisor']:
            sr = chunk['supervisor']['structured_response']
            if hasattr(sr, 'dict'):
                sr = sr.dict()
            return sr  # Return the dict for final output
        for agent_key in chunk:
            agent_data = chunk[agent_key]
            if isinstance(agent_data, dict) and 'messages' in agent_data:
                messages = agent_data['messages']
                for m in reversed(messages):
                    if isinstance(m, AIMessage) or isinstance(m, HumanMessage) or isinstance(m, ToolMessage):
                        content = getattr(m, 'content', None)
                        if content:
                            return {"type": "notification", "agent": agent_key, "content": content}
    return {"type": "chunk", "data": str(chunk)}

@app.post("/ask")
async def ask_database_stream(request: QueryRequest):
    """
    Process a natural language question and stream the database results,
    including intermediate agent notifications
    """
    async def stream_generator():
        final_output = None
        try:
            # Create the async generator
            async_gen = agent.astream_database(request.query)
            
            # Process each chunk as it arrives
            async for chunk in async_gen:
                pretty = extract_message_content(chunk)
                
                # If we have the final structured output
                if isinstance(pretty, dict) and not pretty.get("type"):
                    final_output = pretty
                    yield f"data: {json.dumps({'type': 'final', 'data': pretty})}\n\n"
                    break

                elif isinstance(pretty, dict) and pretty.get("type") == "notification":
                    yield f"data: {json.dumps(pretty)}\n\n"
                # Any other chunk data
                else:
                    yield f"data: {json.dumps(pretty)}\n\n"
            

            if not final_output:
                yield f"data: {json.dumps({'type': 'final', 'data': {'answer': 'Query processing complete but no structured result was produced.'}})}\n\n"
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        
        # Signal the end of the stream
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(stream_generator(), media_type="text/event-stream")




# @app.post("/ask",response_model=ApiResponse)
# async def ask_database(request: QueryRequest):
#     """
#     Process a natural language question and return database results
#     """
#     try:
#         result = agent.ask_database(request.query)
        
#         if isinstance(result, Response):
#             # Extract table data if available in the messages
#             response_dict = result.model_dump()
            
#             # Make sure query_result is included in the response
#             if result.query_result is None and hasattr(result, 'messages'):
#                 # Try to extract table data from SQL runner agent's messages
#                 for msg in result.messages:
#                     if getattr(msg, 'name', '') == 'sql_runner_agent' and '```' in getattr(msg, 'content', ''):
#                         import re
#                         table_match = re.search(r'```(?:markdown)?\n(.*?)\n```', msg.content, re.DOTALL)
#                         if table_match:
#                             response_dict['query_result'] = table_match.group(1)
#                             break
            
#             return response_dict
            
#         # If we got a dictionary with structured_response
#         if isinstance(result, dict):
#             if "structured_response" in result:
#                 response_dict = result["structured_response"].model_dump()
                
#                 # Check for missing query_result
#                 if "query_result" not in response_dict or response_dict["query_result"] is None:
#                     # Try to extract from messages if available
#                     if "messages" in result:
#                         for msg in result["messages"]:
#                             if getattr(msg, 'name', '') == 'sql_runner_agent' and '```' in getattr(msg, 'content', ''):
#                                 import re
#                                 table_match = re.search(r'```(?:markdown)?\n(.*?)\n```', msg.content, re.DOTALL)
#                                 if table_match:
#                                     response_dict['query_result'] = table_match.group(1)
#                                     break
                
#                 return response_dict
#             elif "clarifying_question" in result:
#                 return ApiResponse(answer=result["clarifying_question"])
        
#         # If we just got messages or other content
#         return ApiResponse(answer=str(result))
        
        
        # Check if we got a Response object directly
        # if isinstance(result, Response):
        #     # Use model_dump() instead of dict() for Pydantic v2
        #     return result.model_dump()
            
        # # If we got a dictionary with structured_response
        # if isinstance(result, dict):
        #     if "structured_response" in result:
        #         return result["structured_response"].model_dump()
        #     elif "clarifying_question" in result:
        #         return ApiResponse(answer=result["clarifying_question"])
        
        # # If we just got messages or other content
        # return ApiResponse(answer=str(result))
    
    # except Exception as e:
    #     import traceback
    #     traceback.print_exc()
    #     raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Simple endpoint to check if API is running"""
    return {"status": "healthy"}


if __name__ == "__main__":
    print("Checking Azure Search index...")
    # initialize_search_index("src/tools/updated_examples.csv")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)