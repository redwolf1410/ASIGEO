import json


data1 = {'user': 'IWarmer','password': 'IWarmer'}
with open("json_f/user.json", "w") as f:
    json.dump(data1, f)


