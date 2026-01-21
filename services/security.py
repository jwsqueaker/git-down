"""Security and encryption for sensitive financial data."""
import os
import hashlib
import secrets
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
import base64
import json
from typing import Dict, Optional, Any
import streamlit as st


class DataEncryption:
    """Encrypt and decrypt sensitive financial data."""

    @staticmethod
    def generate_key_from_password(password: str, salt: bytes = None) -> tuple[bytes, bytes]:
        """
        Generate encryption key from password.

        Args:
            password: User password
            salt: Salt for key derivation (generated if not provided)

        Returns:
            Tuple of (key, salt)
        """
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key, salt

    @staticmethod
    def encrypt_data(data: Any, key: bytes) -> bytes:
        """
        Encrypt data using Fernet symmetric encryption.

        Args:
            data: Data to encrypt (will be JSON serialized)
            key: Encryption key

        Returns:
            Encrypted data
        """
        f = Fernet(key)

        # Convert to JSON string then bytes
        data_str = json.dumps(data)
        data_bytes = data_str.encode()

        encrypted = f.encrypt(data_bytes)
        return encrypted

    @staticmethod
    def decrypt_data(encrypted_data: bytes, key: bytes) -> Any:
        """
        Decrypt data.

        Args:
            encrypted_data: Encrypted bytes
            key: Encryption key

        Returns:
            Decrypted data
        """
        f = Fernet(key)

        decrypted_bytes = f.decrypt(encrypted_data)
        decrypted_str = decrypted_bytes.decode()

        return json.loads(decrypted_str)

    @staticmethod
    def hash_sensitive_field(value: str) -> str:
        """
        One-way hash of sensitive fields (for comparison without storing).

        Args:
            value: Value to hash

        Returns:
            Hexadecimal hash
        """
        return hashlib.sha256(value.encode()).hexdigest()


class SessionSecurity:
    """Manage secure user sessions."""

    @staticmethod
    def generate_session_token() -> str:
        """Generate cryptographically secure session token."""
        return secrets.token_urlsafe(32)

    @staticmethod
    def init_secure_session():
        """Initialize secure session state."""
        if 'session_token' not in st.session_state:
            st.session_state.session_token = SessionSecurity.generate_session_token()

        if 'session_timeout' not in st.session_state:
            import time
            st.session_state.session_timeout = time.time() + 3600  # 1 hour

    @staticmethod
    def check_session_valid() -> bool:
        """Check if session is still valid."""
        import time

        if 'session_timeout' not in st.session_state:
            return False

        return time.time() < st.session_state.session_timeout

    @staticmethod
    def refresh_session():
        """Refresh session timeout."""
        import time
        st.session_state.session_timeout = time.time() + 3600


