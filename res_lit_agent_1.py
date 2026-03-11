import anthropic
import requests
import xml.etree.ElementTree as ET
import json

client = anthropic.Anthropic()

# --- Tool definitions ---

tools = [
    {
        "name": "search_pubmed",
        "description": "Search PubMed for biomedical literature. Returns a list of PMIDs matching the query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query, e.g. 'juvenile idiopathic arthritis disease activity biomarkers'"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 5)",
                    "default": 10
                },
                "years": {
                    "type": "integer",
                    "description": "How many years back to search (default 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "fetch_abstracts",
        "description": "Fetch titles and abstracts from PubMed given a list of PMIDs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pmids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of PubMed IDs to fetch"
                }
            },
            "required": ["pmids"]
        }
    }
]

# --- Tool implementations ---

# def search_pubmed(query: str, max_results: int = 10, years: int = 5) -> list[str]:
#     from datetime import datetime
#     current_year = datetime.now().year
#     start_year = current_year - years
#     date_filter = f"{start_year}[PDAT]:{current_year}[PDAT]"
#     url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
#     params = {
#         "db": "pubmed",
#         "term": f"{query} AND {date_filter}",
#         "retmax": max_results,
#         "retmode": "json"
#     }
#     response = requests.get(url, params=params)
#     data = response.json()
#     return data["esearchresult"]["idlist"]

def search_pubmed(query: str, max_results: int = 10, years: int = 5) -> list[str]:
    from datetime import datetime
    current_year = datetime.now().year
    start_year = current_year - years
    date_filter = f"{start_year}[PDAT]:{current_year}[PDAT]"
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": f"{query} AND {date_filter}",
        "retmax": max_results,
        "retmode": "json"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["esearchresult"]["idlist"]
    except Exception as e:
        print(f"   └─ PubMed search error: {e}")
        return []

def fetch_abstracts(pmids: list[str]) -> list[dict]:
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml"
    }
    response = requests.get(url, params=params)
    root = ET.fromstring(response.content)

    articles = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID") or "unknown"
        title = article.findtext(".//ArticleTitle") or "No title"
        abstract = article.findtext(".//AbstractText") or "No abstract available"
        year = article.findtext(".//PubDate/Year") or "unknown year"
        authors = article.findall(".//Author")
        first_author = ""
        if authors:
            last = authors[0].findtext("LastName") or ""
            first = authors[0].findtext("ForeName") or ""
            first_author = f"{last} {first}".strip()

        articles.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "year": year,
            "first_author": first_author
        })
    return articles

def run_tool(name: str, inputs: dict):
    if name == "search_pubmed":
        return search_pubmed(**inputs)
    elif name == "fetch_abstracts":
        return fetch_abstracts(**inputs)
    else:
        return {"error": f"Unknown tool: {name}"}

# --- Agent loop ---

def run_agent(question: str):
    print(f"\nQuestion: {question}\n")

    messages = [{"role": "user", "content": question}]

    system = """You are a biomedical research assistant. When given a research question:
1. Search PubMed for relevant literature using search_pubmed
2. Fetch abstracts for the top results using fetch_abstracts
3. Synthesize the findings into a clear, concise answer with citations (PMID)

Always ground your answer in the retrieved literature."""

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system,
            tools=tools,
            messages=messages
        )

        # Append assistant response to history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print("\n" + "="*60)
                    print("📚 RESEARCH SYNTHESIS")
                    print("="*60 + "\n")
                    print(block.text)
                    print("\n" + "="*60)
                    # Save to file
                    # filename = question[:50].strip().replace(" ", "_").replace("/", "-") + ".txt"
                    # with open(filename, "w") as f:
                    #     f.write(f"Question: {question}\n\n")
                    #     f.write(block.text)
                    # print(f"\n[Saved to {filename}]")
            break

        elif response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "search_pubmed":
                        print(f"\n🔍 Searching PubMed for: '{block.input.get('query')}'")
                        print(f"   └─ filters: last {block.input.get('years', 5)} years, top {block.input.get('max_results', 10)} results")
                    elif block.name == "fetch_abstracts":
                        print(f"\n📄 Fetching abstracts for {len(block.input.get('pmids', []))} papers...")
                        print(f"   └─ PMIDs: {', '.join(block.input.get('pmids', []))}")

                    result = run_tool(block.name, block.input)

                    if block.name == "search_pubmed":
                        print(f"   └─ Found {len(result) if result else 0} papers")
                    elif block.name == "fetch_abstracts":
                        print(f"   └─ Abstracts retrieved successfully")

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            print(f"Unexpected stop reason: {response.stop_reason}")
            break

# --- Run it ---

if __name__ == "__main__":
    question = input("What do you want to research today? ")
    run_agent(question)