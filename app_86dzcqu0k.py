import requests

def fetch_bitcoin_price():
    # CoinGecko API endpoint for Bitcoin price in USD
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': 'bitcoin',
        'vs_currencies': 'usd'
    }
    
    try:
        # Send GET request to the API
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the JSON response
        data = response.json()
        
        # Extract and return the Bitcoin price in USD
        bitcoin_price = data['bitcoin']['usd']
        return bitcoin_price
    
    except requests.exceptions.RequestException as e:
        # Handle exceptions related to the HTTP request
        print(f"Error fetching Bitcoin price: {e}")
        return None

if __name__ == "__main__":
    price = fetch_bitcoin_price()
    if price:
        print(f"Current Bitcoin Price: ${price}")