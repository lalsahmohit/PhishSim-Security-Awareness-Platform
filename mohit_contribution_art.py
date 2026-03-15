"""
GitHub Contribution Graph Art — spells "MOHIT"
Run this inside your PhishSim repo folder.
It creates commits on specific past dates to light up the squares.
"""

import subprocess
from datetime import datetime, timedelta

# ── PIXEL FONT (7 rows = days of week, each letter = 5 cols wide) ──
# Row 0 = Sunday, Row 6 = Saturday
# We use rows 1–5 (Mon–Fri) for the letters, leaving Sun/Sat empty

LETTERS = {
    'M': [
        [1,0,0,0,1],
        [1,1,0,1,1],
        [1,0,1,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    'O': [
        [0,1,1,1,0],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
        [0,1,1,1,0],
    ],
    'H': [
        [1,0,0,0,1],
        [1,0,0,0,1],
        [1,1,1,1,1],
        [1,0,0,0,1],
        [1,0,0,0,1],
    ],
    'I': [
        [1,1,1,1,1],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [1,1,1,1,1],
    ],
    'T': [
        [1,1,1,1,1],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
        [0,0,1,0,0],
    ],
}

TEXT    = "MOHIT"
SPACING = 1   # blank columns between letters

def build_grid(text):
    """Returns list of columns, each column = 7 rows (0=Sun..6=Sat)."""
    columns = []
    for i, char in enumerate(text):
        letter_cols = LETTERS[char]  # 5 rows × 5 cols
        # Each col in letter_cols = a day column (5 rows, mapped to rows 1-5)
        for col_idx in range(5):
            col = [0] * 7  # 7 days
            for row_idx in range(5):
                col[row_idx + 1] = letter_cols[row_idx][col_idx]
            columns.append(col)
        # Add spacing columns (except after last letter)
        if i < len(text) - 1:
            for _ in range(SPACING):
                columns.append([0] * 7)
    return columns

def get_start_date(num_cols):
    """
    Find the most recent Sunday from which we can fit all columns
    and still be in the past (visible on the contribution graph).
    We go back (num_cols + 4) weeks from today.
    """
    today = datetime.now()
    # Roll back to the most recent Sunday
    days_since_sunday = today.weekday() + 1  # Monday=0, so Sunday is 6+1=7 mod 7
    days_since_sunday = days_since_sunday % 7
    last_sunday = today - timedelta(days=days_since_sunday)
    # Go back enough weeks so the text fits and ends ~2 weeks ago
    start = last_sunday - timedelta(weeks=num_cols + 2)
    return start

def make_commit(date_str, message):
    """Create an empty commit with a specific date."""
    env_date = f"{date_str}T12:00:00"
    cmd = [
        "git", "commit", "--allow-empty",
        "-m", message,
        "--date", env_date
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ⚠ Error: {result.stderr.strip()}")
    else:
        print(f"  ✅ Committed: {date_str} — {message}")

def main():
    print("=" * 50)
    print("  GitHub Contribution Art — MOHIT")
    print("=" * 50)

    columns = build_grid(TEXT)
    start_date = get_start_date(len(columns))

    print(f"\n📅 Starting from: {start_date.strftime('%Y-%m-%d')}")
    print(f"📐 Total columns: {len(columns)}")
    print(f"📝 Total commits to create: {sum(sum(col) for col in columns)}\n")

    commit_count = 0
    for week_offset, col in enumerate(columns):
        for day_offset, lit in enumerate(col):
            if lit:
                date = start_date + timedelta(weeks=week_offset, days=day_offset)
                date_str = date.strftime("%Y-%m-%d")
                make_commit(date_str, f"contribution-art: {TEXT} w{week_offset}d{day_offset}")
                commit_count += 1

    print(f"\n🎉 Done! Created {commit_count} commits.")
    print("\nNow push to GitHub:")
    print("  git push origin main --force\n")

if __name__ == "__main__":
    main()
