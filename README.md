# curiosity

> Dabbling with ReAct chatbots

I started this toy project to dabble with [LangGraph](https://langchain-ai.github.io/langgraph/) and [FastHTML](https://fastht.ml). My goal was to get some exposure to these tech stacks while trying to build a Perplexity-like user experience.

At the core is a simple ReAct Agent that uses [Tavily](https://tavily.com) search to augment the text generation. As in any good web project, most time was spend on making it look visually acceptable and sound from the interaction standpoint.

![curiostiy](https://github.com/user-attachments/assets/8584340d-0824-455f-b8db-2421489b3774)

I ended up using OpenAI GPT-4o-mini as it was straightforward to integrate via LangGraph and has decent tool calling capabilities. I also managed to use my locally Ollama hosted llama3.1:latest model. With the latest model updates from early August 2024 tool calling did work. Hosting it on my Mac mini M1 really took the Mac to its limits. I was also eager to try out Groq for even faster response times. However, I got strange 403 errors that I could not decypher and fix - might have been a temporary issue.

Building the web frontend with FastHTML was quite an experience. Given all the tech stacked into this framework it does feel fast at some time, but can also be a bit cumbersome to debug (e.g. issues with WebSockets closing for no reason). I also wanted to use WebSockets to stream token by token from the LLM to the frontend. But accessing the LLM tokens while keeping SQLite persistence for LangGraph was too deep of a rabbit hole for now.

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
