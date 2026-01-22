import requests

def fetch_bitcoin_price():
    """
    Fetches the current price of Bitcoin from the CoinGecko API.
    
    Returns:
        float: The current price of Bitcoin in USD.
        None: If an error occurs during the fetch.
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        bitcoin_price = data.get("bitcoin", {}).get("usd")
        
        if bitcoin_price is not None:
            return bitcoin_price
        else:
            print("Error: Bitcoin price data not found in the response.")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Bitcoin price: {e}")
        return None

if __name__ == "__main__":
    price = fetch_bitcoin_price()
    if price is not None:
        print(f"The current price of Bitcoin is ${price:.2f}")