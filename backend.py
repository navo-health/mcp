from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from multi_tool_agent.agent import build_agent
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = build_agent()

@app.get("/")
def root():
    return {"status": "Skills Gateway running"}


app = FastAPI()
agent = build_agent()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    # Handle async generator from agent.run_async
    async for result in agent.run_async(request.message):
        reply = str(result)
        break
    return {"response": reply}


