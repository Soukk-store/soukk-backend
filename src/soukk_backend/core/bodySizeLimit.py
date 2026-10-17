from fastapi import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BodySizeLimitMiddleware:
    """Refuse request bodies over a limit, per route, before they are stored.

    Starlette writes uploaded files to a temporary file with no size limit, so a
    check inside the endpoint only runs once the whole upload has been received.
    This stops it at the door instead: a declared Content-Length over the limit
    is refused before anything is read, and a body without one (chunked) is cut
    off as soon as it passes the limit.

    A plain ASGI middleware rather than BaseHTTPMiddleware, which can't watch the
    body while the endpoint reads it.
    """

    def __init__(self, app: ASGIApp, limits: dict[tuple[str, str], int], detail: str) -> None:
        # (method, path) -> largest body accepted, in bytes.
        self.app = app
        self.limits = limits
        self.detail = detail

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        limit = None
        if scope["type"] == "http":
            limit = self.limits.get((scope["method"], scope["path"]))
        if limit is None:
            await self.app(scope, receive, send)
            return

        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None:
            try:
                too_large = int(declared) > limit
            except ValueError:
                await JSONResponse({"detail": "Invalid Content-Length"}, 400)(scope, receive, send)
                return
            if too_large:
                await JSONResponse({"detail": self.detail}, 413)(scope, receive, send)
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # An HTTPException, because FastAPI passes those through while
                    # parsing the body but turns any other error into a 400.
                    raise HTTPException(status_code=413, detail=self.detail)
            return message

        await self.app(scope, limited_receive, send)
