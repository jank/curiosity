from fasthtml.common import *
from starlette.responses import RedirectResponse
from starlette.websockets import WebSocketState
from chat_agent import get_agent, get_checkpoint
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from openai import BadRequestError
from dataclasses import dataclass
from datetime import datetime
import textwrap
import shortuuid
import asyncio


# Site Map
# / entry page, redirects to /{uuid} with a fresh uuid
# /{uuid} shows the chat history of chat {uuid}, the uuid is used as thread_id for langgraph
#
# datamodel
# (user) 1-n> (chats) 0-n> (cards / stored in LangGraph db)

# model that will be used for generation of next answer
selected_model = "gpt-4o-mini"
# list of supported models the use can choose from
models = {
    # OpenAI
    "gpt-4o-mini": "GPT-4o-mini (OpenAI)",
    # Local Ollama
    "llama3.1": "Llama 3.1 8b (Ollama)",
    # Groq
    "llama-3.1-70b-versatile": "Llama 3.1 70b (Groq)",
    "llama3-groq-8b-8192-tool-use-preview": "Llama 3 8b tool use (Groq)",
    "llama3-groq-70b-8192-tool-use-preview": "Llama 3 70b tool use (Groq)",
}

# persistent storage of chat sessions
db = database("data/curiosity.db")
chats = db.t.chats
if chats not in db.t:
    chats.create(id=str, title=str, updated=datetime, pk="id")
ChatDTO = chats.dataclass()


# Patch ChatDTO class with ft renderer and ID initialization
@patch
def __ft__(self: ChatDTO):  # type: ignore
    return Li(
        A(
            textwrap.shorten(self.title, width=60, placeholder="..."),
            id=self.id,
            href=f"/chat/{self.id}",
        ),
        dir="ltr",
    )


# FIXME: this patch does not work, requires fixing
@patch
def __post_init__(self: ChatDTO):  # type: ignore
    self.id = shortuuid.uuid()


# default chat for new chats
new_chatDTO = ChatDTO()
new_chatDTO.id = shortuuid.uuid()


@dataclass
class ChatCard:
    question: str
    content: str
    model_id: str = None
    busy: bool = False
    sources: List = None
    images: List = None
    id: str = ""

    def __post_init__(self):
        self.id = shortuuid.uuid()

    def __ft__(self):
        return Card(
            (
                Progress()
                if self.busy
                else Div(
                    self.content,
                    cls="marked",
                )
            ),
            (
                Grid(*[A(Img(src=image), href=image) for image in self.images])
                if self.images and len(self.images) > 0
                else None
            ),
            id=self.id,
            header=Div(
                Strong(self.question), Small(self.model_id, cls="pico-color-grey-200")
            ),
            footer=(
                None
                if self.sources == None
                else Grid(
                    *[
                        Div(A(search_result["title"], href=search_result["url"]))
                        for search_result in self.sources
                    ]
                )
            ),
        )


# FastHTML includes the "HTMX" and "Surreal" libraries in headers, unless you pass `default_hdrs=False`.
app, rt = fast_app(
    live=True,  # type: ignore
    hdrs=(
        picolink,
        Link(
            rel="stylesheet",
            href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.colors.min.css",
            type="text/css",
        ),
        Meta(name="color-scheme", content="light dark"),
        MarkdownJS(),
    ),
    ws_hdr=True,  # web socket headers
)


def navigation():
    navigation = Nav(
        Ul(Li(Hgroup(H3("Be Curious!"), P("There are no stupid questions.")))),
        Ul(
            Li(
                Button(
                    "New question",
                    cls="secondary",
                    onclick=f"window.location.href='/chat/{new_chatDTO.id}'",
                )
            ),
            Li(model_selector()),
            Li(question_list()),
            Li(
                Details(
                    Summary("Theme", role="button", cls="secondary"),
                    Ul(
                        Li(
                            A(
                                "Auto",
                                href="#theme-dropdown",
                                data_theme_switcher="auto",
                            )
                        ),
                        Li(
                            A(
                                "Light",
                                href="#theme-dropdown",
                                data_theme_switcher="light",
                            )
                        ),
                        Li(
                            A(
                                "Dark",
                                href="#theme-dropdown",
                                data_theme_switcher="dark",
                            )
                        ),
                    ),
                    id="theme-dropdown",
                    cls="dropdown",
                )
            ),
        ),
    )
    return navigation


def question(chat_id: str):
    question = Div(
        Search(
            Group(
                Input(
                    id="new-question",
                    name="question",
                    autofocus=True,
                    placeholder="Ask your question here...",
                    autocomplete="off",
                ),
                Button("Answer", id="answer-btn", cls="hidden-default"),
            ),
            hx_post=f"/chat/{chat_id}",
            target_id="answer-list",
            hx_swap="afterbegin",
            id="search-group",
        )
    )
    return question


def question_list():
    return Details(
        Summary("Your last 25 questions"),
        Ul(*chats(order_by="updated DESC", limit=25), dir="rtl"),
        id="question-list",
        cls="dropdown",
        hx_swap_oob="true",
    )


