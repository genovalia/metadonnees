import glob
import os
import json

dictionary = None
keywords = []

# load dictionary
with open("dictionary.json") as f:
    dictionary = json.load(f)

# find all dcat.json files
for file in glob.glob("**/dcat.json", recursive=True):
    print(file)
    with open(file) as f:
        data = f.read()
        # find all keywords in the file
        keywords.extend(json.loads(data).get("dcat:keyword", []))
# remove keywords that are in the dictionary
keywords = [k for k in keywords if k not in dictionary]
# print the keywords
print("untranslated keywords:")
print("{")
for k in keywords:
    print(f'  "{k}":"{k}",')
print("}")
