import json

def get_keys(d, prefix=''):
    keys = set()
    for k, v in d.items():
        if isinstance(v, dict):
            keys.update(get_keys(v, prefix + k + '.'))
        else:
            keys.add(prefix + k)
    return keys

ru_data = json.load(open('frontend/src/locales/ru.json', encoding='utf-8'))
en_data = json.load(open('frontend/src/locales/en.json', encoding='utf-8'))
uz_data = json.load(open('frontend/src/locales/uz.json', encoding='utf-8'))

ru_keys = get_keys(ru_data)
en_keys = get_keys(en_data)
uz_keys = get_keys(uz_data)

print(f"RU keys: {len(ru_keys)}")
print(f"EN keys: {len(en_keys)}")
print(f"UZ keys: {len(uz_keys)}")

print(f"Missing in EN (from RU): {len(ru_keys - en_keys)}")
# print(list(ru_keys - en_keys)[:10])
print(f"Missing in UZ (from RU): {len(ru_keys - uz_keys)}")
# print(list(ru_keys - uz_keys)[:10])

def insert_missing(base_d, target_d):
    for k, v in base_d.items():
        if k not in target_d:
            target_d[k] = v
        elif isinstance(v, dict) and isinstance(target_d[k], dict):
            insert_missing(v, target_d[k])

insert_missing(ru_data, en_data)
insert_missing(ru_data, uz_data)

json.dump(en_data, open('frontend/src/locales/en.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
json.dump(uz_data, open('frontend/src/locales/uz.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print("Updated en.json and uz.json with missing keys (values from ru.json).")
