import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from lahso.web import create_app, socketio  # noqa: E402

app = create_app()

if __name__ == "__main__":
    print("🚀 LAHSO Web Application starting...")
    print("📡 Access the Flask API at: http://localhost:5001")
    print("🖥️  Start the SvelteKit UI from frontend/ with: bun --bun run dev")

    socketio.run(app, host="0.0.0.0", port=5001, debug=True)
