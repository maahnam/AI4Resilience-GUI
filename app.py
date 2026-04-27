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
    print("📡 Access the application at: http://localhost:5000")

    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
