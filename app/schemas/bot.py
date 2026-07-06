from pydantic import BaseModel, Field


class BotTradeRequest(BaseModel):
    pair: str = Field(min_length=3, max_length=50)
    amount: float = Field(gt=0, le=1_000_000)
    phase: str = Field(default="start")


class BotTradeResponse(BaseModel):
    pair: str
    side: str
    amount: float
    win: bool
    delta: float
    balance: float
    message: str | None = None
