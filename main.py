from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json

from res_lit_agent_1 import search_pubmed, fetch_abstracts, run_tool, tools

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class Query(BaseModel):
    question: str

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("index.html") as f:
        return f.read()

@app.post("/research")
async def research(query: Query):
    return StreamingResponse(
        run_agent_stream(query.question),
        media_type="text/event-stream"
    )

async def run_agent_stream(question: str):
    import anthropic
    client = anthropic.Anthropic()

    system = """You are a biomedical research assistant. When given a research question:
1. Search PubMed for relevant literature using search_pubmed
2. Fetch abstracts for the top results using fetch_abstracts
3. Synthesize the findings into a clear, concise answer with citations (PMID)

Always ground your answer in the retrieved literature."""

    messages = [{"role": "user", "content": question}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system,
            tools=tools,
            messages=messages
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    yield f"data: {json.dumps({'type': 'answer', 'content': block.text})}\n\n"
            break

        elif response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    # if block.name == "search_pubmed":
                    #     yield f"data: {json.dumps({'type': 'step', 'content': f'🔍 Searching PubMed for: {block.input.get(\"query\")}'})}\n\n"
                    # elif block.name == "fetch_abstracts":
                    #     yield f"data: {json.dumps({'type': 'step', 'content': f'📄 Fetching abstracts for {len(block.input.get(\"pmids\", []))} papers...'})}\n\n"

                    if block.name == "search_pubmed":
                        query_text = block.input.get('query')
                        step = f"🔍 Searching PubMed for: {query_text}"
                        yield f"data: {json.dumps({'type': 'step', 'content': step})}\n\n"
                    elif block.name == "fetch_abstracts":
                        num_papers = len(block.input.get('pmids', []))
                        step = f"📄 Fetching abstracts for {num_papers} papers..."
                        yield f"data: {json.dumps({'type': 'step', 'content': step})}\n\n"

                    
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })

            messages.append({"role": "user", "content": tool_results})