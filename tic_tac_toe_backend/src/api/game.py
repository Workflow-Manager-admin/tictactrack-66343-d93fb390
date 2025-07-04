from typing import Optional, Dict, List, Any
from uuid import uuid4

from .models import (
    GameCreatedResponse,
    GameStateResponse, MoveRequest, MoveResponse, PlayerResponse,
)

BOARD_SIZE = 3

# In-memory data stores
players: Dict[str, Dict[str, Any]] = {}  # username -> stats/info
games: Dict[str, Dict[str, Any]] = {}    # game_id -> state

# PUBLIC_INTERFACE
class GameManager:
    """Manages in-memory games and player state."""

    @staticmethod
    def create_player(username: str) -> PlayerResponse:
        """Register a new player or return existing."""
        if username not in players:
            players[username] = {
                "username": username,
                "wins": 0,
                "losses": 0,
                "games_played": 0,
            }
        return PlayerResponse(**players[username])

    @staticmethod
    def get_player(username: str) -> Optional[PlayerResponse]:
        """Fetch player info if exists."""
        pl = players.get(username)
        if pl:
            return PlayerResponse(**pl)
        return None

    @staticmethod
    def start_game(username: str) -> GameCreatedResponse:
        """Creates a new game initiated by username (player_x)."""
        game_id = str(uuid4())
        games[game_id] = {
            "game_id": game_id,
            "player_x": username,
            "player_o": None,
            "board": GameManager._create_board(),
            "next_turn": username,
            "winner": None,
            "status": "waiting"
        }
        return GameCreatedResponse(
            game_id=game_id,
            player_x=username,
            player_o=None,
            status="waiting"
        )

    @staticmethod
    def join_game(game_id: str, username: str) -> Optional[GameCreatedResponse]:
        """Joins an available game as player_o."""
        game = games.get(game_id)
        if not game or game["status"] != "waiting":
            return None
        if game["player_x"] == username or game["player_o"]:
            return None
        game["player_o"] = username
        game["status"] = "in_progress"
        return GameCreatedResponse(
            game_id=game_id,
            player_x=game["player_x"],
            player_o=game["player_o"],
            status=game["status"]
        )

    @staticmethod
    def get_game_state(game_id: str) -> Optional[GameStateResponse]:
        """Return the GameState for a given game_id."""
        game = games.get(game_id)
        if not game:
            return None
        return GameStateResponse(
            game_id=game_id,
            player_x=game["player_x"],
            player_o=game["player_o"],
            board=game["board"],
            next_turn=game["next_turn"],
            winner=game["winner"],
            status=game["status"]
        )

    @staticmethod
    def make_move(game_id: str, move: MoveRequest) -> Optional[MoveResponse]:
        """Handle a move being played in a game."""
        game = games.get(game_id)
        if (not game or
            game["status"] != "in_progress" or
            move.username not in [game["player_x"], game["player_o"]] or
            game["next_turn"] != move.username or
            not (0 <= move.row < BOARD_SIZE and 0 <= move.col < BOARD_SIZE)):
            return None

        symbol = "X" if move.username == game["player_x"] else "O"
        if game["board"][move.row][move.col] is not None:
            return None  # Illegal move

        # Place symbol
        game["board"][move.row][move.col] = symbol

        winner_result = GameManager._check_winner(game["board"])
        if winner_result == "draw":
            game["winner"] = None
            game["status"] = "completed"
            GameManager._increment_stats(game["player_x"], draw=True)
            GameManager._increment_stats(game["player_o"], draw=True)
            game["next_turn"] = None
        elif winner_result in {"X", "O"}:
            win_player = game["player_x"] if winner_result == "X" else game["player_o"]
            lose_player = game["player_o"] if winner_result == "X" else game["player_x"]
            game["winner"] = win_player
            game["status"] = "completed"
            GameManager._increment_stats(win_player, win=True)
            GameManager._increment_stats(lose_player, loss=True)
            game["next_turn"] = None
        else:
            # Switch turn
            game["next_turn"] = (
                game["player_o"] if move.username == game["player_x"] else game["player_x"]
            )

        return MoveResponse(
            game_id=game_id,
            board=game["board"],
            next_turn=game["next_turn"],
            winner=game["winner"],
            status=game["status"]
        )

    @staticmethod
    def _create_board() -> List[List[Optional[str]]]:
        """Creates a blank BOARD_SIZE x BOARD_SIZE board."""
        return [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]

    @staticmethod
    def _check_winner(board: List[List[Optional[str]]]) -> Optional[str]:
        """Checks board for winner: 'X', 'O', or 'draw', or None."""
        lines = board + [list(t) for t in zip(*board)]  # rows & cols
        lines.append([board[i][i] for i in range(BOARD_SIZE)])  # diag
        lines.append([board[i][BOARD_SIZE - 1 - i] for i in range(BOARD_SIZE)])  # anti-diag

        for line in lines:
            if line[0] and all(cell == line[0] for cell in line):
                return line[0]
        # Draw
        if all(cell is not None for row in board for cell in row):
            return "draw"
        return None

    @staticmethod
    def _increment_stats(username: str, win=False, loss=False, draw=False):
        if username in players:
            if win:
                players[username]["wins"] += 1
            if loss:
                players[username]["losses"] += 1
            players[username]["games_played"] += 1
            # For draw, just increment games_played

    @staticmethod
    def leaderboard() -> List[Dict[str, Any]]:
        return sorted(
            [
                {"username": uname, "wins": pdata["wins"]}
                for uname, pdata in players.items()
            ],
            key=lambda e: e["wins"],
            reverse=True
        )

    @staticmethod
    def all_players() -> List[PlayerResponse]:
        return [PlayerResponse(**pdata) for pdata in players.values()]
