"""Country / city / region lookup for free-text location strings.

ATS boards report location as prose, not codes. Real examples from one probe:

    "Madrid"            "Barcelona, Spain"     "Remote, United Kingdom"
    "Spain"             "Arlington, VA"        "Remote, Canada; Remote, US"

So: split, look for a country name, fall back to a city, fall back to a US
state code. Anything unrecognised stays UNKNOWN rather than being guessed —
a wrong country silently moves a job into the wrong quota bucket.
"""

from __future__ import annotations

import re

from .models import Region, norm_text

#: Region EU covers EU27 + EEA + Switzerland + UK. The UK is not in the EU and
#: has its own visa regime, but it serves the same "work in Europe" goal; the
#: visa difference is handled by the scoring signals, not by the bucket.
EU_COUNTRIES = frozenset(
    {
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",  # EU27
        "IS",
        "LI",
        "NO",
        "CH",  # EEA + Switzerland
        "GB",  # UK
    }
)

#: Normalised country name -> ISO 3166-1 alpha-2. Local spellings included
#: because Spanish boards write "España" and Turkish ones write "Türkiye".
COUNTRY_BY_NAME: dict[str, str] = {}


def _register(code: str, *names: str) -> None:
    for name in names:
        COUNTRY_BY_NAME[norm_text(name)] = code


_register("ES", "Spain", "España", "Espana", "Espanya", "ES")
_register("SE", "Sweden", "Sverige", "SE")
_register("TR", "Turkey", "Türkiye", "Turkiye", "Turkey (Türkiye)", "TR")
_register("NL", "Netherlands", "The Netherlands", "Holland", "Nederland", "NL")
_register("DE", "Germany", "Deutschland", "DE")
_register("PT", "Portugal", "PT")
_register("IE", "Ireland", "Republic of Ireland", "IE")
_register("PL", "Poland", "Polska", "PL")
_register("FR", "France", "FR")
_register("IT", "Italy", "Italia", "IT")
_register("BE", "Belgium", "België", "Belgique", "BE")
_register("AT", "Austria", "Österreich", "AT")
_register("DK", "Denmark", "Danmark", "DK")
_register("FI", "Finland", "Suomi", "FI")
_register("NO", "Norway", "Norge", "NO")
_register("CH", "Switzerland", "Schweiz", "Suisse", "CH")
_register("CZ", "Czechia", "Czech Republic", "CZ")
_register("GR", "Greece", "Hellas", "GR")
_register("RO", "Romania", "România", "RO")
_register("HU", "Hungary", "Magyarország", "HU")
_register("BG", "Bulgaria", "BG")
_register("HR", "Croatia", "Hrvatska", "HR")
_register("SK", "Slovakia", "SK")
_register("SI", "Slovenia", "SI")
_register("EE", "Estonia", "EE")
_register("LV", "Latvia", "LV")
_register("LT", "Lithuania", "LT")
_register("LU", "Luxembourg", "LU")
_register("MT", "Malta", "MT")
_register("CY", "Cyprus", "CY")
_register("IS", "Iceland", "IS")
_register("GB", "United Kingdom", "UK", "Great Britain", "England", "Scotland", "Wales", "GB")
_register("US", "United States", "United States of America", "USA", "US", "U.S.")
_register("CA", "Canada", "CA")
_register("MX", "Mexico", "México", "MX")
_register("BR", "Brazil", "Brasil", "BR")
_register("AR", "Argentina", "AR")
_register("CL", "Chile", "CL")
_register("CO", "Colombia", "CO")
_register("PE", "Peru", "Perú", "PE")
_register("UY", "Uruguay", "UY")
_register("IN", "India", "IN")
_register("SG", "Singapore", "SG")
_register("JP", "Japan", "JP")
_register("AU", "Australia", "AU")
_register("NZ", "New Zealand", "NZ")
_register("IL", "Israel", "IL")
_register("AE", "United Arab Emirates", "UAE", "AE")
_register("BH", "Bahrain", "BH")
_register("QA", "Qatar", "QA")
_register("SA", "Saudi Arabia", "KSA", "SA")
_register("KW", "Kuwait", "KW")
_register("OM", "Oman", "OM")
_register("ZA", "South Africa", "ZA")
_register("EG", "Egypt", "EG")
_register("NG", "Nigeria", "NG")
_register("KE", "Kenya", "KE")
_register("PH", "Philippines", "PH")
_register("ID", "Indonesia", "ID")
_register("VN", "Vietnam", "VN")
_register("TH", "Thailand", "TH")
_register("MY", "Malaysia", "MY")
_register("KR", "South Korea", "Korea", "KR")
_register("CN", "China", "CN")
_register("HK", "Hong Kong", "HK")
_register("TW", "Taiwan", "TW")
_register("UA", "Ukraine", "UA")
_register("RS", "Serbia", "RS")
_register("GE", "Georgia (country)", "GE")

