# Tesla Authentication Guide

This guide explains the Tesla authentication process for TeslaOnTarget.

## Overview

TeslaOnTarget uses OAuth2 authentication through TeslaPy to securely connect to your Tesla account. The authentication token is stored locally and automatically refreshed as needed.

## First-Time Authentication

### Docker Method

1. Run the authentication command:
   ```bash
   ./docker-run.sh auth
   ```

2. You'll see output like:
   ```
   Starting Tesla authentication...
   Use browser to login. Page Not Found will be shown at success.
   Open this URL: https://auth.tesla.com/oauth2/v3/authorize?...
   ```

3. Your browser will open automatically (or copy/paste the URL)

4. Log in with your Tesla account credentials

5. After successful login, you'll see a **"Page Not Found"** error page
   - **This is normal and expected!**
   - The URL will look like: `https://auth.tesla.com/void/callback?code=...`

6. Copy the **ENTIRE URL** from your browser's address bar

7. Paste it back in the terminal when prompted:
   ```
   Enter URL after authentication: [paste here]
   ```

8. If successful, you'll see:
   ```
   ✓ Authentication successful!
   Found 1 vehicle(s):
   - [Vehicle Name] (VIN: ...XXXXX)
   ```

### Traditional Installation

```bash
python3 -m teslaontarget.auth
```

Follow the same steps as above.

## Authentication File Storage

### Docker
- Token stored in Docker volume: `tesla_data:/data/cache.json`
- Persists across container restarts
- Shared between auth and run containers

### Traditional Installation
- Token stored in: `./cache.json`
- Keep this file secure
- Add to .gitignore (already done)

## Troubleshooting

### "Page Not Found" doesn't appear
- Make sure you're logged into the correct Tesla account
- Try using an incognito/private browser window
- Clear browser cookies for tesla.com

### "Authentication failed"
- Ensure you copied the ENTIRE URL including all parameters
- URL should start with `https://auth.tesla.com/void/callback?code=`
- Try the authentication process again

### Multiple Tesla Accounts
- TeslaOnTarget uses the email specified in TESLA_USERNAME
- Ensure you log in with the matching account

### Token Expiration
- Tokens are automatically refreshed by TeslaPy
- If authentication fails after working previously:
  ```bash
  # Docker
  docker volume rm tesla_data
  ./docker-run.sh auth
  
  # Traditional
  rm cache.json
  python3 -m teslaontarget.auth
  ```

### Two-Factor Authentication
- 2FA is supported
- Enter the code when prompted during login
- You may need to approve the login from your Tesla app

## Security Notes

- The authentication token provides access to your vehicle's data
- Never share your `cache.json` file
- Never commit it to version control
- Tokens expire after 45 days but are auto-renewed
- You can revoke access anytime from your Tesla account settings

## Testing Authentication

After successful authentication, test the connection:

```bash
# Docker
./docker-run.sh test

# Traditional
python3 -m teslaontarget --test
```

This will verify the connection and display your vehicle information without starting the TAK feed.