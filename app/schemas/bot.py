from pydantic import BaseModel, Field


class BotTradeRequest(BaseModel):
    pair: str = Field(min_length=3, max_length=50)
    amount: float = Field(gt=0, le=1_000_000)


class BotTradeResponse(BaseModel):
    pair: str
    side: str
    amount: float
    win: bool
    delta: float
    balance: float
