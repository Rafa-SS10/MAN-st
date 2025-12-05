import streamlit as st
import requests
import urllib.parse
import jwt
import warnings
from auth_config import AuthConfig

warnings.filterwarnings("ignore", category=DeprecationWarning)

class Auth:
    def __init__(self):
        self.setts = AuthConfig()  
        self.client_id="md7bnk4kv4m0a5c7iv9ujr6qp"
        self.redirect_uri = self.setts.callback_url
        # Azure B2C endpoints
        self.authorization = self.setts.authorize_url

        self.token_url = self.setts.token_url

        self.logout_url = (
            "https://manonlineservicesintb2c.b2clogin.com/"
            "manonlineservicesintb2c.onmicrosoft.com/"
            "b2c_1a_man_web_susi_dev/oauth2/v2.0/logout"
        )

    # Redirect user to Azure B2C login
    def redirect_to_login(self):
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

    # Callback handler: exchange code for JWT tokens
    def handle_callback(self, code):
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

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