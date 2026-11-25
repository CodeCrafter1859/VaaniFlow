from starlette.responses import JSONResponse


class BodyLimitMiddleware:
    """Bound raw bodies before Starlette parses multipart or JSON, including chunked uploads."""

    def __init__(self, app, max_bytes):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = self.max_bytes if scope.get("path", "").endswith("/audio") else 512000
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = limit + 1
        if length > limit:
            await self.reject(scope, receive, send)
            return
        # Bounded pre-read ensures an oversize body cannot be swallowed by the multipart parser.
        chunks = []
        size = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > limit:
                await self.reject(scope, receive, send)
                return
            chunks.append(message)
            if not message.get("more_body", False):
                break
        iterator = iter(chunks)

        async def replay():
            try:
                return next(iterator)
            except StopIteration:
                return await receive()

        await self.app(scope, replay, send)

    async def reject(self, scope, receive, send):
        response = JSONResponse(
            {"error": {"code": "413", "message": "Request body too large"}}, status_code=413
        )
        await response(scope, receive, send)
