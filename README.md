# Maze Munch

A browser-based Pac-Man-style maze game served from a small Python container. Player profiles and scores are stored in SQLite.

## What is included

- Easy, normal, and hard difficulty settings
- Player-name profiles, saved difficulty, best score per level, attempts, and unlocked stages
- A next-stage button after clearing a level; each stage changes the maze orientation and makes ghosts faster
- A global homepage leaderboard, ranked by the sum of each player's best score per level
- A pause menu with resume and exit-to-home buttons
- Ghosts use maze pathfinding to chase, ambush, or flee from the player
- No countdown timer; easy mode gives more lives and slower ghosts
- Responsive board that fits the browser window, with keyboard and touch controls
- SQLite data stored in a Docker named volume so it survives container rebuilds and restarts

## Run with Docker Compose

Install Docker Desktop (Mac/Windows) or Docker Engine with the Compose plugin (Linux), clone this repository, then run:

```bash
git clone https://github.com/khomkrit77/aws-lab1.git
cd aws-lab1
docker compose up -d --build
```

Open [http://localhost:8083](http://localhost:8083). On a remote VM, use `http://<VM-IP>:8083` after allowing the port through its firewall/security group.

To choose a different host port:

```bash
APP_PORT=8090 docker compose up -d --build
```

After pulling updates, rebuild with `docker compose up -d --build`. View status and logs with:

```bash
docker compose ps
docker compose logs -f
```

Stop the container with `docker compose down`. The named volume keeps the database. Avoid `docker compose down -v` if you want to retain player records.

## Run without Docker

Python 3.10 or newer is enough; no packages need to be installed:

```bash
python3 server.py
```

Then open [http://localhost:8000](http://localhost:8000).

## Controls

- Arrow keys or WASD: move
- Space: pause
- Touch arrow buttons: move on mobile
- Sound button: toggle game sounds

## Demo account note

This prototype identifies a profile by player name only. It has no password or account verification, so anyone who can reach the game can enter the same name and change its progress. Keep it on a trusted/private network until real authentication is added for a public deployment.
