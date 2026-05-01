import sys
from bashmage.app import BashMageApp
from bashmage.storage import load_commands


def main() -> None:
    try:
        commands = load_commands()
    except Exception as e:
        print(f"bashmage: error loading commands: {e}", file=sys.stderr)
        sys.exit(1)

    saved_stdout = sys.stdout
    saved_stderr = sys.stderr
    tty_file = None

    try:
        if not sys.stdout.isatty():
            tty_file = open("/dev/tty", "w")
            sys.stdout = tty_file
            sys.stderr = tty_file

        app = BashMageApp(commands)
        result = app.run()
    finally:
        sys.stdout = saved_stdout
        sys.stderr = saved_stderr
        if tty_file is not None:
            tty_file.close()

    if result is not None:
        print(result)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
