from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

agent = None
checkpointer = None

def get_checkpoint(thread_id:str):
    config = {"configurable": {"thread_id": thread_id}}
    return checkpointer.get(config)

def create_agent():
    global agent
    if agent == None:
        load_dotenv()
        search = TavilySearchResults(max_results=3)
        tools = [search]
        global checkpointer
        checkpointer = SqliteSaver.from_conn_string("data/curiosity.db")
        model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        agent = create_react_agent(model, tools, checkpointer=checkpointer)
    return agent