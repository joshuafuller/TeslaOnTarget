#!/usr/bin/env python3
"""Tesla authentication script to get a fresh token"""

import sys
import webbrowser
from teslapy import Tesla
from .config_handler import Config

def main():
    # Load configuration
    Config.load_from_file()
    
    print("Tesla Authentication for TeslaOnTarget")
    print("=" * 40)
    print(f"Account: {Config.TESLA_USERNAME}")
    print()
    
    # Initialize Tesla API
    tesla = Tesla(Config.TESLA_USERNAME)
    
    # Check if we already have a valid token
    if tesla.authorized:
        print("✓ Already authenticated with valid token!")
        print()
        print("Testing connection...")
        try:
            vehicles = tesla.vehicle_list()
            print(f"✓ Successfully connected! Found {len(vehicles)} vehicle(s):")
            for v in vehicles:
                print(f"  - {v['display_name']} (State: {v.get('state', 'unknown')})")
            print()
            print("Authentication is valid. You can run ./start.sh")
            return
        except Exception as e:
            print(f"✗ Token exists but seems invalid: {e}")
            print("Proceeding with re-authentication...")
    
    print("Starting authentication process...")
    print()
    print("Steps:")
    print("1. A browser window will open to Tesla's login page")
    print("2. Log in with your Tesla account credentials")
    print("3. After login, you'll see a 'Page Not Found' error - this is normal!")
    print("4. Copy the ENTIRE URL from the browser's address bar")
    print("5. Paste it below when prompted")
    print()
    
    # Try to open the browser automatically
    try:
        auth_url = tesla.authorization_url()
        print(f"Opening browser to: {auth_url}")
        webbrowser.open(auth_url)
    except Exception as e:
        print(f"Could not open browser automatically: {e}")
        print("Please manually open this URL in your browser:")
        print(tesla.authorization_url())
    
    print()
    print("After logging in, copy the redirect URL from your browser")
    redirect_url = input("Paste the URL here: ").strip()
    
    try:
        # Fetch token using the redirect URL
        tesla.fetch_token(authorization_response=redirect_url)
        
        print()
        print("✓ Authentication successful!")
        print()
        
        # Test the connection
        vehicles = tesla.vehicle_list()
        print(f"Found {len(vehicles)} vehicle(s):")
        for v in vehicles:
            print(f"  - {v['display_name']} (VIN: ...{v['vin'][-6:]})")
        
        print()
        print("Token saved to cache.json")
        print("You can now run: ./start.sh")
        
    except Exception as e:
        print()
        print(f"✗ Authentication failed: {e}")
        print()
        print("Common issues:")
        print("- Make sure you copied the ENTIRE URL including 'https://'")
        print("- The URL should contain 'code=' parameter")
        print("- Try again if the session expired")

if __name__ == "__main__":
    main()