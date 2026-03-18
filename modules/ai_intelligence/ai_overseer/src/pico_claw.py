"""
PicoClaw Schema-Space Walker (MPS 12)

A zero-LLM, deterministic micro-agent designed for schema-space interaction games
(like hide-and-seek on AntifaFM). Its primary function is to traverse the
codebase directory tree using a defined state and move budget.

WSP 97 Compliant: Built following Lead Dev/CTO Architect prompt.
"""

import argparse
import logging
import os
import random
import uuid
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class PicoClaw:
    """
    PicoClaw agent instance with minimal state tracking.
    """
    
    def __init__(self, start_pos: str, initial_energy: int = 100, team: str = "neutral"):
        """
        Initialize the PicoClaw agent.
        
        Args:
            start_pos: Initial absolute or relative path to spawn in.
            initial_energy: Total allowable moves for this agent.
            team: Designation for game modes (e.g., 'seeker', 'hider').
        """
        self.id = str(uuid.uuid4())[:8]  # Short ID for easier logging
        self.position = os.path.abspath(start_pos)
        self.energy = initial_energy
        self.team = team

    def _get_valid_neighbors(self) -> List[str]:
        """
        Calculates all valid adjacent paths (parent directory or child items).
        
        Returns:
            List of absolute paths that can be traversed.
        """
        neighbors = []
        try:
            # Can move up to the parent directory
            parent = os.path.dirname(self.position)
            if parent and parent != self.position:
                neighbors.append(parent)
            
            # Can move down into children if current position is a directory
            if os.path.isdir(self.position):
                for item in os.listdir(self.position):
                    # Skip hidden directories like .git to prevent escaping bounds needlessly
                    if not item.startswith('.'):
                        full_path = os.path.join(self.position, item)
                        neighbors.append(full_path)
        except PermissionError:
             logger.debug(f"PicoClaw {self.id}: Permission denied exploring {self.position}")
             
        return neighbors

    def move(self) -> Dict[str, Any]:
        """
        Executes a single deterministic move to a random valid neighbor.
        
        Returns:
            Dict containing the resulting state and status of the move.
        """
        if self.energy <= 0:
            return {"status": "exhausted", "position": self.position, "id": self.id, "team": self.team}
            
        neighbors = self._get_valid_neighbors()
        
        if not neighbors:
             # Agent is trapped
             return {"status": "trapped", "position": self.position, "id": self.id, "team": self.team}
             
        # Make the move
        self.position = random.choice(neighbors)
        self.energy -= 1
        
        return {
            "status": "moved",
            "position": self.position,
            "energy_remaining": self.energy,
            "team": self.team,
            "id": self.id
        }

def run_simulation(start: str, energy: int, team: str):
    """Run a basic interactive simulation of the walker."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    
    walker = PicoClaw(start_pos=start, initial_energy=energy, team=team)
    print(f"[*] SPWAND: PicoClaw [{walker.id}] ({walker.team})")
    print(f"[*] POS:    {walker.position}")
    print(f"[*] ENERGY: {walker.energy}\n")
    print("-" * 50)
    
    while walker.energy > 0:
        result = walker.move()
        status = result['status'].upper()
        
        if status == "MOVED":
            print(f"[{status}] -> {result['position']} (Energy: {result['energy_remaining']})")
        else:
            print(f"[{status}] -> Trapped at {result['position']}")
            break
            
    print("-" * 50)
    print(f"[*] END STATE: Energy={walker.energy}, Final Pos: {walker.position}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PicoClaw Schema-Space Walker")
    parser.add_argument("--start", default=".", help="Starting directory path")
    parser.add_argument("--energy", type=int, default=15, help="Energy budget (max moves)")
    parser.add_argument("--team", default="seeker", help="Team designation")
    args = parser.parse_args()
    
    run_simulation(args.start, args.energy, args.team)
