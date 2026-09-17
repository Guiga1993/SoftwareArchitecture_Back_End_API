"""Define the shared error response contract used by backend routes.

Using one schema keeps OpenAPI documentation and frontend error parsing aligned
for not-found, conflict, business-rule, and unexpected-operation failures.
"""

from pydantic import BaseModel


class ErrorSchema(BaseModel):
    """Expose one human-readable error message across API operations.

    Route handlers may use different HTTP status codes, but they return this
    stable body shape whenever a simple application error is reported.
    """

    message: str