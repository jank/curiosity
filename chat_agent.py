from langchain_openai import ChatOpenAI
#from langchain_community.chat_models import ChatOllama
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

load_dotenv()
agents = {}
checkpointer = SqliteSaver.from_conn_string("data/curiosity.db")

def get_checkpoint(thread_id:str):
    config = {"configurable": {"thread_id": thread_id}}
    return checkpointer.get(config)

def get_agent(model_id:str):
    global agents
    if not model_id in agents:
        search = TavilySearchResults(max_results=3)
        tools = [search]
        global checkpointer
        cp = SqliteSaver.from_conn_string("data/curiosity.db")
        if model_id == "gpt-4o-mini":
            model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        elif model_id == "llama3.1":
            model = ChatOpenAI(model="llama3.1", base_url="http://localhost:11434/v1", temperature=0)
        else:
            raise Exception(f"Model not supported: {model_id}")
        agent = create_react_agent(model, tools, checkpointer=cp)
        agents[model_id] = agent
    return agents[model_id]