"""
Seeds for the comparative auction benchmark.

Contains:
  - tag dictionaries and the request distribution (TAG_WEIGHTS)
  - 30 base company archetypes (a realistic Russian market)
  - functions for building the set of companies and generating volumes/budgets
  - the scenario matrix for the run
"""
from __future__ import annotations
import itertools
import math

# ─── Tag dictionaries ─────────────────────────────────────────────────────────

VOCABS: dict[str, list[str]] = {
    "City": [
        "Moscow", "SPb", "Novosibirsk", "Yekaterinburg", "Kazan",
        "Nizhny_Novgorod", "Samara", "Krasnodar", "Rostov-on-Don", "Ufa",
        "Voronezh", "Perm", "Volgograd", "Krasnoyarsk", "Saratov",
    ],
    "Age": ["18-24", "25-34", "35-44", "45-54", "55+"],
    "Gender": ["M", "F"],
    "Device": ["mobile", "desktop", "tablet"],
    "Interest": [
        "cartridge", "finances", "property", "fashion", "sport",
        "journey", "technology", "food", "health", "education",
        "fun", "family",
    ],
}

# Tag weights in requests — a realistic Russian internet audience
TAG_WEIGHTS: dict[str, dict[str, float]] = {
    "City": {
        "Moscow": 0.250, "SPb": 0.120, "Novosibirsk": 0.060,
        "Yekaterinburg": 0.060, "Kazan": 0.050, "Nizhny_Novgorod": 0.050,
        "Samara": 0.050, "Krasnodar": 0.060, "Rostov-on-Don": 0.050,
        "Ufa": 0.040, "Voronezh": 0.040, "Perm": 0.040,
        "Volgograd": 0.040, "Krasnoyarsk": 0.050, "Saratov": 0.040,
    },
    "Age": {
        "18-24": 0.15, "25-34": 0.30, "35-44": 0.28,
        "45-54": 0.18, "55+": 0.09,
    },
    "Gender": {"M": 0.48, "F": 0.52},
    "Device": {"mobile": 0.70, "desktop": 0.25, "tablet": 0.05},
    "Interest": {
        "cartridge": 0.07, "finances": 0.09, "property": 0.04,
        "fashion": 0.10, "sport": 0.08, "journey": 0.07,
        "technology": 0.13, "food": 0.14, "health": 0.10,
        "education": 0.03, "fun": 0.11, "family": 0.04,
    },
}

# Convenient sets of cities
_CITY_TOP10 = [
    "Moscow", "SPb", "Novosibirsk", "Yekaterinburg", "Kazan",
    "Nizhny_Novgorod", "Samara", "Krasnodar", "Rostov-on-Don", "Ufa",
]
_CITY_TOP5 = ["Moscow", "SPb", "Novosibirsk", "Yekaterinburg", "Kazan"]
_CITY_METRO = ["Moscow", "SPb"]

# ─── 30 base company archetypes ─────────────────────────────────────────
#
# targets: {vocab: [raw_tag]} — only dictionaries with restrictions.
#   If a vocab is absent from targets, the company accepts ALL tags of this dictionary.
# cpm: value of one impression (nominal rubles/impression)
# priority: priority in the auction (1.0–5.0)
#
# Approximate match_rate values are given in the comments for reference.

