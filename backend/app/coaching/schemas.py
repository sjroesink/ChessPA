from pydantic import BaseModel


class CoachingInsightData(BaseModel):
    type: str  # weakness, pattern, strength
    title: str
    description: str
    severity: str  # high, medium, low
    related_game_indices: list[int]  # indices into games list sent in prompt


class CoachingResponse(BaseModel):
    insights: list[CoachingInsightData]