#: Normalised city -> country. Deliberately partial: target markets in full,
#: plus the tech hubs that show up often enough to be worth resolving.
CITY_TO_COUNTRY: dict[str, str] = {}


def _cities(code: str, *names: str) -> None:
    for name in names:
        CITY_TO_COUNTRY[norm_text(name)] = code


_cities(
    "ES",
    "Madrid",
    "Barcelona",
    "Valencia",
    "Sevilla",
    "Seville",
    "Bilbao",
    "Zaragoza",
    "Málaga",
    "Malaga",
    "Murcia",
    "Palma",
    "Las Palmas",
    "Alicante",
    "Valladolid",
    "Vigo",
    "Gijón",
    "A Coruña",
    "La Coruña",
    "Granada",
    "Pamplona",
    "San Sebastián",
    "Santander",
    "Salamanca",
)
_cities(
    "TR",
    "Ankara",
    "İstanbul",
    "Istanbul",
    "İzmir",
    "Izmir",
    "Bursa",
    "Antalya",
    "Adana",
    "Konya",
    "Gaziantep",
    "Kocaeli",
    "Eskişehir",
    "Eskisehir",
    "Kayseri",
    "Karabük",
    "Karabuk",
)
_cities(
    "SE",
    "Stockholm",
    "Gothenburg",
    "Göteborg",
    "Malmö",
    "Malmo",
    "Uppsala",
    "Linköping",
    "Lund",
    "Västerås",
)
_cities(
    "NL",
    "Amsterdam",
    "Rotterdam",
    "The Hague",
    "Den Haag",
    "Utrecht",
    "Eindhoven",
    "Delft",
    "Groningen",
)
_cities(
    "DE",
    "Berlin",
    "Munich",
    "München",
    "Hamburg",
    "Frankfurt",
    "Cologne",
    "Köln",
    "Stuttgart",
    "Düsseldorf",
    "Dusseldorf",
    "Leipzig",
    "Dresden",
    "Karlsruhe",
    "Nuremberg",
    "Nürnberg",
)
_cities("PT", "Lisbon", "Lisboa", "Porto", "Braga", "Coimbra", "Aveiro")
_cities("IE", "Dublin", "Cork", "Galway", "Limerick")
_cities(
    "PL",
    "Warsaw",
    "Warszawa",
    "Kraków",
    "Krakow",
    "Wrocław",
    "Wroclaw",
    "Poznań",
    "Poznan",
    "Gdańsk",
    "Gdansk",
    "Łódź",
    "Lodz",
    "Katowice",
)
_cities(
    "FR",
    "Paris",
    "Lyon",
    "Toulouse",
    "Marseille",
    "Bordeaux",
    "Lille",
    "Nantes",
    "Nice",
    "Montpellier",
    "Grenoble",
    "Sophia Antipolis",
)
_cities(
    "IT",
    "Milan",
    "Milano",
    "Rome",
    "Roma",
    "Turin",
    "Torino",
    "Bologna",
    "Naples",
    "Napoli",
    "Florence",
    "Firenze",
)
_cities("BE", "Brussels", "Bruxelles", "Antwerp", "Antwerpen", "Ghent", "Gent", "Leuven")
_cities("AT", "Vienna", "Wien", "Graz", "Linz", "Salzburg")
_cities("DK", "Copenhagen", "København", "Aarhus", "Odense")
_cities("FI", "Helsinki", "Espoo", "Tampere", "Oulu")
_cities("NO", "Oslo", "Bergen", "Trondheim", "Stavanger")
_cities("CH", "Zurich", "Zürich", "Geneva", "Genève", "Basel", "Lausanne", "Bern", "Zug")
_cities("CZ", "Prague", "Praha", "Brno", "Ostrava")
_cities("GR", "Athens", "Athina", "Thessaloniki", "Patras")
_cities("RO", "Bucharest", "București", "Cluj-Napoca", "Cluj", "Timișoara", "Iași")
_cities("HU", "Budapest", "Debrecen", "Szeged")
_cities("BG", "Sofia", "Plovdiv", "Varna", "Burgas")
_cities("HR", "Zagreb", "Split", "Rijeka", "Osijek")
_cities("SK", "Bratislava", "Košice")
_cities("SI", "Ljubljana", "Maribor")
_cities("EE", "Tallinn", "Tartu")
_cities("LV", "Riga", "Rīga")
_cities("LT", "Vilnius", "Kaunas")
_cities("LU", "Luxembourg City")
_cities("MT", "Valletta", "Sliema")
_cities("CY", "Nicosia", "Limassol")
_cities("IS", "Reykjavik", "Reykjavík")
_cities(
    "GB",
    "London",
    "Manchester",
    "Edinburgh",
    "Bristol",
    "Cambridge",
    "Birmingham",
    "Leeds",
    "Glasgow",
    "Oxford",
    "Belfast",
    "Sheffield",
    "Newcastle",
    "Nottingham",
    "Reading",
    "Brighton",
)
_cities(
    "US",
    "New York",
    "NYC",
    "San Francisco",
    "Seattle",
    "Austin",
    "Boston",
    "Chicago",
    "Los Angeles",
    "Denver",
    "Atlanta",
    "Portland",
    "Miami",
    "San Diego",
    "Dallas",
    "Houston",
    "Washington DC",
    "Washington, DC",
    "Philadelphia",
    "Phoenix",
    "Minneapolis",
    "Detroit",
    "Pittsburgh",
    "Salt Lake City",
    "Arlington",
    "San Jose",
    "Palo Alto",
    "Mountain View",
    "Sunnyvale",
    "Santa Clara",
    "Menlo Park",
    "Cupertino",
    "Redmond",
    "Bellevue",
    "Raleigh",
    "Durham",
    "Charlotte",
    "Nashville",
    "Columbus",
)
_cities(
    "CA",
    "Toronto",
    "Vancouver",
    "Montreal",
    "Montréal",
    "Ottawa",
    "Calgary",
    "Edmonton",
    "Waterloo",
    "Quebec City",
)
_cities(
    "IN",
    "Bangalore",
    "Bengaluru",
    "Mumbai",
    "Delhi",
    "New Delhi",
    "Hyderabad",
    "Chennai",
    "Pune",
    "Gurgaon",
    "Gurugram",
    "Noida",
    "Kolkata",
    "Ahmedabad",
    "Jaipur",
)
_cities(
    "BR",
    "São Paulo",
    "Sao Paulo",
    "Rio de Janeiro",
    "Belo Horizonte",
    "Porto Alegre",
    "Curitiba",
    "Brasília",
    "Recife",
    "Florianópolis",
)
_cities("AR", "Buenos Aires", "Córdoba", "Rosario", "Mendoza")
_cities("CL", "Santiago", "Santiago de Chile", "Valparaíso")
_cities("CO", "Bogotá", "Bogota", "Medellín", "Medellin", "Cali", "Barranquilla")
_cities("PE", "Lima", "Arequipa")
_cities("UY", "Montevideo")
_cities("MX", "Mexico City", "Ciudad de México", "CDMX", "Guadalajara", "Monterrey")
_cities("SG", "Singapore")
_cities("JP", "Tokyo", "Osaka", "Kyoto", "Yokohama")
_cities("AU", "Sydney", "Melbourne", "Brisbane", "Perth", "Canberra", "Adelaide")
_cities("NZ", "Auckland", "Wellington", "Christchurch")
_cities("IL", "Tel Aviv", "Tel Aviv-Yafo", "Jerusalem", "Haifa", "Herzliya")
_cities("AE", "Dubai", "Abu Dhabi")
_cities("BH", "Bahrain", "Manama")
_cities("QA", "Doha")
_cities("SA", "Riyadh", "Jeddah", "Mecca", "Medina", "Dammam", "Dhahran")
_cities("KW", "Kuwait City")
_cities("OM", "Muscat")
_cities("ZA", "Cape Town", "Johannesburg", "Durban", "Pretoria")
_cities("PL", "Rzeszów", "Lublin", "Białystok")
_cities("UA", "Kyiv", "Kiev", "Lviv", "Kharkiv", "Odesa")
_cities("RS", "Belgrade", "Beograd", "Novi Sad", "Niš")
_cities("PH", "Manila", "Cebu", "Makati", "Taguig")
_cities("ID", "Jakarta", "Bandung", "Surabaya")
_cities("VN", "Ho Chi Minh City", "Hanoi", "Da Nang")
_cities("TH", "Bangkok", "Chiang Mai")
_cities("MY", "Kuala Lumpur", "Penang")
_cities("KR", "Seoul", "Busan")
_cities("CN", "Beijing", "Shanghai", "Shenzhen", "Guangzhou", "Hangzhou")
_cities("HK", "Hong Kong")
_cities("TW", "Taipei")
_cities("EG", "Cairo", "Alexandria")
_cities("NG", "Lagos", "Abuja")
_cities("KE", "Nairobi")
_cities("GE", "Tbilisi")

