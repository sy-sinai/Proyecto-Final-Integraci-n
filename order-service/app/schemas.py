from pydantic import BaseModel
from datetime import datetime

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
    created_at: datetime

    class Config:
        orm_mode = True
