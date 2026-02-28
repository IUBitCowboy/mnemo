"""
Session recording for Mnemo CLI chat tool.

Creates a Markdown session file on first response and appends each turn
immediately so no data is lost if the user quits mid-session.

Filename format: YYYYMMDDHHMMSS_<persona_stem>.md
"""

from datetime import datetime
from pathlib import Path


class Session:
    def __init__(
        self,
        sessions_dir: str,
        persona_path: str,
        provider: str,
        model: str,
        context_files: list[str] | None = None,
    ):
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

        self._total_input = 0
        self._total_output = 0
        self._turn_count = 0

        context_lines = ""
        if context_files:
            context_lines = "context:\n" + "".join(
                f"  - {c}\n" for c in context_files
            )

        self._frontmatter = (
            f"---\n"
            f"date: {date_str}\n"
            f"time: {time_str}\n"
            f"provider: {provider}\n"
            f"model: {model}\n"
            f"persona: {Path(persona_path).name}\n"
            f"{context_lines}"
            f"---\n\n"
            f"# Session: {date_str} — {persona_stem}\n"
        )

    def append_turn(
        self,
        user_input: str,
        assistant_response: str,
        usage: dict | None = None,
        timing: dict | None = None,
    ):
        if not self._initialized:
            with open(self.path, "w", encoding="utf-8") as f:
                f.write(self._frontmatter)
            self._initialized = True

        if usage:
            self._total_input += usage.get("input_tokens", 0)
            self._total_output += usage.get("output_tokens", 0)
            usage_note = (
                f"*tokens — in: {usage['input_tokens']:,}, "
                f"out: {usage['output_tokens']:,}, "
                f"turn total: {usage['input_tokens'] + usage['output_tokens']:,}*"
            )
        else:
            usage_note = None

        if timing:
            response_s = timing.get("response_s")
            since_last_s = timing.get("since_last_s")
            parts = []
            if response_s is not None:
                parts.append(f"response: {response_s:.1f}s")
            if since_last_s is not None:
                # Format gap: seconds under a minute, otherwise Xm Ys
                if since_last_s < 60:
                    parts.append(f"gap: {since_last_s:.0f}s")
                else:
                    m, s = divmod(int(since_last_s), 60)
                    parts.append(f"gap: {m}m {s:02d}s")
            timing_note = f"*timing — {' | '.join(parts)}*" if parts else None
        else:
            timing_note = None

        self._turn_count += 1
        n = self._turn_count

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(f"\n## Q{n} [Human]\n{user_input}\n\n## A{n} [Assistant]\n{assistant_response}\n")
            if usage_note:
                f.write(f"\n{usage_note}\n")
            if timing_note:
                f.write(f"{timing_note}\n")

    def write_summary(self):
        """Append a token usage summary at the end of the session."""
        if not self._initialized or (self._total_input == 0 and self._total_output == 0):
            return
        total = self._total_input + self._total_output
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(
                f"\n---\n"
                f"*Session totals — in: {self._total_input:,}, "
                f"out: {self._total_output:,}, "
                f"total: {total:,} tokens*\n"
            )
