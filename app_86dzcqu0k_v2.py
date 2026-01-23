import requests

def get_bitcoin_price():
    """
    Fetches the current price of Bitcoin from the CoinGecko API.

    Returns:
        float: The current price of Bitcoin in USD.

    Raises:
        Exception: If the API request fails or the response is invalid.
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        
        # Check if the response contains the expected data
        if "bitcoin" not in data or "usd" not in data["bitcoin"]:
            raise Exception("Invalid API response format")
        
        return data["bitcoin"]["usd"]
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {e}")

if __name__ == "__main__":
    try:
        price = get_bitcoin_price()
        print(f"Current Bitcoin Price: ${price}")
    except Exception as e:
        raise Exception(f"Failed to fetch Bitcoin price: {e}")