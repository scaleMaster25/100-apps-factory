import requests

def fetch_bitcoin_price():
    """
    Fetches the current price of Bitcoin from the CoinGecko API.
    
    Returns:
        float: The current price of Bitcoin in USD.
    Raises:
        Exception: If the request fails or the response is invalid.
    """
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()
        
        # Extract Bitcoin price from the response
        bitcoin_price = data.get('bitcoin', {}).get('usd')
        
        if bitcoin_price is None:
            raise ValueError("Bitcoin price not found in the response.")
        
        return bitcoin_price
        
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch Bitcoin price: {e}")
    except ValueError as e:
        raise Exception(f"Invalid response data: {e}")

def main():
    try:
        price = fetch_bitcoin_price()
        print(f"The current price of Bitcoin is: ${price:.2f}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()