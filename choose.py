#!/usr/bin/python3
#
# An interactive shell script to help user choose between N options.
#
# Usage: choose.py

import argparse
import json
import os
import sys
import urllib.request

__version__ = "0.1.0"

try:
    import tomllib
except ModuleNotFoundError:  # Python <3.11 fallback to disabled config
    tomllib = None


DEFAULT_CONFIG = {
    "max_items": 8,
    "ai_endpoint": "",
    "ai_model": "",
    "ai_api_key": "",
}


def load_config(config_path=None):
    """Load user config from ~/.config/choose/choose.toml; fall back to defaults."""

    if tomllib is None:
        return DEFAULT_CONFIG.copy()

    path = config_path or os.path.expanduser("~/.config/choose/choose.toml")
    config = DEFAULT_CONFIG.copy()

    if os.path.exists(path):
        try:
            with open(path, "rb") as fh:
                data = tomllib.load(fh)
            for key, default_value in DEFAULT_CONFIG.items():
                if isinstance(data.get(key), type(default_value)):
                    config[key] = data[key]
        except Exception:
            # Ignore malformed config and use defaults
            pass

    return config


def ai_enabled(config):
    """Return True if a model is configured; empty model means AI is disabled."""

    return bool(config.get("ai_model", "").strip())


def read_items_from_stdin():
    """Read non-empty lines from stdin and return a list of items."""

    return [line.strip() for line in sys.stdin if line.strip()]


def read_items_interactive():
    """Prompt user for one item per line until 'done' is entered."""

    print("Enter items to choose from (one per line). Type 'done' when finished:")
    items = []
    while True:
        line = input().strip()
        if line.lower() == "done":
            break
        if line:
            items.append(line)
    return items


def label_items(items):
    """Assign alphabetic labels starting at A; returns list of (label, item)."""

    labels = []
    for idx, item in enumerate(items):
        label = chr(ord('A') + idx)
        labels.append((label, item))
    return labels


def interactive_prune(items, max_items):
    """Ask user which items to remove until count <= max_items."""

    current = list(items)
    while len(current) > max_items:
        print(f"You have {len(current)} items, but the limit is {max_items}.")
        for idx, item in enumerate(current, start=1):
            print(f"{idx}. {item}")
        choice = input("Enter the number of an item to remove (or press Enter to stop): ").strip()
        if not choice:
            break
        if choice.isdigit():
            pos = int(choice)
            if 1 <= pos <= len(current):
                removed = current.pop(pos - 1)
                print(f"Removed: {removed}")
                continue
        print("Invalid selection; please try again.")
    return current[:max_items]


def ai_suggest_keep(items, config, verbose=False):
    """Use OpenAI-compatible API to suggest which items to keep; expect JSON list or {"keep": [...]} response."""

    endpoint = config.get("ai_endpoint", "").strip()
    model = config.get("ai_model", "").strip()
    api_key = config.get("ai_api_key", "").strip()

    if not endpoint or not model:
        if verbose:
            print(f"[verbose] AI skipped: endpoint={endpoint!r}, model={model!r}")
        return None

    prompt_text = (
        "Given the following list of items, suggest which to keep within the limit. "
        "Respond ONLY with a JSON object: {\"keep\": [\"item\", ...]} with items drawn from the list."
    )
    user_json = json.dumps({"items": items})
    messages = [
        {"role": "system", "content": "You help prune lists."},
        {"role": "user", "content": f"{prompt_text}\nItems: {user_json}"},
    ]

    payload = json.dumps({"model": model, "messages": messages, "temperature": 0}).encode()
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if verbose:
        print(f"[verbose] AI request: POST {endpoint} model={model}")

    try:
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode()
            data = json.loads(raw)
    except Exception as exc:
        if verbose:
            print(f"[verbose] AI request failed: {exc}")
        return None

    # Try to extract the assistant message content
    content = None
    if isinstance(data, dict):
        choices = data.get("choices")
        if choices and isinstance(choices, list):
            message = choices[0].get("message") or {}
            content = message.get("content")
    if not content and isinstance(data, dict):
        content = data.get("content")

    if verbose:
        print(f"[verbose] AI response content: {content!r}")

    if not content:
        return None

    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return [item for item in parsed if item in items]
        if isinstance(parsed, dict) and isinstance(parsed.get("keep"), list):
            return [item for item in parsed["keep"] if item in items]
    except Exception as exc:
        if verbose:
            print(f"[verbose] AI response parse failed: {exc}")
        return None

    if verbose:
        print(f"[verbose] AI response had unexpected structure: {content!r}")
    return None