#: "Arlington, VA" and "San Francisco, CA" are US without naming the country.
US_STATE_CODES = frozenset(
    [
        "AL",
        "AK",
        "AZ",
        "AR",
        "CA",
        "CO",
        "CT",
        "DE",
        "FL",
        "GA",
        "HI",
        "ID",
        "IL",
        "IN",
        "IA",
        "KS",
        "KY",
        "LA",
        "ME",
        "MD",
        "MA",
        "MI",
        "MN",
        "MS",
        "MO",
        "MT",
        "NE",
        "NV",
        "NH",
        "NJ",
        "NM",
        "NY",
        "NC",
        "ND",
        "OH",
        "OK",
        "OR",
        "PA",
        "RI",
        "SC",
        "SD",
        "TN",
        "TX",
        "UT",
        "VT",
        "VA",
        "WA",
        "WV",
        "WI",
        "WY",
        "DC",
    ]
)

#: Canadian provinces, same problem: "Toronto, ON".
CA_PROVINCE_CODES = frozenset(
    ["AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"]
)


def country_from_name(text: str | None) -> str | None:
    """Resolve one location fragment to an ISO country code."""
    if not text:
        return None
    key = norm_text(text)
    if not key:
        return None
    if key in COUNTRY_BY_NAME:
        return COUNTRY_BY_NAME[key]
    if key in CITY_TO_COUNTRY:
        return CITY_TO_COUNTRY[key]

    raw = text.strip().upper()
    if raw in US_STATE_CODES:
        return "US"
    if raw in CA_PROVINCE_CODES:
        return "CA"
    return None


