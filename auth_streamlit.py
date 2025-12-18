import streamlit as st
import requests
import urllib.parse
import jwt
import warnings
from auth_config import AuthConfig

warnings.filterwarnings("ignore", category=DeprecationWarning)

class Auth:
    """
    Handles Azure AD B2C Authentication flows including Login, Callback handling, 
    and Logout within a Streamlit application.

    Args:
        None

    Attributes:
        setts (AuthConfig): Configuration and secrets helper.
        client_id (str): OAuth client id retrieved from secrets manager.
        redirect_uri (str): Redirect URI for OAuth callbacks.
        authorization (str): Authorization endpoint URL.
        token_url (str): Token endpoint URL.
        logout_url (str): Logout endpoint URL.

    Example:
        >>> auth = Auth()
        >>> isinstance(auth, Auth)
        True
    """
    def __init__(self):
        """
        Initialize Auth instance with configuration and client credentials.

        Reads environment and secrets via AuthConfig, sets OAuth endpoints and
        logout URL.

        Args:
            None

        Returns:
            None

        Raises:
            botocore.exceptions.ClientError: If retrieving client secret fails.

        Example:
            >>> auth = Auth()
            >>> auth.client_id is not None
            True
        """
        self.setts = AuthConfig()  
        self.client_id=self.setts.get_client_secret("B2C_CLIENT_SECRET")["client_id"]
        self.redirect_uri = self.setts.callback_url
        # Azure B2C endpoints
        self.authorization = self.setts.authorize_url

        self.token_url = self.setts.token_url

        self.logout_url = (
            "https://manonlineservicesintb2c.b2clogin.com/"
            "manonlineservicesintb2c.onmicrosoft.com/"
            "b2c_1a_man_web_susi_dev/oauth2/v2.0/logout"
        )


    def redirect_to_login(self):
        """
        Constructs the Azure B2C authorization URL and redirects the user 
        via a HTML meta-refresh tag.

        Args:
            None

        Returns:
            None

        Example:
            >>> auth = Auth()
            >>> auth.redirect_to_login()  # triggers a redirect in Streamlit
        """
        login_url = (
            f"{self.authorization}"
            f"?response_type=code"
            f"&client_id={self.client_id}"
            f"&redirect_uri={urllib.parse.quote(self.redirect_uri)}"
            f"&scope=openid+email+profile"
        )
        st.experimental_set_query_params()
        st.markdown(
            f"<meta http-equiv='refresh' content='0; url={login_url}'>",
            unsafe_allow_html=True
        )

    def handle_callback(self, code):
        """
        Exchanges the authorization code for an ID token and decodes user info.

        Args:
            code (str): The authorization code received from Azure B2C.

        Returns:
            dict: Parsed user information with keys 'email', 'name', 'sub' on success.
            None: If token exchange or JWT decoding fails.

        Raises:
            requests.exceptions.RequestException: If the token endpoint request fails.
            ValueError: If the response does not contain a valid ID token.

        Example:
            >>> auth = Auth()
            >>> auth.handle_callback("auth_code")
            {'email': 'user@example.com', 'name': 'User Name', 'sub': '...'}
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        #execute POST request to token endpoint
        resp = requests.post(self.token_url, data=data, headers=headers)
        if resp.status_code != 200:
            print("Token exchange failed:", resp.text)
            return None

        tokens = resp.json()
        id_token = tokens.get("id_token")
        if not id_token:
            print("No ID token returned")
            return None

        try:
            decoded = jwt.decode(id_token, options={"verify_signature": False})
        except Exception as e:
            print("JWT decode failed:", e)
            return None

        return {
            "email": decoded.get("email"),
            "name": decoded.get("name"),
            "sub": decoded.get("sub"),
        }

    # Logout
    def logout(self):
        """
        Redirects the user to the Azure B2C logout endpoint.

        Constructs the logout URL with client_id and post-logout redirect and
        triggers a meta-refresh to perform the logout.

        Args:
            None

        Returns:
            None

        Example:
            >>> auth = Auth()
            >>> auth.logout()  # performs logout redirect
        """
        url = (
            f"{self.logout_url}"
            f"?client_id={self.client_id}"
            f"&post_logout_redirect_uri={urllib.parse.quote(self.redirect_uri)}"
        )
        st.experimental_set_query_params()
        st.markdown(
            f"<meta http-equiv='refresh' content='0; url={url}'>",
            unsafe_allow_html=True
        )