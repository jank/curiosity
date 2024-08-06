# curiosity
Dabbling with ReAct chatbots


## Setup
- Clone repository
- Make sure to have a recent Python3 interpreter (required by fasthtml)
- Setup venv and `pip install -r requirements.txt`
- create an `.env` file and set the following variables:
```
# OpenAI - https://platform.openai.com/playground/chat
OPENAI_API_KEY=<key>
# Groq - https://console.groq.com
GROQ_API_KEY=<key>
# Tavily Search - https://app.tavily.com
TAVILY_API_KEY=<key>
# LangSmith - https://smith.langchain.com
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY=<key>
LANGCHAIN_PROJECT="Curiosity"
```
- run `python curiosity.py`
