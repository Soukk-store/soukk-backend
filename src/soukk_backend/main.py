from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from soukk_backend.core.rateLimit import limiter
from soukk_backend.domains.auth.authController import router as auth_router
from soukk_backend.domains.users.userController import router as users_router
from soukk_backend.settings.appSettings import settings

app = FastAPI(title="Soukk Backend API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    # Lets the browser send and store the refresh token cookie.
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,  
)

app.include_router(auth_router)
app.include_router(users_router)

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
