"""Plaid integration for automatic account syncing."""
import os
from typing import Dict, List, Optional
import requests
from datetime import datetime, timedelta
import pandas as pd
from services.security import SecureStorage, validate_api_key


class PlaidClient:
    """
    Plaid API client for bank and brokerage account integration.

    Setup:
    1. Sign up at https://plaid.com/
    2. Get API keys from Plaid Dashboard
    3. Start with Sandbox environment for testing
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        secret: Optional[str] = None,
        environment: str = 'sandbox'
    ):
        """
        Initialize Plaid client.

        Args:
            client_id: Plaid client ID
            secret: Plaid secret key
            environment: 'sandbox', 'development', or 'production'
        """
        self.client_id = client_id or os.getenv('PLAID_CLIENT_ID')
        self.secret = secret or os.getenv('PLAID_SECRET')
        self.environment = environment

        # API endpoints by environment
        self.base_urls = {
            'sandbox': 'https://sandbox.plaid.com',
            'development': 'https://development.plaid.com',
            'production': 'https://production.plaid.com'
        }

        self.base_url = self.base_urls.get(environment, self.base_urls['sandbox'])

        # Validate credentials
        if self.client_id and self.secret:
            if not validate_api_key(self.secret, 'plaid'):
                raise ValueError("Invalid Plaid API key format")

    def create_link_token(self, user_id: str) -> Dict:
        """
        Create Link token for Plaid Link initialization.

        Args:
            user_id: Unique user identifier

        Returns:
            Dictionary with link_token
        """
        url = f"{self.base_url}/link/token/create"

        payload = {
            'client_id': self.client_id,
            'secret': self.secret,
            'user': {
                'client_user_id': user_id
            },
            'client_name': 'Portfolio Dashboard',
            'products': ['investments', 'transactions'],
            'country_codes': ['US'],
            'language': 'en',
            'webhook': '',  # Optional: webhook URL for updates
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    def exchange_public_token(self, public_token: str) -> Dict:
        """
        Exchange public token for access token.

        Args:
            public_token: Public token from Plaid Link

        Returns:
            Dictionary with access_token and item_id
        """
        url = f"{self.base_url}/item/public_token/exchange"

        payload = {
            'client_id': self.client_id,
            'secret': self.secret,
            'public_token': public_token
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    def get_accounts(self, access_token: str) -> List[Dict]:
        """
        Get account information.

        Args:
            access_token: Plaid access token

        Returns:
            List of account dictionaries
        """
        url = f"{self.base_url}/accounts/get"

        payload = {
            'client_id': self.client_id,
            'secret': self.secret,
            'access_token': access_token
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get('accounts', [])

    def get_investment_holdings(self, access_token: str) -> Dict:
        """
        Get investment holdings from brokerage accounts.

        Args:
            access_token: Plaid access token

        Returns:
            Dictionary with holdings and securities info
        """
        url = f"{self.base_url}/investments/holdings/get"

        payload = {
            'client_id': self.client_id,
            'secret': self.secret,
            'access_token': access_token
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()

        return response.json()

    def get_transactions(
        self,
        access_token: str,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        Get transaction history.

        Args:
            access_token: Plaid access token
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of transactions
        """
        url = f"{self.base_url}/transactions/get"

        payload = {
            'client_id': self.client_id,
            'secret': self.secret,
            'access_token': access_token,
            'start_date': start_date,
            'end_date': end_date
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get('transactions', [])

    def get_investment_transactions(
        self,
        access_token: str,
        start_date: str,
        end_date: str
    ) -> Dict:
        """
        Get investment transactions (buys, sells, dividends).

        Args:
            access_token: Plaid access token
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dictionary with investment transactions
        """
        url = f"{self.base_url}/investments/transactions/get"

        payload = {
            'client_id': self.client_id,
            'secret': self.secret,
            'access_token': access_token,
            'start_date': start_date,
            'end_date': end_date
        }

        response = requests.post(url, json=payload)
        response.raise_for_status()

        return response.json()


class PlaidPortfolioSync:
    """Sync portfolio data from Plaid to dashboard."""

    def __init__(self, plaid_client: PlaidClient, secure_storage: SecureStorage):
        """
        Initialize portfolio sync.

        Args:
            plaid_client: PlaidClient instance
            secure_storage: SecureStorage for access tokens
        """
        self.plaid = plaid_client
        self.storage = secure_storage

    def sync_holdings_to_portfolio(
        self,
        access_token: str,
        account_filter: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Sync holdings from Plaid to portfolio format.

        Args:
            access_token: Plaid access token
            account_filter: Optional list of account IDs to include

        Returns:
            DataFrame with portfolio positions
        """
        # Get holdings
        holdings_data = self.plaid.get_investment_holdings(access_token)

        holdings = holdings_data.get('holdings', [])
        securities = {s['security_id']: s for s in holdings_data.get('securities', [])}

        portfolio_positions = []

        for holding in holdings:
            # Filter by account if specified
            if account_filter and holding['account_id'] not in account_filter:
                continue

            security_id = holding['security_id']
            security = securities.get(security_id, {})

            # Map to portfolio format
            position = {
                'symbol': security.get('ticker_symbol', 'UNKNOWN'),
                'name': security.get('name', ''),
                'shares': holding.get('quantity', 0),
                'current_price': holding.get('institution_price', 0),
                'current_value': holding.get('institution_value', 0),
                'cost_basis': holding.get('cost_basis', 0),
                'account_id': holding['account_id'],
                'security_type': security.get('type', 'equity'),
                'last_updated': datetime.now().isoformat()
            }

            # Calculate purchase price (approximate)
            if position['shares'] > 0 and position['cost_basis'] > 0:
                position['purchase_price'] = position['cost_basis'] / position['shares']
            else:
                position['purchase_price'] = position['current_price']

            portfolio_positions.append(position)

        return pd.DataFrame(portfolio_positions)

    def sync_transactions_to_history(
        self,
        access_token: str,
        days_back: int = 90
    ) -> pd.DataFrame:
        """
        Sync transaction history.

        Args:
            access_token: Plaid access token
            days_back: Number of days of history to sync

        Returns:
            DataFrame with transaction history
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Get investment transactions
        trans_data = self.plaid.get_investment_transactions(
            access_token,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d')
        )

        transactions = trans_data.get('investment_transactions', [])
        securities = {s['security_id']: s for s in trans_data.get('securities', [])}

        trans_list = []

        for trans in transactions:
            security_id = trans.get('security_id')
            security = securities.get(security_id, {})

            trans_list.append({
                'date': trans['date'],
                'symbol': security.get('ticker_symbol', 'UNKNOWN'),
                'type': trans['type'],  # buy, sell, dividend, etc.
                'quantity': trans.get('quantity', 0),
                'price': trans.get('price', 0),
                'amount': trans.get('amount', 0),
                'fees': trans.get('fees', 0),
                'account_id': trans['account_id'],
                'name': trans.get('name', '')
            })

        return pd.DataFrame(trans_list)

    def calculate_portfolio_from_transactions(
        self,
        transactions_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate current portfolio from transaction history.

        Args:
            transactions_df: Transaction history DataFrame

        Returns:
            DataFrame with calculated positions
        """
        if transactions_df.empty:
            return pd.DataFrame()

        positions = {}

        for _, trans in transactions_df.iterrows():
            symbol = trans['symbol']
            trans_type = trans['type']
            quantity = trans.get('quantity', 0)
            price = trans.get('price', 0)

            if symbol not in positions:
                positions[symbol] = {
                    'symbol': symbol,
                    'shares': 0,
                    'total_cost': 0,
                    'transactions': []
                }

            # Update position based on transaction type
            if trans_type in ['buy', 'reinvestment']:
                positions[symbol]['shares'] += quantity
                positions[symbol]['total_cost'] += abs(trans['amount'])
            elif trans_type == 'sell':
                positions[symbol]['shares'] -= quantity
                # Reduce cost basis proportionally
                if positions[symbol]['shares'] > 0:
                    positions[symbol]['total_cost'] *= (positions[symbol]['shares'] / (positions[symbol]['shares'] + quantity))

            positions[symbol]['transactions'].append(trans.to_dict())

        # Convert to DataFrame
        result = []
        for symbol, data in positions.items():
            if data['shares'] > 0:  # Only include current holdings
                avg_price = data['total_cost'] / data['shares'] if data['shares'] > 0 else 0

                result.append({
                    'symbol': symbol,
                    'shares': data['shares'],
                    'purchase_price': avg_price,
                    'cost_basis': data['total_cost'],
                    'num_transactions': len(data['transactions'])
                })

        return pd.DataFrame(result)


def setup_plaid_link_html(link_token: str) -> str:
    """
    Generate HTML for Plaid Link integration.

    Args:
        link_token: Link token from create_link_token

    Returns:
        HTML string for embedding in Streamlit
    """
    html = f"""
    <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
    <button id="link-button">Connect a bank account</button>
    <script>
        const linkHandler = Plaid.create({{
            token: '{link_token}',
            onSuccess: (public_token, metadata) => {{
                // Send public_token to your app server
                console.log('Public token:', public_token);
                console.log('Metadata:', metadata);

                // You would send this to your backend
                // fetch('/exchange_token', {{
                //     method: 'POST',
                //     headers: {{'Content-Type': 'application/json'}},
                //     body: JSON.stringify({{public_token}})
                // }});
            }},
            onExit: (err, metadata) => {{
                if (err != null) {{
                    console.error('Error:', err);
                }}
            }},
        }});

        document.getElementById('link-button').onclick = function() {{
            linkHandler.open();
        }};
    </script>
    """

    return html


# Usage guide
PLAID_SETUP_GUIDE = """
Plaid Integration Setup Guide:

1. SIGN UP FOR PLAID
   - Visit: https://dashboard.plaid.com/signup
   - Create account (free for development)
   - Verify email

2. GET API CREDENTIALS
   - Go to Team Settings > Keys
   - Copy your client_id and secrets
   - Start with Sandbox keys for testing

3. CONFIGURE ENVIRONMENT
   Add to .env file:
   ```
   PLAID_CLIENT_ID=your_client_id_here
   PLAID_SECRET=your_sandbox_secret_here
   PLAID_ENVIRONMENT=sandbox
   ```

4. INSTALL PLAID LIBRARY
   ```bash
   pip install plaid-python
   ```

5. TEST CONNECTION
   ```python
   from services.plaid_integration import PlaidClient

   client = PlaidClient(
       client_id='your_client_id',
       secret='your_secret',
       environment='sandbox'
   )

   # Create link token
   link_token_response = client.create_link_token(user_id='user_123')
   print(link_token_response)
   ```

6. INTEGRATE PLAID LINK
   - Use setup_plaid_link_html() to generate link button
   - User clicks button → selects bank → authenticates
   - Receive public_token → exchange for access_token
   - Store access_token securely

7. SYNC DATA
   ```python
   from services.plaid_integration import PlaidPortfolioSync

   sync = PlaidPortfolioSync(client, secure_storage)

   # Sync holdings
   holdings_df = sync.sync_holdings_to_portfolio(access_token)

   # Sync transactions
   trans_df = sync.sync_transactions_to_history(access_token)
   ```

8. PRODUCTION CHECKLIST
   - Switch to production environment
   - Use production API keys
   - Implement webhook handling
   - Add error handling and retry logic
   - Set up monitoring

SUPPORTED INSTITUTIONS:
   - Major brokerages (Fidelity, Vanguard, Charles Schwab, etc.)
   - Banks with investment accounts
   - Robinhood, E*TRADE, TD Ameritrade
   - 12,000+ financial institutions total

PRICING:
   - Development: Free
   - Production: Pay-as-you-go pricing
   - See: https://plaid.com/pricing/
"""
