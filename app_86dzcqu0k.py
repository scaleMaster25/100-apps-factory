import requests

def fetch_bitcoin_price():
    """
    Fetches the current price of Bitcoin in USD from the CoinGecko API.
    
    Returns:
        float: The current price of Bitcoin in USD.
    
    Raises:
        Exception: If there is an error fetching the data.
    """
    # API endpoint for fetching Bitcoin price in USD
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    
    try:
        # Make the API request
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the JSON response
        data = response.json()
        
        # Extract the Bitcoin price in USD
        bitcoin_price = data['bitcoin']['usd']
        
        return bitcoin_price
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"Error fetching Bitcoin price: {e}")

if __name__ == "__main__":
    try:
        price = fetch_bitcoin_price()
        print(f"The current price of Bitcoin is: ${price}")
    except Exception as e:
        print(e)