BASE_COMPANIES: list[dict] = [
    # ══════ Federal brands — wide reach ══════

    {   # match ≈ 0.60
        "id": "fed_bank", "name": "FederalBank",
        "targets": {"City": _CITY_TOP10, "Age": ["25-34", "35-44", "45-54"]},
        "cpm": 280.0, "priority": 5.0,
    },
    {   # match ≈ 0.72
        "id": "mega_telecom", "name": "MegaTelecom",
        "targets": {"Age": ["18-24", "25-34", "35-44", "45-54"],
                    "Device": ["mobile", "desktop"]},
        "cpm": 160.0, "priority": 4.0,
    },
    {   # match ≈ 0.69
        "id": "online_market", "name": "OnlineMarket",
        "targets": {"Age": ["18-24", "25-34", "35-44"],
                    "Device": ["mobile", "desktop"]},
        "cpm": 140.0, "priority": 3.5,
    },
    {   # match ≈ 0.25
        "id": "food_delivery", "name": "DeliveryBrand",
        "targets": {"City": _CITY_TOP10, "Age": ["18-24", "25-34"],
                    "Device": ["mobile"]},
        "cpm": 90.0, "priority": 3.0,
    },
    {   # match ≈ 0.37
        "id": "auto_max", "name": "AutoBrand",
        "targets": {"Gender": ["M"], "Age": ["25-34", "35-44", "45-54"]},
        "cpm": 250.0, "priority": 4.5,
    },
    {   # match ≈ 0.67
        "id": "insurance_co", "name": "InsuranceBrand",
        "targets": {"City": _CITY_TOP10,
                    "Age": ["25-34", "35-44", "45-54", "55+"]},
        "cpm": 200.0, "priority": 4.0,
    },
    {   # match ≈ 0.41
        "id": "pik_realty", "name": "PropertyBrand",
        "targets": {"City": _CITY_TOP5, "Age": ["25-34", "35-44", "45-54"]},
        "cpm": 320.0, "priority": 4.5,
    },
    {   # match ≈ 0.38
        "id": "moda_retail", "name": "FashionRetail",
        "targets": {"Gender": ["F"], "Age": ["18-24", "25-34", "35-44"]},
        "cpm": 130.0, "priority": 3.0,
    },
    {   # match ≈ 0.55
        "id": "medplus", "name": "HealthPlus",
        "targets": {"Age": ["35-44", "45-54", "55+"]},
        "cpm": 150.0, "priority": 3.5,
    },
    {   # match ≈ 0.15
        "id": "travel_plus", "name": "TravelPlus",
        "targets": {"Age": ["25-34", "35-44"],
                    "Interest": ["journey", "fun", "sport"]},
        "cpm": 200.0, "priority": 3.5,
    },

    # ══════ Mid-size companies — a niche or a region ══════

    {   # match ≈ 0.20
        "id": "region_bank", "name": "RegionalBank",
        "targets": {"City": _CITY_TOP5, "Age": ["25-34", "35-44", "45-54"],
                    "Gender": ["M"]},
        "cpm": 200.0, "priority": 4.0,
    },
    {   # match ≈ 0.15
        "id": "techno_market", "name": "TechMarket",
        "targets": {"Age": ["18-24", "25-34", "35-44"],
                    "Interest": ["technology", "cartridge"]},
        "cpm": 160.0, "priority": 3.5,
    },
    {   # match ≈ 0.13
        "id": "sport_master", "name": "SportsRetail",
        "targets": {"Age": ["18-24", "25-34", "35-44"],
                    "Interest": ["sport", "health"]},
        "cpm": 110.0, "priority": 3.0,
    },
    {   # match ≈ 0.38
        "id": "groc_delivery", "name": "Wiliwali",
        "targets": {"City": _CITY_TOP5, "Device": ["mobile"]},
        "cpm": 80.0, "priority": 3.0,
    },
    {   # match ≈ 0.11
        "id": "kino_sub", "name": "Movie Subscription",
        "targets": {"Age": ["18-24", "25-34"],
                    "Interest": ["fun", "technology"]},
        "cpm": 100.0, "priority": 3.0,
    },
    {   # match ≈ 0.32
        "id": "office_furn", "name": "Office Furniture",
        "targets": {"City": _CITY_TOP10, "Gender": ["M"],
                    "Age": ["25-34", "35-44", "45-54"]},
        "cpm": 120.0, "priority": 3.5,
    },
    {   # match ≈ 0.30
        "id": "detmir", "name": "ChildrenRetail",
        "targets": {"Gender": ["F"], "Age": ["25-34", "35-44"]},
        "cpm": 100.0, "priority": 3.0,
    },
    {   # match ≈ 0.46
        "id": "tur_agency", "name": "Travel Agency",
        "targets": {"City": _CITY_TOP10, "Age": ["25-34", "35-44"]},
        "cpm": 170.0, "priority": 3.5,
    },
    {   # match ≈ 0.28
        "id": "fin_services", "name": "Financial Services",
        "targets": {"City": _CITY_METRO, "Age": ["25-34", "35-44", "45-54"]},
        "cpm": 240.0, "priority": 4.0,
    },
    {   # match ≈ 0.45
        "id": "clothes_chain", "name": "Clothing Network",
        "targets": {"Age": ["18-24", "25-34"]},
        "cpm": 110.0, "priority": 3.0,
    },

    # ══════ Regional and niche ══════

    {   # match ≈ 0.19
        "id": "msk_bank", "name": "MoscowBank",
        "targets": {"City": ["Moscow"], "Age": ["25-34", "35-44", "45-54"]},
        "cpm": 300.0, "priority": 4.5,
    },
    {   # match ≈ 0.27
        "id": "spb_market", "name": "SPbMarket",
        "targets": {"City": _CITY_METRO, "Age": ["18-24", "25-34", "35-44"]},
        "cpm": 130.0, "priority": 3.5,
    },
    {   # match ≈ 0.14
        "id": "ural_telecom", "name": "UralTelecom",
        "targets": {"City": ["Yekaterinburg", "Ufa", "Perm"]},
        "cpm": 140.0, "priority": 3.5,
    },
    {   # match ≈ 0.23
        "id": "volga_retail", "name": "VolgaRetail",
        "targets": {"City": ["Kazan", "Nizhny_Novgorod", "Samara",
                               "Volgograd", "Saratov"]},
        "cpm": 100.0, "priority": 3.0,
    },
    {   # match ≈ 0.15
        "id": "south_service", "name": "YusufService",
        "targets": {"City": ["Krasnodar", "Rostov-on-Don", "Voronezh"]},
        "cpm": 110.0, "priority": 3.0,
    },
    {   # match ≈ 0.11
        "id": "youth_plus", "name": "Youth Plus",
        "targets": {"Age": ["18-24"], "Device": ["mobile"]},
        "cpm": 80.0, "priority": 2.5,
    },
    {   # match ≈ 0.12
        "id": "biz_profi", "name": "BusinessProfi",
        "targets": {"City": _CITY_TOP5, "Gender": ["M"],
                    "Age": ["35-44", "45-54"]},
        "cpm": 280.0, "priority": 4.0,
    },
    {   # match ≈ 0.11
        "id": "lux_moda", "name": "LuxMode",
        "targets": {"City": _CITY_METRO, "Gender": ["F"],
                    "Age": ["25-34", "35-44"]},
        "cpm": 400.0, "priority": 5.0,
    },
    {   # match ≈ 0.43
        "id": "health_plus", "name": "Health Plus",
        "targets": {"City": _CITY_TOP10, "Age": ["35-44", "45-54", "55+"]},
        "cpm": 160.0, "priority": 3.5,
    },
    {   # match ≈ 0.46
        "id": "pet_store", "name": "Home Pets",
        "targets": {"City": _CITY_TOP10, "Age": ["25-34", "35-44"]},
        "cpm": 90.0, "priority": 3.0,
    },

    # ══════ Intricate multidimensional targetings (3–4 dictionaries) ══════

    {   # match ≈ 0.054  (top10 × 25–54 × finance)
        "id": "invest_platform", "name": "Investment Platform",
        "targets": {"City": _CITY_TOP10, "Age": ["25-34", "35-44", "45-54"],
                    "Interest": ["finances"]},
        "cpm": 380.0, "priority": 5.0,
    },
    {   # match ≈ 0.019  (metro × F × 25–44 × travel+fashion)
        "id": "lux_travel", "name": "Luxtravel",
        "targets": {"City": _CITY_METRO, "Gender": ["F"], "Age": ["25-34", "35-44"],
                    "Interest": ["journey", "fashion"]},
        "cpm": 350.0, "priority": 4.5,
    },
    {   # match ≈ 0.043  (top10 × 35+ × health)
        "id": "online_pharma", "name": "Online Pharmacy",
        "targets": {"City": _CITY_TOP10, "Age": ["35-44", "45-54", "55+"],
                    "Interest": ["health"]},
        "cpm": 130.0, "priority": 3.0,
    },
    {   # match ≈ 0.025  (18–24 × mobile × entertainment+technology)
        "id": "game_sub", "name": "GameSubscription",
        "targets": {"Age": ["18-24"], "Device": ["mobile"],
                    "Interest": ["fun", "technology"]},
        "cpm": 75.0, "priority": 2.5,
    },
    {   # match ≈ 0.008  (top5 × M × 35–54 × auto) — ultra-premium
        "id": "prem_auto", "name": "PremiumAuto",
        "targets": {"City": _CITY_TOP5, "Gender": ["M"], "Age": ["35-44", "45-54"],
                    "Interest": ["cartridge"]},
        "cpm": 500.0, "priority": 5.0,
    },
    {   # match ≈ 0.072  (18–34 × technology+education)
        "id": "code_school", "name": "Code School",
        "targets": {"Age": ["18-24", "25-34"],
                    "Interest": ["technology", "education"]},
        "cpm": 120.0, "priority": 3.0,
    },
    {   # match ≈ 0.022  (top10 × mobile × 18–34 × finance)
        "id": "fintech_card", "name": "fintechkarta",
        "targets": {"City": _CITY_TOP10, "Device": ["mobile"],
                    "Age": ["18-24", "25-34"], "Interest": ["finances"]},
        "cpm": 260.0, "priority": 4.0,
    },
    {   # match ≈ 0.047  (F × 18–34 × fashion+health)
        "id": "eco_fashion", "name": "EcoMode",
        "targets": {"Gender": ["F"], "Age": ["18-24", "25-34"],
                    "Interest": ["fashion", "health"]},
        "cpm": 140.0, "priority": 3.0,
    },
    {   # match ≈ 0.032  (top10 × 25–44 × travel)
        "id": "avia_tickets", "name": "Air Tickets",
        "targets": {"City": _CITY_TOP10, "Age": ["25-34", "35-44"],
                    "Interest": ["journey"]},
        "cpm": 210.0, "priority": 3.5,
    },
    {   # match ≈ 0.018  (metro × M × 25–54 × real estate+finance)
        "id": "mortgage_bank", "name": "Mortgage Bank",
        "targets": {"City": _CITY_METRO, "Gender": ["M"],
                    "Age": ["25-34", "35-44", "45-54"],
                    "Interest": ["property", "finances"]},
        "cpm": 420.0, "priority": 5.0,
    },
]

