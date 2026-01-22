import requests

def fetch_bitcoin_price():
    """
    Fetches the current price of Bitcoin from the CoinGecko API.
    
    Returns:
        float: The current price of Bitcoin in USD.
        None: If the request fails or an error occurs.
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx, 5xx)
        data = response.json()
        return data['bitcoin']['usd']
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Bitcoin price: {e}")
        return None

if __name__ == "__main__":
    price = fetch_bitcoin_price()
    if price is not None:
        print(f"The current price of Bitcoin is ${price:.2f} USD.")
    else:
        print("Failed to fetch the Bitcoin price.")