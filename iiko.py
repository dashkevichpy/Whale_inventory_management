"""Functions to interact with the iiko API."""

import logging
import os
from typing import List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()
IIKO_API_KEY = os.getenv("IIKO_API_KEY")
TEST_MODE = os.getenv("TEST_MODE", "False").lower() == "true"
BASE_URL = "https://burgerkit-co.iiko.it:443/resto/api"

def login_iiko() -> str:
    """Return authentication token for iiko API."""
    if TEST_MODE:
        logging.info("TEST_MODE: login_iiko")
        return "test_token"

    url = f"{BASE_URL}/auth?login=kitapi&pass={IIKO_API_KEY}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.text


def logout_iiko(token: str) -> None:
    """Invalidate authentication token."""
    if TEST_MODE:
        logging.info("TEST_MODE: logout_iiko")
        return

    url = f"{BASE_URL}/logout?key={token}"
    requests.get(url, timeout=10)


def get_iiko_average_check_inhouse(
    date_from: str, date_to: str
) -> Optional[List[List[str]]]:
    """Return average check in-house between two dates."""
    if TEST_MODE:
        logging.info(
            "TEST_MODE: get_iiko_average_check_inhouse %s %s", date_from, date_to
        )
        return []

    try:
        token_iiko = login_iiko()
        url = f"{BASE_URL}/v2/reports/olap?key={token_iiko}"
        params = {
            "reportType": "SALES",
            "buildSummary": "false",
            "groupByRowFields": ["RestorauntGroup"],
            "aggregateFields": ["DishDiscountSumInt.average"],
            "filters": {
                "OpenDate.Typed": {
                    "filterType": "DateRange",
                    "periodType": "CUSTOM",
                    "from": f"{date_from}T00:00:00.000",
                    "to": f"{date_to}T00:00:00.000",
                },
                "DeletedWithWriteoff": {
                    "filterType": "IncludeValues",
                    "values": ["NOT_DELETED"],
                },
                "OrderDeleted": {
                    "filterType": "IncludeValues",
                    "values": ["NOT_DELETED"],
                },
                "OrderType": {
                    "filterType": "ExcludeValues",
                    "values": [
                        "Доставка курьером",
                        "Доставка самовывоз",
                        "Доставка Яндекс.Еда",
                    ],
                },
                "PayTypes": {
                    "filterType": "IncludeValues",
                    "values": ["Наличные", "Visa", "SBRF"],
                },
                "Storned": {
                    "filterType": "IncludeValues",
                    "values": ["FALSE"],
                },
                "DiscountPercent": {
                    "filterType": "Range",
                    "from": 0,
                    "to": 1,
                },
            },
        }
        response = requests.post(url, json=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        logout_iiko(token_iiko)

        logging.debug("iiko result: %s", result)
        return result.get("data")
    except requests.RequestException as exc:
        logging.error("get_iiko_average_check_inhouse error %s", exc)
        return None