def answer_list(chat_id: str):
    # restore message histroy for current thread
    checkpoint = get_checkpoint(chat_id)
    if checkpoint != None:
        top = None
        content = None
        model_id = None
        sources = None
        images = None
        old_messages = []
        for msg in checkpoint["channel_values"]["messages"]:
            if isinstance(msg, HumanMessage):
                if top != None and content != None:
                    old_messages.append(
                        ChatCard(
                            question=top,
                            content=content,
                            model_id=model_id,
                            sources=sources,
                            images=images,
                        )
                    )
                    top, content, model_id, sources, images = (
                        None,
                        None,
                        None,
                        None,
                        None,
                    )
                top = msg.content
            elif isinstance(msg, AIMessage):
                if "tool_calls" in msg.additional_kwargs:
                    # this is an AIMessage with tool calls. skip
                    continue
                else:
                    content = msg.content
                    model_id = msg.response_metadata["model_name"]
            elif isinstance(msg, ToolMessage) and "results" in msg.artifact:
                sources = msg.artifact["results"]
                images = msg.artifact["images"]
        if top != None and content != None:
            old_messages.append(
                ChatCard(
                    question=top,
                    content=content,
                    model_id=model_id,
                    sources=sources,
                    images=images,
                )
            )
        old_messages.reverse()
        answer_list = Div(*old_messages, id="answer-list")
    else:
        # no previous interaction, so show empty list
        answer_list = Div(id="answer-list")
    return answer_list


def model_selector():
    return Details(
        Summary("Model"),
        Ul(
            *[
                Li(
                    Label(
                        title,
                        Input(
                            name="model",
                            type="radio",
                            value=key,
                            **{"checked": key == selected_model},
                            hx_target="#model",
                            hx_swap="outerHTML",
                            hx_get="/model",
                        ),
                    ),
                    dir="ltr",
                )
                for key, title in models.items()
            ],
            dir="rtl",
        ),
        id="model",
        cls="dropdown",
    )


@rt("/model")
async def get(model: str):
    global selected_model
    if model in models.keys():
        selected_model = model
    return model_selector()


@rt("/")
async def get():
    return RedirectResponse(url=f"/chat/{new_chatDTO.id}")


@rt("/chat/{id}")
async def get(id: str):
    try:
        if id == new_chatDTO.id:
            chat = new_chatDTO
        else:
            chat = chats[id]
    except NotFoundError:
        # TODO need to rewrite URL if id != new_ChatDTO.id
        chat = new_chatDTO

    body = Body(
        Header(navigation()),
        Main(question(chat.id), cls="page-dropdown"),
        Footer(answer_list(chat.id)),
        Script(src="/static/minimal-theme-switcher.js"),
        cls="container",
        hx_ext="ws",
        ws_connect="/ws_connect",
    )
    return Title("Always be courious."), body


# WebSocket connection bookkeeping
ws_connections = {}


async def on_connect(send):
    ws_connections[send.args[0].client] = send
    print(f"WS    connect: {send.args[0].client}, total open: {len(ws_connections)}")


async def on_disconnect(send):
    global ws_connections
    ws_connections = {
        key: value
        for key, value in ws_connections.items()
        if send.args[0].client_state == WebSocketState.CONNECTED
    }
    print(f"WS disconnect: {send.args[0].client}, total open: {len(ws_connections)}")


@app.ws("/ws_connect", conn=on_connect, disconn=on_disconnect)
async def ws(msg: str, send):
    pass


async def update_chat(model: str, card: Card, chat: Any, cleared_inpput, busy_button):
    inputs = {"messages": [("user", card.question)]}
    config = {"configurable": {"thread_id": chat.id}}
    try:
        result = get_agent(model).invoke(inputs, config)
        print(f"{model} returned result.")
        if (len(result["messages"]) >= 2) and (
            isinstance(result["messages"][-2], ToolMessage)
        ):
            tmsg = result["messages"][-2]
            card.sources = tmsg.artifact["results"]
            card.images = tmsg.artifact["images"]
        card.content = result["messages"][-1].content
        chats.upsert(chat)
        success = True
    except BadRequestError as e:
        # e = "some error"
        print(f"Exception while calling LLM: {e}")
        card.content = (
            f"Sorry, due to some technical issue no response could be generated: \n{e}"
        )
        success = False

    card.model_id = model
    card.busy = False
    cleared_inpput.disabled = False
    busy_button.disabled = False
    for send in ws_connections.values():
        try:
            await send(card)
            await send(cleared_inpput)
            await send(busy_button)
            if success:
                await send(question_list())
        except:
            pass
    return success


@threaded
def generate_chat(model: str, card: Card, chat: Any, cleared_inpput, busy_button):
    chat.title = card.question if chat.title == None else chat.title
    chat.updated = datetime.now()
    success = asyncio.run(update_chat(model, card, chat, cleared_inpput, busy_button))
    if success:
        global new_chatDTO
        if chat is new_chatDTO:
            new_chatDTO = ChatDTO()
            new_chatDTO.id = shortuuid.uuid()


@rt("/chat/{id}")
async def post(question: str, id: str):
    try:
        if id == new_chatDTO.id:
            chat = new_chatDTO
        else:
            chat = chats[id]
    except NotFoundError:
        # TODO need to rewrite URL if id != new_ChatDTO.id
        chat = new_chatDTO

    card = ChatCard(question=question, content="", busy=True)
    cleared_inpput = Input(
        id="new-question",
        name="question",
        autofocus=True,
        placeholder="Ask your question here...",
        autocomplete="off",
        disabled=True,
        hx_swap_oob="true",
    )
    busy_button = Button(
        "Answer",
        id="answer-btn",
        cls="hidden-default",
        disabled=True,
        hx_swap_oob="true",
    )

    # call response generation in seperate Thread
    generate_chat(selected_model, card, chat, cleared_inpput, busy_button)

    return card, cleared_inpput, busy_button


def main():
    print("preparing html server")
    serve()


if __name__ == "__main__":
    main()