assert len(BASE_COMPANIES) == 40, "It should be exactly 40 base companies"


def _generate_extra_companies(n_extra: int) -> list[dict]:
    """Generates additional companies for scenarios with a large number of participants."""
    # 14 templates with different targeting specifics (from wide to niche)
    templates = [
        ("Regbank",     (150, 250), 4.0,
         {"Age": ["25-34", "35-44", "45-54"]}),
        ("RegRetail",   ( 80, 150), 3.0,
         {"Device": ["mobile", "desktop"]}),
        ("Regulatory Services",   (100, 180), 3.5,
         {"Age": ["25-34", "35-44"]}),
        ("RegMedia",    ( 70, 130), 2.5,
         {"Interest": ["fun", "technology"]}),
        ("Regmoda",     ( 90, 160), 3.0,
         {"Gender": ["F"], "Age": ["18-24", "25-34"]}),
        ("Regauto",     (180, 280), 4.0,
         {"Gender": ["M"], "Interest": ["cartridge", "sport"]}),
        ("Regeda",      ( 60, 120), 3.0,
         {"Device": ["mobile"]}),
        ("Regfinance",  (200, 320), 4.5,
         {"Age": ["25-34", "35-44", "45-54"], "Interest": ["finances"]}),
        ("Regzdorovie", (110, 190), 3.5,
         {"Age": ["35-44", "45-54", "55+"], "Interest": ["health"]}),
        ("RegTechno",    ( 90, 160), 3.0,
         {"Age": ["18-24", "25-34"], "Interest": ["technology"]}),
        ("RegPutes", (150, 230), 3.5,
         {"Gender": ["F"], "Interest": ["journey", "fashion"]}),
        ("Regsport",    ( 80, 140), 3.0,
         {"Gender": ["M"], "Age": ["18-24", "25-34"], "Interest": ["sport"]}),
        ("Reg Real estate", (250, 380), 4.5,
         {"Age": ["25-34", "35-44"], "Interest": ["property"]}),
        ("Regobraz",    ( 80, 130), 3.0,
         {"Age": ["18-24"], "Device": ["mobile", "desktop"]}),
    ]
    city_pools = [
        ["Moscow"],
        ["SPb"],
        ["Moscow", "SPb"],
        ["Novosibirsk", "Krasnoyarsk"],
        ["Yekaterinburg", "Perm", "Ufa"],
        ["Kazan", "Nizhny_Novgorod", "Samara"],
        ["Krasnodar", "Rostov-on-Don", "Voronezh"],
        ["Volgograd", "Saratov"],
        ["Yekaterinburg"],
        ["Kazan"],
        ["Moscow", "Novosibirsk", "Yekaterinburg"],
        ["SPb", "Krasnodar", "Rostov-on-Don"],
        ["Nizhny_Novgorod", "Perm", "Volgograd"],
        ["Samara", "Ufa", "Saratov"],
    ]

    result = []
    for i in range(n_extra):
        name_tpl, cpm_range, priority_base, extra_targets = templates[i % len(templates)]
        city_pool = city_pools[i % len(city_pools)]
        cpm = cpm_range[0] + (cpm_range[1] - cpm_range[0]) * (i % 7) / 6.0
        targets = {"City": city_pool, **extra_targets}
        result.append({
            "id": f"gen_{i:03d}",
            "name": f"{name_tpl}-{i:02d}",
            "targets": targets,
            "cpm": round(cpm, 1),
            "priority": round(priority_base + 0.1 * (i % 5), 1),
        })
    return result


