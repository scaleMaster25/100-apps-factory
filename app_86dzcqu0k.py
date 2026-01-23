import requests

def fetch_bitcoin_price():
    """
    Fetches the current price of Bitcoin from the CoinGecko API.

    Returns:
        float: The current price of Bitcoin in USD.

    Raises:
        Exception: If the API request fails or the response is invalid.
    """
    # CoinGecko API endpoint for Bitcoin price
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
    
    try:
        # Make the API request
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the JSON response
        data = response.json()
        
        # Extract the Bitcoin price in USD
        bitcoin_price = data.get("bitcoin", {}).get("usd")
        
        if bitcoin_price is None:
            raise Exception("Failed to retrieve Bitcoin price from the response.")
        
        return bitcoin_price
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {e}")
    except ValueError as e:
        raise Exception(f"Failed to decode JSON response: {e}")

def main():
    try:
        # Fetch and print the current Bitcoin price
        price = fetch_bitcoin_price()
        print(f"Current Bitcoin Price: ${price}")
    except Exception as e:
        raise Exception(f"Error: {e}")

if __name__ == "__main__":
    main()