# Spring Canvas IDE

> A Makepad-inspired infinite canvas that maps your Spring Boot project into live, draggable code windows connected by dependency lines.

## Quick Start

```bash
bash start.sh
```

Then open **http://127.0.0.1:5000** in your browser, paste the **absolute path** to your Spring project, and click **▶ Load Project**.

## Features

- **Infinite canvas** — drag code windows freely, scroll to navigate
- **Live Monaco editors** — full VS Code editor in every window, lazy-loaded so 200+ classes stays fast
- **Dependency arrows** — auto-detects `@Autowired`, constructor injection, field injection
- **Filter pills** — toggle Controllers / Services / Repos / DTOs / Entities at a glance
- **Class search** — instant filter by class name
- **Streaming progress** — real-time scan progress bar for large projects
- **Absolute path support** — point it at any project folder on your machine

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | Python + Flask |
| Editor | Monaco Editor (VS Code core) |
| Graph | Custom SVG + IntersectionObserver |

## File Structure

```
code_navigator/
├── app.py            # Flask backend + Spring class scanner
├── start.sh          # One-click launcher
├── requirements.txt
└── static/
    ├── makepad_real.html   # Main canvas UI ← open this
    ├── index.html          # Simple file explorer
    └── ...
```
