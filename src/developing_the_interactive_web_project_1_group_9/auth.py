import os
from auth0_server_python.auth_server.server_client import ServerClient
from auth0_server_python.store import StateStore
from dotenv import load_dotenv
import asyncpg
import psycopg
import json
import secrets
import pickle
from typing import Dict, Any, Optional

load_dotenv()
db_url = os.getenv('DB_URL')

# Credit for memory stores to Auth0 quickstart guides (also it's the starting point for auth.py as a whole)
# Simple in-memory storage for development
# For production, use Redis, PostgreSQL, or other persistent storage
class MemoryStateStore:
    """In-memory state store for session data (development only)"""
    def __init__(self):
        self._data = {}
    
    async def get(self, key, options=None):
        return self._data.get(key)
    
    async def set(self, key, value, options=None):
        self._data[key] = value
    
    async def delete(self, key, options=None):
        self._data.pop(key, None)
    
    async def delete_by_logout_token(self, claims, options=None):
        # For backchannel logout support
        pass

# This class should eventually be the basis for a shared memory transaction store
# suitable for gunicorn.
class MemoryTransactionStore:
    """In-memory transaction store for OAuth flows (development only)"""
    def __init__(self):
        self._data = {}
    
    async def get(self, key, options=None):
        return self._data.get(key)
    
    async def set(self, key, value, options=None):
        self._data[key] = value
    
    async def delete(self, key, options=None):
        self._data.pop(key, None)

# The Docs are HORRIBLE, so I'll explain how this works
# The identifier passed in will be the name of the cookie, not the field it's querying
# The job of set is to store the data as a single encrypted blob, and store it's own generated key in a cookie
# Get's job is to get the WHOLE json and pass it back to auth0 to do what it needs to, using the key so you
# give it the correct user's auth block. In other words, auth0 is not asking you to rummage through the giant
# state object itself, it want the whole state. It's just your job to make sure you're passing the current
# user's state via cookies.
# Initial PostgresStateStore is from auth0 store examples. But it has been heavily modified by yours
# truly as the example code simply doesn't work (and as a bonus they use asyncpg but the code has race
# conditions meaning it will fail... sometimes. Don't we all love non-deterministic bugs?)
class PostgresStateStore(StateStore):
    """
    A stateful store that uses Postgres to store session data.
    The cookie holds just a session_id; the rest of the data is in Postgres.
    """

    def __init__(self, secret: str, dsn: str, cookie_name: str = "_a0_session"):
        super().__init__({"secret": secret})
        self.dsn = dsn  # "postgresql://user:password@host:port/dbname"
        self.cookie_name = cookie_name
        self.pool = None  # We'll initialize a connection pool later.

    async def init_pool(self):
        """Create a connection pool. Call this once on startup."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(dsn=self.dsn)


    async def set(
        self, 
        identifier: str, 
        state: Dict[str, Any], 
        options: Optional[Dict[str, Any]] = None
    ) -> None:
        if not options or "response" not in options:
            raise ValueError("Response object is required for setting a cookie in PostgresStateStore.")
        #print("Set Called:")
        #print("Identifier %s", identifier)
        #print("State:")
        #print(state)
        session_id = secrets.token_urlsafe(190)
        conn = psycopg.connect(db_url)
        cursor = conn.cursor()
        # Optionally encrypt `state`:
        # encrypted_data = self.encrypt(session_id, state)
        # For simplicity, store as JSON
        data = pickle.dumps(state)
        #print("dumped state:")
        #print(data)
        # Insert or update the session
        cursor.execute(
            """
            INSERT INTO auth_sessions(session_id, session_data)
            VALUES(%s, %s)
            ON CONFLICT (session_id) DO UPDATE SET session_data=excluded.session_data
            """,
            (session_id,data)
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Set the cookie containing session_id
        response = options["response"]
        response.set_cookie(
            key=identifier,
            value=session_id,
            httponly=True,
            samesite="None",
            secure=True,
            max_age=86400,  # 1 day example
            path="/"
        )

    async def get(
        self, 
        identifier: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        if not options or "request" not in options:
            raise ValueError("Request object is required to read cookies in PostgresStateStore.")

        #print("Get Called:")
        #print("Identifier %s", identifier)

        request = options["request"]
        session_id = request.cookies.get(identifier)
        if not session_id:
            return None
        #print("Retrived session id: %s", session_id)
        conn = psycopg.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT session_data FROM auth_sessions WHERE session_id = %s", (session_id,))
        row = cursor.fetchone()
        if not row:
            return None
        # If you used encryption, do self.decrypt(...)
        data = pickle.loads(row[0])
        #print("loaded data")
        #print(data)
        conn.commit()
        cursor.close()
        conn.close()
        return data

    async def delete(
        self, 
        identifier: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> None:
        if not options or "response" not in options:
            raise ValueError("Response object is required to clear cookies in PostgresStateStore.")
        
        response = options["response"]
        request = options["request"]
        session_id = request.cookies.get(self.cookie_name)

        if session_id:
            conn = psycopg.connect(db_url)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM auth_sessions WHERE session_id = %s", (session_id,))
            conn.commit()
            cursor.close()
            conn.close()


        response.delete_cookie(self.cookie_name)

    # DO NOT USE!!! Will fix if we end up using this method of logout
    async def delete_by_logout_token(
        self, 
        claims: Dict[str, Any], 
        options: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Backchannel logout: find sessions that match sub/sid and remove them.
        This might require storing sub/sid in the DB row for quick lookups.
        """
        async with self.pool.acquire() as conn:
            # If you store 'sid' or 'user.sub' in a separate column, you can do:
            await conn.execute(
                """
                DELETE FROM auth_sessions
                WHERE (session_data->'internal'->>'sid') = $1
                  AND (session_data->'user'->>'sub') = $2
                """,
                claims.get("sid"),
                claims.get("sub")
            )