def build_company_set(count: int) -> list[dict]:
    """Returns a list of `count` companies.

    The first 40 are base archetypes (including 10 with intricate multidimensional targeting).
    The rest are generated from templates. Supported values: any > 0.
    """
    if count <= len(BASE_COMPANIES):
        return BASE_COMPANIES[:count]
    extras = _generate_extra_companies(count - len(BASE_COMPANIES))
    return BASE_COMPANIES + extras


# ─── Computing the expected match rate ──────────────────────────────────────

def compute_match_rate(targets: dict[str, list[str]]) -> float:
    """P(a random request falls into the company's targeting).

    Multiplies the probabilities over each dictionary that has restrictions.
    If a dictionary is not set in targets — the contribution = 1.0 (all tags fit).
    """
    rate = 1.0
    for vocab, raw_tags in targets.items():
        weights = TAG_WEIGHTS.get(vocab, {})
        rate *= sum(weights.get(t, 0.0) for t in raw_tags)
    return rate


# ─── Building scenario-specific ad_data ──────────────────────────────────

# Total capacity (volume) of all companies in the set, as a share of the nominal
# n_requests of the scenario. No longer depends on traffic_type — the same
# set of companies has the same total capacity in all three traffic
# types; instead traffic_type regulates the number of ACTUALLY
# sent requests (see TRAFFIC_REQUEST_FACTORS/actual_request_count).
#
# Intentionally > 1.0: with balanced (requests = 1×n) a capacity reserve
# must remain so that some companies stay slightly under-delivered, while
# most nearly fully deliver the plan (sellout is high, but not 100%).
# If the capacity were <= n_requests, balanced would saturate volume by itself
# and would not differ from excess.
BASE_VOLUME_FACTOR = 1.3

