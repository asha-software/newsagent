from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request
from agents.claim_decomposer import claim_decomposer
from agents.research_agent import research_agent
from agents.reasoning_agent import reasoning_agent
from agents.verdict_agent import verdict_agent

app = FastAPI()


def delete_messages(states: list[dict]):
    for state in states:
        del state['messages']


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/query")
async def query(request: Request):
    req = await request.json()
    text = req.get('body')

    if not text:
        raise HTTPException(
            status_code=400, detail="Input {'body': str} is required.")

    # Run through newsagent
    initial_state = {"text": text}
    result = claim_decomposer.invoke(initial_state)
    claims = result["claims"]

    research_results = [research_agent.invoke(
        {"claim": claim}) for claim in claims]
    delete_messages(research_results)

    reasoning_results = [reasoning_agent.invoke(
        state) for state in research_results]
    delete_messages(reasoning_results)

    return reasoning_results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
