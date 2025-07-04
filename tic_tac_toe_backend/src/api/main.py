from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import uuid4

# --- In-memory storage ---
players: Dict[str, Dict[str, Any]] = {}  # username -> player info
games: Dict[str, Dict[str, Any]] = {}    # game_id -> game state
scores: List[Dict[str, Any]] = []        # List of scores (leaderboard)

# --- Constants ---
BOARD_SIZE = 3

tags_metadata = [
    {"name": "players", "description": "Player registration and login."},
    {"name": "game", "description": "Game lifecycle: create, join, play, and view game state."},
    {"name": "leaderboard", "description": "Score history and leaderboard."}
]

app = FastAPI(
    title="Tic Tac Toe Backend API",
    description="API for a web-based Tic Tac Toe game.",
    version="0.1.0",
    openapi_tags=tags_metadata
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas ---

class PlayerRegisterRequest(BaseModel):
    username: str = Field(..., description="Desired username, must be unique.")

class PlayerResponse(BaseModel):
    username: str
    wins: int
    losses: int
    games_played: int

class GameCreateRequest(BaseModel):
    username: str = Field(..., description="Username of creator/player 1.")

class GameJoinRequest(BaseModel):
    username: str = Field(..., description="Username joining as player 2.")

class GameCreatedResponse(BaseModel):
    game_id: str
    player_x: str
    player_o: Optional[str] = None
    status: str

class GameStateResponse(BaseModel):
    game_id: str
    player_x: str
    player_o: Optional[str]
    board: List[List[Optional[str]]]
    next_turn: Optional[str]
    winner: Optional[str]
    status: str  # waiting, in_progress, completed

class MoveRequest(BaseModel):
    username: str
    row: int = Field(..., ge=0, le=2)
    col: int = Field(..., ge=0, le=2)

class MoveResponse(BaseModel):
    game_id: str
    board: List[List[Optional[str]]]
    next_turn: Optional[str]
    winner: Optional[str]
    status: str  # waiting, in_progress, completed

class ScoreEntry(BaseModel):
    username: str
    wins: int

class LeaderboardResponse(BaseModel):
    leaderboard: List[ScoreEntry]

# --- Helper functions ---

def create_game_board():
    return [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

def check_winner(board):
    # Check rows, columns and diagonals
    lines = board + [list(t) for t in zip(*board)]  # rows & cols
    lines.append([board[i][i] for i in range(BOARD_SIZE)])  # diag
    lines.append([board[i][BOARD_SIZE - 1 - i] for i in range(BOARD_SIZE)])  # anti-diag

    for line in lines:
        if line[0] and all(cell == line[0] for cell in line):
            return line[0]
    # Check draw
    if all(cell is not None for row in board for cell in row):
        return "draw"
    return None

def mark_player_win_loss(winner: str, loser: str):
    if winner in players:
        players[winner]["wins"] += 1
    if loser in players:
        players[loser]["losses"] += 1
    if winner in players:
        players[winner]["games_played"] += 1
    if loser in players:
        players[loser]["games_played"] += 1

def get_leaderboard():
    return sorted(
        [
            {"username": uname, "wins": pdata["wins"]}
            for uname, pdata in players.items()
        ],
        key=lambda e: e["wins"],
        reverse=True,
    )

# --- API Endpoints ---

# PUBLIC_INTERFACE
@app.get("/", tags=["players"])
def health_check():
    """Health check for the API."""
    return {"message": "Healthy"}

# PLAYER REGISTRATION / LOGIN

# PUBLIC_INTERFACE
@app.post("/register", response_model=PlayerResponse, tags=["players"], summary="Register/Login player", description="Registers a new player if username not taken, or logs in an existing player. No password required for MVP.")
def register_player(request: PlayerRegisterRequest):
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty")
    if username not in players:
        players[username] = {"username": username, "wins": 0, "losses": 0, "games_played": 0}
    return PlayerResponse(**players[username])

# PUBLIC_INTERFACE
@app.get("/player/{username}", response_model=PlayerResponse, tags=["players"], summary="Get player info", description="Get information about a player by username.")
def get_player(username: str):
    if username not in players:
        raise HTTPException(status_code=404, detail="Player not found")
    return PlayerResponse(**players[username])

# GAME CREATION & JOINING

# PUBLIC_INTERFACE
@app.post("/game/start", response_model=GameCreatedResponse, tags=["game"], summary="Start a new game", description="Creates a new Tic Tac Toe game. The creator is set as player X.")
def start_game(request: GameCreateRequest):
    if request.username not in players:
        raise HTTPException(status_code=404, detail="Player must be registered")
    game_id = str(uuid4())
    games[game_id] = {
        "game_id": game_id,
        "player_x": request.username,
        "player_o": None,
        "board": create_game_board(),
        "next_turn": request.username,
        "winner": None,
        "status": "waiting"
    }
    return GameCreatedResponse(
        game_id=game_id,
        player_x=request.username,
        player_o=None,
        status="waiting"
    )

# PUBLIC_INTERFACE
@app.post("/game/{game_id}/join", response_model=GameCreatedResponse, tags=["game"], summary="Join game", description="Join an existing Tic Tac Toe game as player O.")
def join_game(game_id: str, request: GameJoinRequest):
    if request.username not in players:
        raise HTTPException(status_code=404, detail="Player must be registered")
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game["player_o"]:
        raise HTTPException(status_code=400, detail="Game already has two players")
    if game["player_x"] == request.username:
        raise HTTPException(status_code=400, detail="Player already in game")
    game["player_o"] = request.username
    game["status"] = "in_progress"
    return GameCreatedResponse(
        game_id=game_id,
        player_x=game["player_x"],
        player_o=game["player_o"],
        status=game["status"]
    )

# PUBLIC_INTERFACE
@app.get("/game/{game_id}", response_model=GameStateResponse, tags=["game"], summary="Get game state", description="Gets the current state of a game.")
def get_game_state(game_id: str):
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return GameStateResponse(
        game_id=game["game_id"],
        player_x=game["player_x"],
        player_o=game["player_o"],
        board=game["board"],
        next_turn=game["next_turn"],
        winner=game["winner"],
        status=game["status"],
    )

# PUBLIC_INTERFACE
@app.post("/game/{game_id}/move", response_model=MoveResponse, tags=["game"], summary="Make a move", description="Make a move on the game board (row and col 0-2).")
def make_move(game_id: str, move: MoveRequest):
    game = games.get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game["status"] != "in_progress":
        raise HTTPException(status_code=400, detail="Game is not in progress")
    if move.username not in [game["player_x"], game["player_o"]]:
        raise HTTPException(status_code=403, detail="Player not in this game")
    current_symbol = "X" if move.username == game["player_x"] else "O"
    if game["next_turn"] != move.username:
        raise HTTPException(status_code=400, detail="Not this player's turn")
    row, col = move.row, move.col
    if game["board"][row][col] is not None:
        raise HTTPException(status_code=400, detail="Cell already occupied")
    # Make move 
    game["board"][row][col] = current_symbol
    winner = check_winner(game["board"])
    if winner == "draw":
        game["winner"] = None
        game["status"] = "completed"
        players[game["player_x"]]["games_played"] += 1
        players[game["player_o"]]["games_played"] += 1
        game["next_turn"] = None
    elif winner in ["X", "O"]:
        win_player = game["player_x"] if winner == "X" else game["player_o"]
        lose_player = game["player_o"] if winner == "X" else game["player_x"]
        game["winner"] = win_player
        game["status"] = "completed"
        mark_player_win_loss(win_player, lose_player)
        game["next_turn"] = None
    else:
        game["next_turn"] = (
            game["player_o"] if move.username == game["player_x"] else game["player_x"]
        )

    return MoveResponse(
        game_id=game["game_id"],
        board=game["board"],
        next_turn=game["next_turn"],
        winner=game["winner"],
        status=game["status"],
    )

# PUBLIC_INTERFACE
@app.get("/leaderboard", response_model=LeaderboardResponse, tags=["leaderboard"], summary="Get leaderboard", description="Get all players' win count sorted (top 10 displayed).")
def leaderboard():
    lb = get_leaderboard()[:10]
    return LeaderboardResponse(leaderboard=[ScoreEntry(**entry) for entry in lb])

# PUBLIC_INTERFACE
@app.get("/score/{username}", response_model=PlayerResponse, tags=["leaderboard"], summary="Get player score", description="Get win/loss/games_played stats for player.")
def get_score(username: str):
    if username not in players:
        raise HTTPException(status_code=404, detail="Player not found")
    return PlayerResponse(**players[username])
