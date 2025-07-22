import os, logging
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import SecretStr

# Configure logging
logger = logging.getLogger(__name__)

load_dotenv()

os.environ["OPENAI_API_VERSION"] = "2024-12-01-preview"

def get_llm(model_name, provider="azure", **kwargs):
    """
    Get an instance of AzureChatOpenAI with the specified model name.
    
    Args:
        model_name (str): The name of the model to use.
        
    Returns:
        AzureChatOpenAI: An instance of AzureChatOpenAI configured with the specified model.
    """

    if provider == "openai":
        logging.info(f"Using OpenAI model: {model_name}")
        llm = ChatOpenAI(
            model = "gpt-4o-mini",
            api_key = SecretStr(os.getenv("OPENAI_API_KEY") or ""),
        )
        print("Using OpenAI model")
    elif provider == "gemini":
        logging.info(f"Using Google Gemini model: {model_name}")
        llm = ChatGoogleGenerativeAI(
            model='gemini-2.0-flash',
            api_key=os.getenv("GOOGLE_API_KEY"),
            **kwargs
        )
    elif provider == "groq":
        logging.info(f"Using Groq model: {model_name}")
        llm = ChatGroq(
            model=model_name,
            api_key=SecretStr(os.getenv("GROQ_API_KEY") or ""),
            **kwargs
        )
    elif provider == "azure":
        logging.info(f"Using Azure model: {model_name}")
        llm = AzureChatOpenAI(
            model=model_name,
            **kwargs
        )

    return llm