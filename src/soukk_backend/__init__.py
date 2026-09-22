from fastapi import FastAPI
import uvicorn

from soukk_backend.settings import settings

app = FastAPI(title="Soukk Backend API")

@app.get("/health")
def health():
    return {"status": "ok"}

def main():
    uvicorn.run(
        "soukk_backend:app",
        host="0.0.0.0",
        port=settings.port,
        workers=settings.web_workers,
        reload=settings.is_dev if settings.web_workers == 1 else False,
    )

if __name__ == "__main__":
    main()
