from pydantic import BaseModel
from typing import List
from datetime import datetime


class DeptStatsResponse(BaseModel):
    dept: str
    year: int
    month: int
    approved: int
    waiting: int
    total: int


class DailyStats(BaseModel):
    day: int
    count: int
