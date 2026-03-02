from __future__ import annotations

import sys

from ai_support.remote_agent.poller import run_forever


def main() -> int:
    try:
        run_forever()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print(f"[AI-Support RemotePoller] Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
