from typing import Literal

from pydantic import BaseModel


Status = Literal["ok", "error"]


class ApiStatus(BaseModel):
    status: Status
    detail: str | None = None

