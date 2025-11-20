import json
import sqlite3

# Path to your cards.json
json_file = 'cards.json'

# Load JSON data
with open(json_file, 'r', encoding='utf-8') as f:
    cards = json.load(f)

print(f"Loaded {len(cards)} cards from {json_file}.")

# Connect to SQLite database (creates it if not exists)
conn = sqlite3.connect('dominion.db')
cur = conn.cursor()

# Drop old tables if they exist
cur.execute('DROP TABLE IF EXISTS cards')
cur.execute('DROP TABLE IF EXISTS card_types')
cur.execute('DROP TABLE IF EXISTS card_sets')

# ------------------
# Create main cards table
# ------------------
cur.execute('''
CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    types TEXT,
    set_name TEXT,
    cost TEXT,
    coins_coffers TEXT,
    actions_villagers TEXT,
    buys TEXT,
    cards TEXT,
    text TEXT,
    victory_points TEXT
)
''')

# Insert all cards into the cards table
for card in cards:
    cur.execute('''
    INSERT INTO cards 
    (name, types, set_name, cost, coins_coffers, actions_villagers, buys, cards, text, victory_points)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        card.get('Name', ''),
        card.get('Types', ''),
        card.get('Set', ''),
        card.get('Cost', ''),
        card.get('Coins_Coffers', ''),
        card.get('Actions_Villagers', ''),
        card.get('Buys', ''),
        card.get('Cards', ''),
        card.get('Text', ''),
        card.get('Victory_Points', '')
    ))

conn.commit()
print("cards table created and populated.")

# ------------------
# Create card_types table (one row per card-type)
# ------------------
cur.execute('''
CREATE TABLE card_types (
    card_id INTEGER,
    type TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
''')

cur.execute('SELECT id, types FROM cards')
all_cards = cur.fetchall()

for card_id, types_str in all_cards:
    if not types_str:
        continue
    # Split types by '-' and strip whitespace
    types = [t.strip() for t in types_str.split('-')]
    for t in types:
        cur.execute('INSERT INTO card_types (card_id, type) VALUES (?, ?)', (card_id, t))

conn.commit()
print("card_types table created and populated.")

# ------------------
# Create card_sets table (one row per card-set)
# ------------------
cur.execute('''
CREATE TABLE card_sets (
    card_id INTEGER,
    set_name TEXT,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
''')

cur.execute('SELECT id, set_name FROM cards')
all_cards = cur.fetchall()

for card_id, set_name in all_cards:
    if not set_name:
        continue
    # Split by ',' if a card has multiple sets (just in case)
    sets = [s.strip() for s in set_name.split(',')]
    for s in sets:
        cur.execute('INSERT INTO card_sets (card_id, set_name) VALUES (?, ?)', (card_id, s))

conn.commit()
conn.close()

print("card_sets table created and populated.")
print("Database 'dominion.db' is fully ready to use!")
