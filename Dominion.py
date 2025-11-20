from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import argparse


def load_cards(path: str | Path = "cards.json") -> List[Dict[str, Any]]:
    """Load cards from a JSON file and return a list of dicts.

    Args:
        path: path to the cards.json file (defaults to "cards.json" in cwd).

    Returns:
        List of card dictionaries.

    Raises:
        FileNotFoundError, json.JSONDecodeError
    """
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # If the JSON contains a top-level object with a key like "cards", try to be helpful.
    if isinstance(data, dict):
        # common keys could be 'cards' or 'Cards'
        for key in ("cards", "Cards", "data"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # if dict appears to be a single card, wrap it
        if all(isinstance(v, (str, int, float, list, dict, bool, type(None))) for v in data.values()):
            # heuristically decide it's a single card if it has a 'name' key
            if "name" in data:
                return [data]
            # otherwise return empty list to avoid surprising behavior
            return []

    if not isinstance(data, list):
        raise ValueError(f"Unexpected JSON structure in {p!s}: expected list or dict with 'cards' key")

    return data


def get_card_by_name(cards: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Case-insensitive search for the first card whose 'name' matches (or contains) the query."""
    name_low = name.lower()
    for c in cards:
        card_name = str(c.get("name") or c.get("title") or "").lower()
        if card_name == name_low or name_low in card_name:
            return c
    return None


def filter_cards(cards: List[Dict[str, Any]], **criteria) -> List[Dict[str, Any]]:
    """Filter cards by exact key/value matches. Matching is case-insensitive for strings."""
    out = []
    for c in cards:
        ok = True
        for k, v in criteria.items():
            val = c.get(k)
            if isinstance(val, str) and isinstance(v, str):
                if val.lower() != v.lower():
                    ok = False
                    break
            else:
                if val != v:
                    ok = False
                    break
        if ok:
            out.append(c)
    return out


def group_by(cards: List[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for c in cards:
        k = str(c.get(key, "(none)"))
        grouped.setdefault(k, []).append(c)
    return grouped


def save_pretty(cards: List[Dict[str, Any]], out_path: str | Path) -> None:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(cards, f, indent=2, ensure_ascii=False)


def _print_card(card: Dict[str, Any]) -> None:
    print(json.dumps(card, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Load and query Dominion cards from a cards.json file.")
    parser.add_argument("--path", "-p", default="cards.json", help="path to cards.json")
    parser.add_argument("--name", "-n", help="search card by name (case-insensitive, substring allowed)")
    parser.add_argument("--type", "-t", dest="type_", help="filter by card 'type' field")
    parser.add_argument("--list-types", action="store_true", help="list all card types present")
    parser.add_argument("--save-pretty", help="save parsed cards to a pretty-printed JSON file")
    args = parser.parse_args()

    cards = load_cards(args.path)
    if args.save_pretty:
        save_pretty(cards, args.save_pretty)
        print(f"Saved {len(cards)} cards to {args.save_pretty}")
        return

    if True:  # was originally if args.list_types:
        grouped = group_by(cards, "type")
        for t, items in grouped.items():
            print(f"{t}: {len(items)}")
        

    if args.name:
        card = get_card_by_name(cards, args.name)
        if card:
            _print_card(card)
        else:
            print(f"No card found matching '{args.name}'")
        return

    if args.type_:
        matched = filter_cards(cards, type=args.type_)
        print(f"Found {len(matched)} cards with type '{args.type_}'")
        for c in matched:
            print("-", c.get("name") or c.get("title"))
        return

    # default: print summary
    print(f"Loaded {len(cards)} cards from {args.path}")


if __name__ == "__main__":
    main()
