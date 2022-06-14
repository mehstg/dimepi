import json

with open('track_mappings.json') as f:
    track_mappings = json.load(f)

def get_track_id(id):
    return next((item.get('uri') for item in track_mappings['tracks'] if item["id"] == id), False)