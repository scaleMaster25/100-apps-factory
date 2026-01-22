import requests
import json

def fetch_bitcoin_price():
    """
    Fetches the current price of Bitcoin from the CoinGecko API.
    
    Returns:
        float: The current price of Bitcoin in USD.
        None: If the request fails or the response is invalid.
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
        bitcoin_price = data.get("bitcoin", {}).get("usd")
        
        if bitcoin_price is None:
            print("Error: Bitcoin price not found in the API response.")
            return None
            
        return bitcoin_price
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Bitcoin price: {e}")
        return None

if __name__ == "__main__":
    price = fetch_bitcoin_price()
    if price is not None:
        print(f"Current Bitcoin price: ${price:,.2f}")