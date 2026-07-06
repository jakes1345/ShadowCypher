from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shadowcypher.chat.routes import router as chat_router

app = FastAPI(title="ShadowCypher Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://shadowcypher.site", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
