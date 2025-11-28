import sqlite3
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

load_dotenv()
agents = {}
checkpointer_conn = sqlite3.connect("data/curiosity.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=checkpointer_conn)


def get_checkpoint(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    return checkpointer.get(config)


def get_agent(model_id: str):
    global agents
    if not model_id in agents:
        search = TavilySearchResults(max_results=5, include_images=True)
        tools = [search]
        if model_id == "gpt-5-mini":
            model = ChatOpenAI(model=model_id, temperature=0)
        elif model_id == "llama3.1":
            model = ChatOpenAI(
                model=model_id, base_url="http://localhost:11434/v1", temperature=0
            )
        elif model_id == "llama-3.1-70b-versatile":
            model = ChatGroq(model=model_id, temperature=0)
        elif model_id == "llama3-groq-70b-8192-tool-use-preview":
            model = ChatGroq(model=model_id, temperature=0)
        elif model_id == "llama3-groq-8b-8192-tool-use-preview":
            model = ChatGroq(model=model_id, temperature=0)
        else:
            raise Exception(f"Model not supported: {model_id}")
        agent = create_react_agent(model, tools, checkpointer=checkpointer)
        agents[model_id] = agent
    return agents[model_id]
