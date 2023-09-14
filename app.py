from fastapi import FastAPI
from bot import njbot
import uvicorn
from dto.message_request import MessageRequest

app = FastAPI()
chatbot = njbot.NJBot()


# Chatbot Endpoint
@app.post("/chatbot")
async def read_item(mr: MessageRequest):
    response = await chatbot.response(mr)
    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
