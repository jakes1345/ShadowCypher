from pathlib import Path

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

@app.get("/api/latest")
def get_latest_release():
    """Return latest release info (replaces GitHub releases API)."""
    try:
        version_file = Path(__file__).parent.parent / "VERSION"
        version = version_file.read_text().strip() if version_file.exists() else "0.0.0"
    except Exception:
        version = "0.0.0"

    return {
        "tag_name": f"v{version}",
        "version": version,
        "html_url": "https://shadowcypher.site/download",
        "body": "Latest ShadowCypher release. Download from shadowcypher.site",
        "assets": [
            {
                "name": "shadowcypher-linux.tar.gz",
                "download_url": f"https://releases.shadowcypher.site/v{version}/shadowcypher-linux.tar.gz"
            },
            {
                "name": "shadowcypher-guardian.apk",
                "download_url": f"https://releases.shadowcypher.site/v{version}/shadowcypher-guardian.apk"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec B104
