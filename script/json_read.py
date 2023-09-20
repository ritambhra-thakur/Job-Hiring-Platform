import json
import os
import sys

import django

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "main.settings")
django.setup()


if django:
    from primary_data.models import City, Country, State

# city
# f1 = open(os.path.join("/home/softuvo/Documents/JK/GitHub/jignesh-softuvo/infertalent-api/fixture/", "new_cities.json"), encoding="utf8")
# city_data = json.load(f1)
# for i in city_data:
#     print(i["id"], i["name"], i["country_id"], i["state_id"])
#     c = Country.objects.get(id=i["country_id"])
#     s = State.objects.get(id=i["state_id"])
#     city = City.objects.create(id=i["id"], name=i["name"], country=c, state=s)
#     print(city)

# states
# f1 = open(os.path.join("/home/softuvo/Documents/JK/GitHub/jignesh-softuvo/infertalent-api/fixture/", "new_states.json"), encoding="utf8")
# state_data = json.load(f1)
# for i in state_data:
#     print(i["id"], i["name"], i["country_id"])
#     a = Country.objects.get(id=i["country_id"])
#     # print(a)
#     z = State.objects.create(id=i["id"], name=i["name"], country=a)
#     print(z)

# country
# f1 = open(os.path.join("/home/softuvo/Documents/JK/GitHub/jignesh-softuvo/infertalent-api/fixture/", "new_countries.json"), encoding="utf8")
# state_data = json.load(f1)
# for i in state_data:
#     # print(i["id"], i["name"], i["iso2"], i["iso3"], i["phone_code"], i["capital"], i["currency"])
#     z = Country.objects.create(
#         id=i["id"], name=i["name"], iso2=i["iso2"], iso3=i["iso3"], phone_code=i["phone_code"], capital=i["capital"], currency=i["currency"]
#     )
# print(z)
