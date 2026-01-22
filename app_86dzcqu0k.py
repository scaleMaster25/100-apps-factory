import requests
import json
from typing import Optional

def fetch_bitcoin_price() -> Optional[float]:
    """
    Fetches the current price of Bitcoin (in USD) from the CoinGecko API.

    Returns:
        Optional[float]: The current Bitcoin price in USD, or None if the request fails.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx, 5xx)
        data = response.json()
        return data["bitcoin"]["usd"]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Bitcoin price: {e}")
        return None
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing API response: {e}")
        return None

if __name__ == "__main__":
    price = fetch_bitcoin_price()
    if price is not None:
        print(f"Current Bitcoin price: ${price:,.2f} USD")
    else:
        print("Failed to fetch Bitcoin price.")