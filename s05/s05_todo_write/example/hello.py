"""Simple hello-world example module."""


def greet(name: str) -> str:
    """Return a greeting for the given name.

    Args:
        name: The name to include in the greeting.

    Returns:
        A greeting message as a string.
    """
    return f"Hello, {name}!"


def main() -> None:
    """Run the hello-world example."""
    print(greet("world"))


if __name__ == "__main__":
    main()