class SecureStorage:
    """Secure storage for sensitive data."""

    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize secure storage.

        Args:
            encryption_key: Encryption key (generated if not provided)
        """
        self.encryption_key = encryption_key or Fernet.generate_key()
        self.encryptor = DataEncryption()

    def store_credentials(
        self,
        service_name: str,
        credentials: Dict,
        storage_path: str = 'data/encrypted_credentials.bin'
    ):
        """
        Store encrypted credentials.

        Args:
            service_name: Name of service (e.g., 'plaid', 'broker_api')
            credentials: Credentials dictionary
            storage_path: Path to encrypted file
        """
        # Load existing credentials
        try:
            with open(storage_path, 'rb') as f:
                encrypted = f.read()
                all_creds = self.encryptor.decrypt_data(encrypted, self.encryption_key)
        except (FileNotFoundError, Exception):
            all_creds = {}

        # Add new credentials
        all_creds[service_name] = credentials

        # Encrypt and save
        encrypted = self.encryptor.encrypt_data(all_creds, self.encryption_key)

        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        with open(storage_path, 'wb') as f:
            f.write(encrypted)

    def retrieve_credentials(
        self,
        service_name: str,
        storage_path: str = 'data/encrypted_credentials.bin'
    ) -> Optional[Dict]:
        """
        Retrieve encrypted credentials.

        Args:
            service_name: Service name
            storage_path: Path to encrypted file

        Returns:
            Credentials dictionary or None
        """
        try:
            with open(storage_path, 'rb') as f:
                encrypted = f.read()
                all_creds = self.encryptor.decrypt_data(encrypted, self.encryption_key)

            return all_creds.get(service_name)
        except (FileNotFoundError, Exception):
            return None


class SecurityAudit:
    """Security audit logging."""

    @staticmethod
    def log_access(action: str, resource: str, user_id: str = 'anonymous'):
        """
        Log security-relevant actions.

        Args:
            action: Action performed (e.g., 'view_portfolio', 'export_data')
            resource: Resource accessed
            user_id: User identifier
        """
        import time
        from datetime import datetime

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'resource': resource,
            'user_id': user_id,
            'session_token': st.session_state.get('session_token', 'none')
        }

        # Write to audit log
        os.makedirs('data/logs', exist_ok=True)
        log_file = 'data/logs/security_audit.log'

        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    @staticmethod
    def get_recent_activity(limit: int = 50) -> list:
        """
        Get recent security audit entries.

        Args:
            limit: Number of entries to return

        Returns:
            List of audit entries
        """
        log_file = 'data/logs/security_audit.log'

        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()

            # Get last N lines
            recent = lines[-limit:]

            return [json.loads(line) for line in recent]
        except FileNotFoundError:
            return []


def sanitize_input(user_input: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.

    Args:
        user_input: Raw user input
        max_length: Maximum allowed length

    Returns:
        Sanitized input
    """
    # Truncate
    sanitized = user_input[:max_length]

    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '{', '}', ';', '|', '&', '$']
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')

    return sanitized.strip()


def validate_api_key(api_key: str, service: str = 'general') -> bool:
    """
    Validate API key format.

    Args:
        api_key: API key to validate
        service: Service name for service-specific validation

    Returns:
        True if valid format
    """
    if not api_key or len(api_key) < 10:
        return False

    # Check for suspicious patterns
    if any(char in api_key for char in [' ', '\n', '\r', '\t']):
        return False

    # Service-specific validation
    if service == 'plaid':
        # Plaid keys start with specific prefixes
        return api_key.startswith(('sandbox-', 'development-', 'production-'))

    return True


# Security recommendations for deployment
SECURITY_CHECKLIST = """
Security Checklist for Production Deployment:

1. AUTHENTICATION
   ☐ Implement user authentication (OAuth, email/password)
   ☐ Use strong password requirements
   ☐ Enable multi-factor authentication (MFA)
   ☐ Implement session management with timeouts

2. DATA ENCRYPTION
   ☐ Encrypt sensitive data at rest (use DataEncryption)
   ☐ Use HTTPS/SSL for data in transit
   ☐ Store API keys in environment variables, not code
   ☐ Use SecureStorage for credentials

3. ACCESS CONTROL
   ☐ Implement role-based access control (RBAC)
   ☐ Log all data access (use SecurityAudit)
   ☐ Implement rate limiting
   ☐ Validate all user inputs (use sanitize_input)

4. API SECURITY
   ☐ Validate all API keys (use validate_api_key)
   ☐ Use API key rotation
   ☐ Implement request signing
   ☐ Monitor for unusual API usage

5. DATABASE SECURITY
   ☐ Use parameterized queries (SQLAlchemy does this)
   ☐ Implement database backups
   ☐ Encrypt database files
   ☐ Limit database permissions

6. COMPLIANCE
   ☐ Implement data retention policies
   ☐ Add privacy policy
   ☐ Enable data export (GDPR)
   ☐ Implement data deletion on request

7. MONITORING
   ☐ Set up security logging
   ☐ Monitor for suspicious activity
   ☐ Implement alerting for security events
   ☐ Regular security audits

8. DEPLOYMENT
   ☐ Use environment-specific configs
   ☐ Never commit secrets to git
   ☐ Use secrets management (AWS Secrets Manager, etc.)
   ☐ Keep dependencies updated
   ☐ Regular security patches
"""
