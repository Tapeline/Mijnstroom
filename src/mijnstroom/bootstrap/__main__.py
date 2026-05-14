import sys

from mijnstroom.bootstrap import main as web_main
from mijnstroom.bootstrap import worker as worker_main


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m mijnstroom.bootstrap [web|worker]", file=sys.stderr)
        return 2
    command = sys.argv[1]
    if command == "web":
        web_main.main()
    elif command == "worker":
        worker_main.main()
    else:
        print(f"unknown command: {command}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
