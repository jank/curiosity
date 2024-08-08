from fasthtml.common import *
from starlette.responses import RedirectResponse
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

db = database("data/curiosity.db")
chats = db.t.chats
if chats not in db.t:
    chats.create(id=str, title=str, updated=datetime, pk="id")
ChatDTO = chats.dataclass()


# Patch ChatDTO class with ft renderer and ID initialization
@patch
def __ft__(self: ChatDTO):  # type: ignore
    return A(
        textwrap.shorten(self.title, width=60, placeholder="..."),
        id=self.id,
        href=f"/chat/{self.id}",
    )


# FIXME: this patch does not work, requires fixing
@patch
def __post_init__(self: ChatDTO):  # type: ignore
    self.id = shortuuid.uuid()


new_chatDTO = ChatDTO()
new_chatDTO.id = shortuuid.uuid()


@dataclass
class ChatCard:
    question: str
    content: str
    busy: bool = False
    sources: List = None
    id: str = ""

    def __post_init__(self):
        self.id = shortuuid.uuid()

    def __ft__(self):
        return Card(
            Progress() if self.busy else P(self.content, cls="marked"),
            header=Strong(self.question),
            footer=(
                None
                if self.sources == None
                else Details(
                    Summary("Web links"),
                    Div(
                        *[
                            Div(A(search_result["title"], href=search_result["url"]))
                            for search_result in self.sources
                        ],
                        cls="grid",
                    ),
                )
            ),
            id=self.id,
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
        Style(""":root { --pico-font-size: 100%;}"""),
        Meta(name="color-scheme", content="light dark"),
        MarkdownJS(),
    ),
    ws_hdr=True,  # web socket headers
)


def question_list():
    return Details(
        Summary("Your last 25 questions"),
        Ul(Li(*chats(order_by="updated DESC", limit=25), dir="ltr"), dir="rtl"),
        id="question-list",
        cls="dropdown",
        hx_swap_oob="true",
    )


@rt("/")
def get():
    return RedirectResponse(f"/chat/{new_chatDTO.id}")


@rt("/chat/{id}")
async def get(id: str):
    try:
        if id == new_chatDTO.id:
            chat = new_chatDTO
        else:
            chat = chats[id]
    except:
        # TODO need to rewrite URL if id != new_ChatDTO.id
        chat = new_chatDTO
    navigation = Nav(
        Ul(Li(Hgroup(H3("Be Curious!"), P("There are no stupid questions.")))),
        Ul(
            Li(
                Button(
                    "New question", cls="secondary", onclick="window.location.href='/'"
                )
            ),
            Li(question_list()),
            Li(
                Details(
                    Summary("Theme", role="button", cls="secondary"),
                    Ul(
                        Li(A("Auto", href="#", data_theme_switcher="auto")),
                        Li(A("Light", href="#", data_theme_switcher="light")),
                        Li(A("Dark", href="#", data_theme_switcher="dark")),
                    ),
                    cls="dropdown",
                )
            ),
            # Li(A('Login', href='#'))
        ),
    )
    ask_question = Div(
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
            hx_post=f"/chat/{chat.id}",
            target_id="answer-list",
            hx_swap="afterbegin",
            id="search-group",
        ),
    )

    # restore message histroy for current thread
    checkpoint = get_checkpoint(id)
    if checkpoint != None:
        top = None
        content = None
        sources = None
        old_messages = []
        for msg in checkpoint["channel_values"]["messages"]:
            if isinstance(msg, HumanMessage):
                if top != None and content != None:
                    old_messages.insert(
                        1, ChatCard(question=top, content=content, sources=sources)
                    )
                    top, content, sources = None, None, None
                top = msg.content
            elif isinstance(msg, AIMessage):
                if "tool_calls" in msg.additional_kwargs:
                    # this is an AIMessage with tool calls. skip
                    continue
                else:
                    content = msg.content
            elif isinstance(msg, ToolMessage) and "results" in msg.artifact:
                sources = msg.artifact["results"]
        if top != None and content != None:
            old_messages.insert(
                1, ChatCard(question=top, content=content, sources=sources)
            )
        answer_list = Div(*old_messages, id="answer-list")
    else:
        answer_list = Div(id="answer-list")

    body = Body(
        Header(navigation),
        Main(ask_question),
        Footer(answer_list, hx_ext="ws", ws_connect="/ws_connect"),
        Script(src="/static/minimal-theme-switcher.js"),
        cls="container",
    )
    return Title("Always be courious."), body


# WebSocket connection bookkeeping
ws_connections = []


async def on_connect(send):
    print(f"WS    connect: {send.args[0].client}")
    ws_connections.append(send)


async def on_disconnect(send):
    print(f"WS disconnect: {send.args[0].client}")


@app.ws("/ws_connect", conn=on_connect, disconn=on_disconnect)
async def ws(msg: str, send):
    pass


async def update_chat(card: Card, chat: Any, cleared_inpput, busy_button):
    inputs = {"messages": [("user", card.question)]}
    config = {"configurable": {"thread_id": chat.id}}
    try:
        result = get_agent("gpt-4o-mini").invoke(inputs, config)
        # result = get_agent("llama3-groq-8b-8192-tool-use-preview").invoke(inputs, config)
        # result = get_agent("llama3.1").invoke(inputs, config)
        if (len(result["messages"]) >= 2) and (
            isinstance(result["messages"][-2], ToolMessage)
        ):
            tmsg = result["messages"][-2]
            card.sources = tmsg.artifact["results"]
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

    card.busy = False
    cleared_inpput.disabled = False
    busy_button.disabled = False
    for browser in ws_connections:
        try:
            await browser(card)
            await browser(cleared_inpput)
            await browser(busy_button)
            if success:
                await browser(question_list())
        except Exception as e:
            ws_connections.remove(browser)
    return success


@threaded
def generate_chat(card: Card, chat: Any, cleared_inpput, busy_button):
    chat.title = card.question if chat.title == None else chat.title
    chat.updated = datetime.now()
    success = asyncio.run(update_chat(card, chat, cleared_inpput, busy_button))
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
    except:
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
    generate_chat(card, chat, cleared_inpput, busy_button)
    return card, cleared_inpput, busy_button


def main():
    print("preparing html server")
    serve()


if __name__ == "__main__":
    main()
