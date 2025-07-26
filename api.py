import json
import logging
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, ActivityTypes

from src.agents.LangBotAgent import LangBotAgent, Response

from config.config import AZURE_BOT_APP_CONFIG

APP_ID = AZURE_BOT_APP_CONFIG["azure_bot_app_id"]
APP_PASSWORD = AZURE_BOT_APP_CONFIG["azure_app_bot_password"]

adapter_settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
adapter = BotFrameworkAdapter(adapter_settings)
processed_activities = set()

class InputPayload(BaseModel):
    question: str = Field(..., description="Question to be asked")

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

@app.post("/askbot",response_model=ApiResponse)
async def ask_database(request: QueryRequest):
    """
    Process a natural language question and return database results
    """
    try:
        result = agent.ask_database(request.query)
        print(f"Result from agent: {result}")
        
        # If we got a Response object
        if isinstance(result, Response):
            # Extract table data if available in the messages
            response_dict = result.model_dump()            
            return response_dict        
        # If we got a dictionary with structured_response
        elif "structured_response" in result:
            logging.info("Structured response received from agent.")
            response_dict = result["structured_response"].model_dump()
            return response_dict
        else:
            logging.info("Received non-structured response from agent.")
            # If we just got messages or other content
            return ApiResponse(answer=str(result))
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/qa_teams")
async def qna_teams(input_payload: Dict, request: Request) -> Any:
    try:
        str(vars(Activity()))
        activity = Activity().deserialize(input_payload)
        auth_header = request.headers.get("Authorization", "")

        # Add idempotency check
        activity_id = activity.id
        if activity_id in processed_activities:
            logging.info(
                f"Skipping already processed activity ID: {activity_id}")
            return {"message": "Activity already processed"}

        processed_activities.add(activity_id)
        # Limit the size of the set to avoid memory issues
        if len(processed_activities) > 1000:
            processed_activities.pop()

        async def process_activity_async(turn_context: TurnContext):
            user_message = turn_context.activity.text
            
            input_teams = {
                "question": user_message
            }

            typing_activity = Activity(
                type=ActivityTypes.typing,
                relates_to=turn_context.activity.relates_to
            )
            await turn_context.send_activity(typing_activity)

            output = await ask_database(InputPayload(**input_teams))

            response = output["answer"]
            final_answer = response

            await turn_context.send_activity(final_answer)
    
        await adapter.process_activity(activity, auth_header, process_activity_async)
        logging.info("Sending Response to bot.")
    except Exception as e:
        logging.error(f"Error processing activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Response generated"}

@app.get("/health")
async def health_check():
    """Simple endpoint to check if API is running"""
    return {"status": "healthy"}