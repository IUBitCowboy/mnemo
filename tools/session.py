"""
Session recording for Mnemo CLI chat tool.

Creates a Markdown session file on first response and appends each turn
immediately so no data is lost if the user quits mid-session.

Filename format: YYYYMMDDHHMMSS_<persona_stem>.md
"""

import os
from datetime import datetime
from pathlib import Path


class Session:
    def __init__(self, sessions_dir: str, persona_path: str, provider: str, model: str):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        persona_stem = Path(persona_path).stem
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S")
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        filename = f"{timestamp}_{persona_stem}.md"
        self.path = self.sessions_dir / filename
        self._initialized = False

        self._frontmatter = (
            f"---\n"
            f"date: {date_str}\n"
            f"time: {time_str}\n"
            f"provider: {provider}\n"
            f"model: {model}\n"
            f"persona: {Path(persona_path).name}\n"
            f"---\n\n"
            f"# Session: {date_str} — {persona_stem}\n"
        )

    def append_turn(self, user_input: str, assistant_response: str):
        if not self._initialized:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(self._frontmatter)
            self._initialized = True

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(f"\n## [Human]\n{user_input}\n\n## [Assistant]\n{assistant_response}\n")
