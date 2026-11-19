"""Read size-bounded transport bodies without echoing untrusted input."""
from fastapi import HTTPException, Request


async def bounded_body(request: Request, limit: int) -> bytearray:
    encoding = request.headers.get("content-encoding", "identity").strip().lower()
    if encoding != "identity":
        raise HTTPException(status_code=415, detail="Send an uncompressed JSON request body.")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > limit:
            raise HTTPException(status_code=413, detail="The JSON request body exceeds the allowed size.")
        body.extend(chunk)
    return body