def ensure_interactive_input():
    """Ensure that interactive prompts can be read; reopen /dev/tty if stdin was piped."""

    if sys.stdin.isatty():
        return False
    try:
        sys.stdin = open("/dev/tty")
        return True
    except OSError:
        print("No TTY available for interactive prompts. Please run without piping stdin.")
        sys.exit(1)


def read_items(config, verbose=False):
    """Unified item intake with stdin and interactive modes plus over-limit handling."""

    from_stdin = not sys.stdin.isatty()
    items = read_items_from_stdin() if from_stdin else read_items_interactive()

    labeled = label_items(items)
    print("You are considering the following items:")
    for label, item in labeled:
        print(f"{label}: {item}")

    max_items = config.get("max_items", DEFAULT_CONFIG["max_items"])
    if len(items) > max_items:
        if from_stdin:
            ensure_interactive_input()
        kept = None
        if ai_enabled(config):
            kept = ai_suggest_keep(items, config, verbose=verbose)
            if kept:
                print("AI suggested keeping:")
                for item in kept:
                    print(f"- {item}")
                confirm = input("Use this selection? [Y/n]: ").strip().lower()
                if confirm == "n":
                    kept = None
        if kept is None:
            items = interactive_prune(items, max_items)
        else:
            items = kept[:max_items]

    return items

# Prompt user for a comma-separated list of options.
# TODO: Validate input.
# TODO: Also receive options as arguments, or by stdin.
# TODO: Allow for other separators.
def read_options():
    # Deprecated: retained for compatibility; new flow uses read_items().
    options = input("Enter a comma-separated list of options: ")
    return options.split(", ")

# For each option, ask whether user prefers this option or each of
# the other options. Do not repeat comparisons. Remember user's
# preferences so they can be used used as a tie-breaker.
# TODO: Validate input.
# TODO: Simplify input, e.g. "1" for first option, "2" for second.
def eval_options(options):
    import itertools

    preferences = {}
    labels = label_items(options)
    label_to_item = {label: item for label, item in labels}
    item_to_label = {item: label for label, item in labels}

    for option1, option2 in itertools.combinations(options, 2):
        label1 = item_to_label[option1]
        label2 = item_to_label[option2]
        prompt = f"Would you rather ({label1}) {option1} or ({label2}) {option2}? "

        while True:
            response = input(prompt).strip()
            # Accept label or full text
            choice = response.upper()
            if choice in label_to_item:
                selected = label_to_item[choice]
            else:
                selected = response

            if selected == option1 or selected == option2:
                preferences[(option1, option2)] = selected
                break

            print("Please answer with the option text or its letter label.")

    return preferences

# Rank options by count of how many times each was preferred over
# others.
# TODO: Solve ties here, or in output?
def rank_options(options, preferences):
    import collections
    counts = collections.Counter()
    for (option1, option2), preference in preferences.items():
        if preference == option1:
            counts[option1] += 1
        else:
            counts[option2] += 1
    return counts

# Output each ranked option and its preference count. Sort output by
# preference count.
# TODO: Solve ties here, or in ranking?
def print_ranked_options(ranked_options):
    for option, count in sorted(ranked_options.items(), key=lambda x: (-x[1], x[0])):
        print("%s: %d" % (option, count))

def parse_args(argv=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="choose",
        description="Choose among N options via pairwise comparison.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--config", metavar="PATH", default=None,
        help="path to config file (default: ~/.config/choose/choose.toml)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", default=False,
        help="show debug info (AI requests, config loading, etc.)",
    )
    return parser.parse_args(argv)


def main():
    args = parse_args()
    config = load_config(config_path=args.config)
    verbose = args.verbose
    if verbose:
        print(f"[verbose] config: { {k: ('***' if 'key' in k and v else v) for k, v in config.items()} }")
    options = read_items(config, verbose=verbose)
    preferences = eval_options(options)
    ranked_options = rank_options(options, preferences)
    print_ranked_options(ranked_options)

if __name__ == "__main__":
    main()
