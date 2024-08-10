# curiosity

> Dabbling with ReAct chatbots

I started this toy project to dabble with [LangGraph](https://langchain-ai.github.io/langgraph/) and [FastHTML](https://fastht.ml). My goal was to get some exposure to these tech stacks while trying to build a Perplexity-like user experience.

At the core is a simple ReAct Agent that uses [Tavily](https://tavily.com) search to augment the text generation. As in any good web project, most time was spend on making it look visually acceptable and sound from the interaction standpoint.

![Curiosity](https://github.com/user-attachments/assets/e85e68c7-8913-462e-876a-77cbd2b489ba)

## Using different LLMs

Three different LLMs are currently supported:
- gpt-4o-mini by OpenAI
- llama3-groq-8b-8192-tool-use-preview by Groq
- llama3.1:latest by Ollama (run your own)

So far, OpenAI's *gpt-4o-mini* has been most robust. It showed a decent tool calling performance and generated meaningful responses. I had some initial issues with Groq, but that seemed to have been an issue with the API key. It seems that you need to have some patience until it is fully activated. Generation speed is excellent with Groq. However, the 8b llama3 is substantially fallling behind the gpt-4o answers. Using the local llama3.1 was just for fun. Running this on my Mac mini M1 brought the machine to its limits. But it is great to see the flexibility in swapping backends.

## The Frontend

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
