# Clinical and Biomedical Literature Research Agent

An AI-powered research agent that searches PubMed in real time, retrieves recent abstracts, and synthesizes findings into structured answers with citations.

## What it does
- Takes a biomedical research question as input
- Searches PubMed for relevant literature published in the last 5 years
- Retrieves and reads up to 10 abstracts autonomously
- Returns a synthesized, citation-grounded answer organized by theme

## How it works
The agent uses a tool-calling architecture where Claude (Anthropic) acts as the reasoning engine. It decides what to search, which papers to retrieve, and how to synthesize the findings — all autonomously in a multi-step loop.

## Stack
- **AI:** Claude Sonnet via Anthropic API
- **Literature source:** PubMed via NCBI E-utilities API
- **Backend:** FastAPI + Uvicorn
- **Deployment:** Render
- **Frontend:** HTML/CSS/JavaScript

## Live demo
[Try it here](https://research-lit-agent.onrender.com)

## Author
Jose Cobeña-Reyes, Ph.D. — [jcobenareyes.com](https://jcobenareyes.com)
