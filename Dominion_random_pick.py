import sqlite3
import random

DB = "dominion.db"

def get_sets(cur):
    cur.execute("SELECT DISTINCT set_name FROM card_sets ORDER BY set_name")
    return [row[0] for row in cur.fetchall()]

def get_types(cur):
    cur.execute("SELECT DISTINCT type FROM card_types ORDER BY type")
    return [row[0] for row in cur.fetchall()]

def get_cards(cur, selected_sets=None, selected_types=None):
    query = """
    SELECT DISTINCT c.id, c.name, cs.set_name
    FROM cards c
    JOIN card_sets cs ON c.id = cs.card_id
    JOIN card_types ct ON c.id = ct.card_id
    WHERE 1=1
    """
    params = []

    if selected_sets:
        query += " AND cs.set_name IN ({})".format(",".join("?" * len(selected_sets)))
        params.extend(selected_sets)

    if selected_types:
        query += " AND ct.type IN ({})".format(",".join("?" * len(selected_types)))
        params.extend(selected_types)

    cur.execute(query, params)
    return cur.fetchall()

def pick_random_cards(cards, amount):
    return random.sample(cards, amount) if amount <= len(cards) else cards

def parse_list_input(value):
    if not value.strip():
        return None
    return [v.strip() for v in value.split(",")]

def main():
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    print("\nAvailable Sets:")
    for s in get_sets(cur):
        print(" -", s)

    chosen_sets = input("\nEnter sets (comma-separated) or leave blank for ALL: ")
    selected_sets = parse_list_input(chosen_sets)

    print("\nAvailable Types:")
    for t in get_types(cur):
        print(" -", t)

    chosen_types = input("\nEnter types (comma-separated) or leave blank for ALL: ")
    selected_types = parse_list_input(chosen_types)

    amount = int(input("\nHow many random cards do you want to pick? "))

    cards = get_cards(cur, selected_sets, selected_types)

    if not cards:
        print("\nNo cards match your filters.")
        return

    print(f"\nFound {len(cards)} matching cards.")

    chosen = pick_random_cards(cards, amount)

    print("\n=== RANDOMLY SELECTED CARDS ===")
    for cid, name, setname in chosen:
        print(f"- {name} ({setname})")

    conn.close()

if __name__ == "__main__":
    main()
