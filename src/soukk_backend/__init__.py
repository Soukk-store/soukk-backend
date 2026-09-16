import os
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Soukk Backend API")

@app.get("/")
def read_root():
    return {"status": "online"}

def main():
    port = int(os.getenv("PORT", "8000")) 
    workers = int(os.getenv("WEB_WORKERS", "1"))
    is_dev = os.getenv("ENV", "development").lower() == "development"
    
    uvicorn.run("soukk_backend:app", host="0.0.0.0", port=port, workers=workers,reload=is_dev if workers == 1 else False)

if __name__ == "__main__":
    main()
