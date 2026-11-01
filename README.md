# Maze Munch

A small arcade maze game built with HTML, CSS, and JavaScript. The game is served by Nginx inside a Docker container; no Node.js runtime or external assets are needed.

## Run with Docker Compose

Install Docker Desktop (Mac/Windows) or Docker Engine with the Docker Compose plugin (Linux), then run from this repository:

```bash
docker compose up -d --build
```

Open [http://localhost:8083](http://localhost:8083).

To use a different host port:

```bash
APP_PORT=8090 docker compose up -d --build
```

Stop the container:

```bash
docker compose down
```

Check status and logs:

```bash
docker compose ps
docker compose logs -f
```

## Run directly without Docker

Open `index.html` in a modern browser, or serve the repository locally:

```bash
python3 -m http.server 8080
```

Then open [http://localhost:8080](http://localhost:8080).

## Controls

- Arrow keys or WASD: move
- Space: pause or resume
- Touch arrow buttons: move on mobile
- Sound button: toggle game sounds

Collect the dots, use the gold power orbs to make ghosts flee, and clear the maze.