# Multiplier of the number of actually sent requests relative to the nominal
# of the scenario (10k/100k/...). The companies' capacity is fixed, therefore:
#   shortage — requests are half the capacity, volume is not a constraint;
#   balanced — requests are slightly below the capacity (see BASE_VOLUME_FACTOR),
#              fill is high, but not 100%;
#   excess   — requests are almost twice the capacity, volume is exhausted quickly.
TRAFFIC_REQUEST_FACTORS: dict[str, float] = {
    "balanced": 1.0,
    "shortage": 0.5,
    "excess":   2.0,
}


def actual_request_count(n_requests: int, traffic_type: str) -> int:
    """The actual number of requests really run through the engine."""
    return max(1, round(n_requests * TRAFFIC_REQUEST_FACTORS[traffic_type]))


def build_scenario_ads(
    companies: list[dict],
    n_requests: int,
) -> dict[str, dict]:
    """Builds ad_data for a scenario: sets the volume and budget of companies.

    The total capacity of the set ≈ BASE_VOLUME_FACTOR × n_requests (nominal,
    does not depend on traffic_type) and is divided among companies proportionally to
    their match_rate. As a result, with more companies in the set the volume
    of each individual company is smaller, while the total volume of the set stays
    approximately the same for the same n_requests.

    Returns:
        dict[ad_id, {name, targets, cpm, priority, volume, budget, match_rate}]
    """
    match_rates = {comp["id"]: compute_match_rate(comp["targets"]) for comp in companies}
    total_match_rate = sum(match_rates.values()) or 1.0
    total_target_volume = n_requests * BASE_VOLUME_FACTOR

    result = {}
    for comp in companies:
        match_rate = match_rates[comp["id"]]
        volume = max(1, round(total_target_volume * match_rate / total_match_rate))
        budget = volume * comp["cpm"]  # for A3: budget = volume × bid/impression
        result[comp["id"]] = {
            "name": comp["name"],
            "targets": comp["targets"],
            "cpm": comp["cpm"],
            "priority": comp["priority"],
            "volume": volume,
            "budget": budget,
            "match_rate": match_rate,
        }
    return result


