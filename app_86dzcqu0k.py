import requests
import sys


def fetch_bitcoin_price():
    """
    Fetches the current price of Bitcoin in USD from the CoinGecko API.

    Returns:
        float: The current price of Bitcoin in USD.
    
    Raises:
        SystemExit: If the API request fails or the response is invalid.
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

        if "bitcoin" not in data or "usd" not in data["bitcoin"]:
            raise ValueError("Invalid response format from CoinGecko API")

        return data["bitcoin"]["usd"]

    except requests.exceptions.RequestException as e:
        raise SystemExit(f"Failed to fetch Bitcoin price: {e}")
    except ValueError as e:
        raise SystemExit(f"Error processing API response: {e}")


if __name__ == "__main__":
    try:
        price = fetch_bitcoin_price()
        print(f"Current Bitcoin price: ${price:,.2f} USD")
    except SystemExit as e:
        print(e)
        sys.exit(1)