# Temporary class while shared memory across gunicorn is not figured out
# Everything here is shortlived, cleanup scripts should be run often
class PostgresTransactionStore(StateStore):
    """
    A stateful store that uses Postgres to store session data.
    The cookie holds just a session_id; the rest of the data is in Postgres.
    """

    def __init__(self, secret: str, dsn: str, cookie_name: str = "_a0_transaction"):
        super().__init__({"secret": secret})
        self.dsn = dsn  # "postgresql://user:password@host:port/dbname"
        self.cookie_name = cookie_name
        self.pool = None  # We'll initialize a connection pool later.

    async def init_pool(self):
        """Create a connection pool. Call this once on startup."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(dsn=self.dsn)


    async def set(
        self, 
        identifier: str, 
        state: Dict[str, Any], 
        options: Optional[Dict[str, Any]] = None
    ) -> None:
        if not options or "response" not in options:
            raise ValueError("Response object is required for setting a cookie in PostgresStateStore.")
        #print("Set Called:")
        #print("Identifier %s", identifier)
        #print("State:")
        #print(state)
        transaction_id = secrets.token_urlsafe(16)
        conn = psycopg.connect(db_url)
        cursor = conn.cursor()
        # Optionally encrypt `state`:
        # encrypted_data = self.encrypt(session_id, state)
        # For simplicity, store as JSON
        data = pickle.dumps(state)
        #print("dumped state:")
        #print(data)
        # Insert or update the session
        cursor.execute(
            """
            INSERT INTO auth_transactions(transaction_id, transaction_data)
            VALUES(%s, %s)
            ON CONFLICT (transaction_id) DO UPDATE SET transaction_data=excluded.transaction_data
            """,
            (transaction_id,data)
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Set the cookie containing session_id
        response = options["response"]
        response.set_cookie(
            key=identifier,
            value=transaction_id,
            httponly=True,
            samesite="None",
            secure=True,
            max_age=86400,  # 1 day example
            path="/"
        )

    async def get(
        self, 
        identifier: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        if not options or "request" not in options:
            raise ValueError("Request object is required to read cookies in PostgresStateStore.")

        #print("Get Called:")
        #print("Identifier %s", identifier)

        request = options["request"]
        transaction_id = request.cookies.get(identifier)
        if not transaction_id:
            return None
        #print("Retrived session id: %s", session_id)
        conn = psycopg.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT transaction_data FROM auth_transactions WHERE transaction_id = %s", (transaction_id,))
        row = cursor.fetchone()
        if not row:
            return None
        # If you used encryption, do self.decrypt(...)
        data = pickle.loads(row[0])
        #print("loaded data")
        #print(data)
        conn.commit()
        cursor.close()
        conn.close()
        return data

    async def delete(
        self, 
        identifier: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> None:
        if not options or "response" not in options:
            raise ValueError("Response object is required to clear cookies in PostgresStateStore.")
        
        response = options["response"]
        request = options["request"]
        transaction_id = request.cookies.get(self.cookie_name)

        if transaction_id:
            conn = psycopg.connect(db_url)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM auth_transactions WHERE transaction_id = %s", (transaction_id,))
            conn.commit()
            cursor.close()
            conn.close()


        response.delete_cookie(self.cookie_name)


# Initialize stores, these can be kept global as they open and close connection
state_store = PostgresStateStore(os.getenv('AUTH0_SECRET'), db_url)
transaction_store = PostgresTransactionStore(os.getenv('AUTH0_SECRET'), db_url)

# Initialize the Auth0 ServerClient inside a function
# Because auth0 is async and thus requires flask to be flask[async]
# We need to attach a new serverclient to the current asyncio object
# Let's play a game, did the docs mention this? (NO, THE ANSWER IS NO)
def init_auth0():
    auth0 = ServerClient(
        domain=os.getenv('AUTH0_DOMAIN'),
        client_id=os.getenv('AUTH0_CLIENT_ID'),
        client_secret=os.getenv('AUTH0_CLIENT_SECRET'),
        secret=os.getenv('AUTH0_SECRET'),
        redirect_uri=os.getenv('AUTH0_REDIRECT_URI'),
        state_store=state_store,
        transaction_store=transaction_store,
        authorization_params={
            'scope': 'openid profile email',
            'audience': os.getenv('AUTH0_AUDIENCE', '')  # Optional: for API access
        }
    )
    return auth0