import requests
import sys

def fetch_bitcoin_price():
    """
    Fetches the current price of Bitcoin from the CoinGecko API.
    
    Returns:
        float: The current price of Bitcoin in USD.
    
    Raises:
        requests.exceptions.RequestException: If the API request fails.
        ValueError: If the response data is invalid.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raises an HTTPError for bad responses
        data = response.json()
        
        if "bitcoin" not in data or "usd" not in data["bitcoin"]:
            raise ValueError("Invalid response data format")
        
        return data["bitcoin"]["usd"]
    
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(f"API request failed: {e}")
    except ValueError as e:
        raise ValueError(f"Data parsing error: {e}")

def main():
    """
    Main function to fetch and print the current Bitcoin price.
    """
    try:
        price = fetch_bitcoin_price()
        print(f"Current Bitcoin Price: ${price:,.2f} USD")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()