import requests

def fetch_bitcoin_price():
    """Fetch the current price of Bitcoin from the CoinGecko API."""
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    
    try:
        # Send GET request to the CoinGecko API
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the JSON response
        data = response.json()
        bitcoin_price = data['bitcoin']['usd']
        
        # Print the Bitcoin price
        print(f"Current Bitcoin Price: ${bitcoin_price}")
    
    except requests.exceptions.RequestException as e:
        # Handle any errors that occur during the request
        print(f"An error occurred while fetching the Bitcoin price: {e}")

if __name__ == "__main__":
    fetch_bitcoin_price()