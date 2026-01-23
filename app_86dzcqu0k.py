import requests

def fetch_bitcoin_price():
    """
    Fetches the current price of Bitcoin from the CoinGecko API.

    :return: The current price of Bitcoin in USD.
    :raises Exception: If the API request fails or the response is invalid.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin",
        "vs_currencies": "usd"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        data = response.json()
        if "bitcoin" not in data or "usd" not in data["bitcoin"]:
            raise Exception("Invalid response format from CoinGecko API.")
        
        return data["bitcoin"]["usd"]
    
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch Bitcoin price: {e}")

if __name__ == "__main__":
    try:
        price = fetch_bitcoin_price()
        print(f"The current price of Bitcoin is ${price:.2f} USD")
    except Exception as e:
        raise Exception(f"Error: {e}")