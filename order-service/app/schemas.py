from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class OrderCreate(BaseModel):
    customer_name: str
    product: str
    quantity: int

class OrderResponse(BaseModel):
    id: int
    customer_name: str
    product: str
    quantity: int
    status: str
    correlation_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
