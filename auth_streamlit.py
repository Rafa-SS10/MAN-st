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
    """
    def __init__(self):
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
        Exchanges the authorization code for an ID token.
        
        Args:
            code (str): The authorization code received from Azure B2C.
            
        Returns:
            dict: User details (email, name, sub) if successful.
            None: If token exchange or decoding fails.
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