# ─── Scenario matrix ─────────────────────────────────────────────────────

COMPANY_COUNTS = [3, 10, 20, 100, 250]
REQUEST_COUNTS = [10_000, 100_000, 1_000_000, 10_000_000]
TRAFFIC_TYPES  = ["balanced", "shortage", "excess"]

# All 5×4×3 = 60 scenarios
SCENARIO_MATRIX: list[tuple[int, int, str]] = list(
    itertools.product(COMPANY_COUNTS, REQUEST_COUNTS, TRAFFIC_TYPES)
)

# ─── Algorithms ────────────────────────────────────────────────────────────

CLASSIC_STRATEGIES = [
    "best_one", "random_one",
    "best_price", "random_price",
    "best_velocity", "random_velocity",
    "best_heuristics", "random_heuristics",
    "best_hybrid_0.2", "best_hybrid_0.4",
    "random_hybrid_0.3", "random_hybrid_0.5", "random_hybrid_0.7",
]

ADWORDS_ALGORITHMS = ["a2_single_valued", "a3_small"]

# Default number of a2/a3 runs depending on the number of requests
DEFAULT_ADWORDS_RUNS: dict[int, int] = {
    10_000:      1000,
    100_000:      300,
    1_000_000:     50,
    10_000_000:    20,
}
