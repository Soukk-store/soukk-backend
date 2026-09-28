from fastapi import FastAPI
import uvicorn
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from soukk_backend.core.rateLimit import limiter
from soukk_backend.domains.auth.authController import router as auth_router
from soukk_backend.settings import settings

app = FastAPI(title="Soukk Backend API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(auth_router)

@app.get("/health")
def health():
    return {"status": "ok"}

def main():
    uvicorn.run(
        "soukk_backend.main:app",
        host="0.0.0.0",
        port=settings.port,
        workers=settings.web_workers,
        reload=settings.is_dev if settings.web_workers == 1 else False,
    )

if __name__ == "__main__":
    main()
