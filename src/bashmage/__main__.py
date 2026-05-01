import sys
from bashmage.app import BashMageApp
from bashmage.storage import load_commands


def main() -> None:
    try:
        commands = load_commands()
    except Exception as e:
        print(f"bashmage: error loading commands: {e}", file=sys.stderr)
        sys.exit(1)

    output_stream = sys.stdout
    if not sys.stdout.isatty():
        tty = open("/dev/tty", "w")
        sys.stdout = tty
        sys.stderr = tty

    app = BashMageApp(commands)
    result = app.run()

    sys.stdout = output_stream

    if result is not None:
        print(result)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