def city_from_name(text: str | None) -> str | None:
    """Return the fragment if it is a city we know, else None."""
    if not text:
        return None
    return text.strip() if norm_text(text) in CITY_TO_COUNTRY else None


def country_from_location(text: str | None) -> str | None:
    """Resolve a whole free-text location, not just one fragment.

    `country_from_name` matches a single name: "Berlin" resolves, "Ankara,
    Türkiye" does not. Real sources write the compound form — "New York, NY",
    "United Kingdom, Spain, Dubai", "Hawthorne, CA (Los Angeles)" — so the
    string is tried whole first, then split on the separators publishers use.

    Fragments are read left to right: the first resolvable one is where the
    employer led, which is the closest thing to a primary location a
    multi-location line gives.
    """
    if not text:
        return None
    whole = country_from_name(text)
    if whole:
        return whole
    for part in re.split(r"[,/()|·—–-]", text):
        part = part.strip()
        if not part:
            continue
        # A state code beats a country of the same name: "CA" after a US city
        # is California, not Canada.
        if part.upper() in US_STATE_CODES:
            return "US"
        if part.upper() in CA_PROVINCE_CODES:
            return "CA"
        found = country_from_name(part)
        if found:
            return found
    return None


def region_for(country: str | None) -> Region:
    if not country:
        return Region.UNKNOWN
    code = country.upper()
    if code == "TR":
        return Region.TR
    if code in EU_COUNTRIES:
        return Region.EU
    return Region.OTHER
