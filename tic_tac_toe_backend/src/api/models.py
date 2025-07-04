from pydantic import BaseModel, Field
from typing import List, Optional

# PUBLIC_INTERFACE
class PlayerRegisterRequest(BaseModel):
    """Request model for registering or logging in a player."""
    username: str = Field(..., description="Desired username, must be unique.")

# PUBLIC_INTERFACE
class PlayerResponse(BaseModel):
    """Response model for player info."""
    username: str
    wins: int
    losses: int
    games_played: int

# PUBLIC_INTERFACE
class GameCreateRequest(BaseModel):
    """Request model for starting a new game."""
    username: str = Field(..., description="Username of creator/player X.")

# PUBLIC_INTERFACE
class GameJoinRequest(BaseModel):
    """Request model for joining a game as player O."""
    username: str = Field(..., description="Username joining as player O.")

# PUBLIC_INTERFACE
class GameCreatedResponse(BaseModel):
    """Response model once a game is created/joined."""
    game_id: str
    player_x: str
    player_o: Optional[str] = None
    status: str

# PUBLIC_INTERFACE
class GameStateResponse(BaseModel):
    """Response model for the current state of a game."""
    game_id: str
    player_x: str
    player_o: Optional[str]
    board: List[List[Optional[str]]]  # 3x3 board of "X", "O", or None
    next_turn: Optional[str]
    winner: Optional[str]  # username of winner, or None
    status: str  # 'waiting', 'in_progress', 'completed'

# PUBLIC_INTERFACE
class MoveRequest(BaseModel):
    """Request model to play a move on the board."""
    username: str
    row: int = Field(..., ge=0, le=2, description="Row (0-2)")
    col: int = Field(..., ge=0, le=2, description="Column (0-2)")

# PUBLIC_INTERFACE
class MoveResponse(BaseModel):
    """Response model after a move is played."""
    game_id: str
    board: List[List[Optional[str]]]
    next_turn: Optional[str]
    winner: Optional[str]
    status: str  # 'waiting', 'in_progress', 'completed'

# PUBLIC_INTERFACE
class ScoreEntry(BaseModel):
    """Leaderboard entry."""
    username: str
    wins: int

# PUBLIC_INTERFACE
class LeaderboardResponse(BaseModel):
    """Leaderboard response structure."""
    leaderboard: List[ScoreEntry]
