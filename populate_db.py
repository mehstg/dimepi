## Script to populate DB from json file
import json
import database

f = open ('track_mappings.json', "r")
  
data = json.loads(f.read())
  

for i in data['tracks']:
    database.set_track(i['id'],"","",i['uri'])
    print(f'Track {i["uri"]} added to DB')
  
f.close()