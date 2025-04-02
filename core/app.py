import os
import sys
import base64
import datetime
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Depends
from agents.claim_decomposer import claim_decomposer
from agents.research_agent import create_agent as create_research_agent
from agents.reasoning_agent import reasoning_agent

# Create FastAPI app
app = FastAPI()


def delete_messages(states: list[dict]):
    for state in states:
        del state['messages']


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/query")
async def query(request: Request):

    # Parse the request body
    req = await request.json()
    text = req.get('body')

    if not text:
        raise HTTPException(
            status_code=400, detail="Input {'body': str} is required.")

    # Try constructing research agent
    research_agent = create_research_agent(
        model="mistral-nemo",
        builtin_tools={
            'calculator': ['multiply', 'add'],
            'wikipedia': ['query']
        },
        user_tool_kwargs=[]
    )

    # Claims decomposer
    initial_state = {"text": text}
    result = claim_decomposer.invoke(initial_state)
    claims = result["claims"]

    research_results = [research_agent.invoke(
        {"claim": claim}) for claim in claims]
    delete_messages(research_results)

    # Drop the 'args' from the research results evidence, leaving only tool name and result content
    evidence_for_reasoning = [{'name': evidence['name'], 
                              'content': evidence['content']}
                              for evidence in research_results['evidence']]
    
    

    reasoning_results = [reasoning_agent.invoke(
        state) for state in research_results]
    delete_messages(reasoning_results)

    return reasoning_results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
