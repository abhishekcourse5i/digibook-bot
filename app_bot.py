from fastapi import APIRouter, HTTPException, Request
from langchain.pydantic_v1 import BaseModel, Field
from utils.get_async_answer import limited_ainvoke_with_backoff, limited_embed_with_retry
from langchain.prompts import ChatPromptTemplate
from prompts.answer_prompts import answer_prompt
from utils.get_llm import get_azure_llm
from utils.get_s3_url import get_url
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity, ActivityTypes
from utils.async_indexes import AsyncIndexes
from config.config import AZURE_BOT_APP_CONFIG
from config.db import database
from datetime import datetime
from functools import wraps
import asyncio
import time
import logging
from typing import Dict, Any
from utils.greet_check import greet_check, greet_reply
from utils.fetch_user_chat import fetch_last_record, check_question
from utils.reformat_question import reformat_question
from utils.azure_blob_services import AsyncBlobManager

router = APIRouter()

CONCURRENT_CALLS = 6
semaphore = asyncio.Semaphore(CONCURRENT_CALLS)

processed_activities = set()


def limit_concurrent_calls(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        async with semaphore:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    return wrapper


class InputPayload(BaseModel):
    question: str = Field(..., description="Question to be asked")
    username: str = Field(..., description="Username")


llm = get_azure_llm()
async_index_client = AsyncIndexes()
top_k = 3

NON_HR_ANSWER = "Could you please ask a question related to HR topics such as leaves, awards, employee travel, resignation, relocation, ethics, or CSR?"


@router.post("/ai_assistant/qna")
@limit_concurrent_calls
async def qna(input_payload: InputPayload):
    try:
        start_time = time.time()
        question = input_payload.question
        try:
            username = input_payload.username
        except:
            username = ""

        is_greet = greet_check(question)
        logging.info(f"IS GREET : {is_greet}")
        if is_greet == "yes":
            res = greet_reply(question, username)
            return {"question" : question,
                    "response": res,
                    "context_pdf": [],
                    "context_page_num": [],
                    "status": 200}

        if username:
            try:
                last_asked_question = await fetch_last_record(username=username)
                question = reformat_question(
                    prev_questions=last_asked_question, question=question)
            except Exception as e:
                logging.info(f"ERROR : {e}")
                logging.info("Question context - not updated")

        logging.info(f"TRYING TO GET CONTEXT")
        context = await limited_embed_with_retry(question, async_index_client, top_k)
        logging.info(f"GOT CONTEXT : {context}")

        context_str = ""
        context_pdf = []
        context_page_num = []
        link_limit = 3

        for data in context:
            context_str += ("DATA:\n" + str((data["chunk_data"]) +
                            "\nSUMMARY:\n" + str(data['chunk_summary'])) + "\n\n")
            if len(context_pdf) < link_limit:
                context_pdf.append(data["pdf_name"])
                context_page_num.append(data["page_number"])

        chain = ChatPromptTemplate.from_template(template=answer_prompt) | llm
        response = await limited_ainvoke_with_backoff(chain, question, context_str)

        # print(f"RESPONSE : {response}")

        end_time = time.time()

        logging.info(f"{end_time - start_time} secs")

        non_hr = False
        if NON_HR_ANSWER.strip().lower()[:50] in response.content.lower().strip():
            non_hr = True

        # Load on the HR Bot is too high. Please try again later.

        return {"question": question,
                "response": response.content,
                "context_pdf": context_pdf if non_hr is False else [],
                "context_page_num": context_page_num if non_hr is False else [],
                "status": 200}

    except Exception as e:
        return {"question": question,
                "response": f"Exception : {e}",
                "context_pdf": [],
                "context_page_num": [],
                "status": 429}

APP_ID = AZURE_BOT_APP_CONFIG["azure_bot_app_id"]
APP_PASSWORD = AZURE_BOT_APP_CONFIG["azure_app_bot_password"]

adapter_settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
adapter = BotFrameworkAdapter(adapter_settings)


@router.post("/ai_assistant/qa_teams")
@limit_concurrent_calls
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
            username = turn_context.activity.from_property.name
            input_teams = {"question": user_message,
                           "username": username}

            typing_activity = Activity(
                type=ActivityTypes.typing,
                relates_to=turn_context.activity.relates_to
            )
            await turn_context.send_activity(typing_activity)

            start_time = time.time()
            output = await qna(InputPayload(**input_teams))
            end_time = time.time()

            response = output["response"]
            question = output["question"]
            context_pdf = output.get("context_pdf", "")
            context_page_num = output.get("context_page_num", "")
            status = output.get("status", "")
            final_answer = ""

            if status == 200:
                final_answer = str(response)

                blob_manager = AsyncBlobManager()

                if len(context_pdf) > 0:
                    final_answer += f"<br><br><b>Sources:</b><br>"
                for i in range(len(context_pdf)):
                    pdf_name_ = str(context_pdf[i]).strip() + ".pdf"
                    # context_url = get_url(file_name=pdf_name_)
                    html_url = await blob_manager.get_shareable_url(file_name=pdf_name_, page_num=context_page_num[i])
                    # html_url = f"{context_url}#page={context_page_num[i]}"
                    final_answer += f"<a href='{html_url}'>{context_pdf[i]} - Page {context_page_num[i]}</a><br>"
            else:
                final_answer = response

            await turn_context.send_activity(final_answer)

            # TODO make this async
            username = turn_context.activity.from_property.name
            user_message = user_message
            time_to_generate_response = end_time - start_time
            log_query = '''
            INSERT INTO qna_logs_test (username, user_message, final_answer, datetime, time_to_generate_response)
            VALUES (:username, :user_message, :final_answer, :datetime, :time_to_generate_response)
            '''
            await database.execute(log_query, values={
                "username": username,
                "user_message": question,
                "final_answer": final_answer,
                "datetime": datetime.now(),
                "time_to_generate_response": time_to_generate_response
            })

        await adapter.process_activity(activity, auth_header, process_activity_async)
        logging.info("Sending Response to bot.")
    except Exception as e:
        logging.error(f"Error processing activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    return {"message": "Response generated"}
