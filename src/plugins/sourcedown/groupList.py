import os
import json
from pathlib import Path

yellow_book = dict()

def loadPage():
    data = None
    with open(os.path.join(Path(__file__).parent.resolve(), 'yellow_book.json')) as f:
        data = json.load(f)

    for k, v in data.items():
        if isinstance(v, dict):
            for group_name, group_id in v.items():
                yellow_book[group_id] = group_name
        else:
            yellow_book[v] = k

loadPage()
