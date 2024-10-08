from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_groq import ChatGroq
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

load_dotenv()
agents = {}
checkpointer = None


def get_checkpoint(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    global checkpointer
    if checkpointer is None:
        checkpointer = SqliteSaver.from_conn_string("data/curiosity.db")
    return checkpointer.get(config)


def get_agent(model_id: str):
    global agents
    if not model_id in agents:
        search = TavilySearchResults(max_results=5, include_images=True)
        tools = [search]
        global checkpointer
        cp = SqliteSaver.from_conn_string("data/curiosity.db")
        if model_id == "gpt-4o-mini":
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
        agent = create_react_agent(model, tools, checkpointer=cp)
        agents[model_id] = agent
    return agents[model_id]
