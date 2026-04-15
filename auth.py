import streamlit as st
import requests
import urllib.parse
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

def login():
    if "user_email" not in st.session_state:
        st.session_state["user_email"] = None
        
    if st.session_state["user_email"]:
        return st.session_state["user_email"]
        
    client_id = st.secrets["oauth"]["client_id"]
    client_secret = st.secrets["oauth"]["client_secret"]
    redirect_uri = st.secrets.get("OAUTH_REDIRECT_URI", "http://localhost:8501/")
    
    query_params = st.query_params
    
    # ---------------------------------------------------------
    # STATIC PKCE GENERATOR (Bypasses Session Wipe)
    import hashlib
    import base64
    # A static 64-character string
    static_verifier = "0123456789012345678901234567890123456789012345678901234567891234"
    challenge_bytes = hashlib.sha256(static_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).rstrip(b'=').decode('utf-8')
    # ---------------------------------------------------------

    if "code" in query_params:
        code = query_params.get("code")
        
        # Step 2: Manually exchange code for token using the static verifier
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
            "code_verifier": static_verifier,  # Satisfy PKCE here
        }
        
        try:
            response = requests.post(token_url, data=data)
            response.raise_for_status() # If it fails, we catch it
            tokens = response.json()
            
            # Step 3: Parse and Verify ID Token via Google library
            user_info = id_token.verify_oauth2_token(
                tokens["id_token"], google_requests.Request(), client_id
            )
            
            st.session_state["user_email"] = user_info.get("email")
            st.query_params.clear()
            st.rerun()
            return st.session_state["user_email"]
        except Exception as e:
            import traceback
            traceback.print_exc()
            st.error(f"Authentication Token Exchange Failed: {response.text if 'response' in locals() else str(e)}")
            return None

    # Step 1: Manually reconstruct Auth request WITH the static code_challenge
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"prompt=consent&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )
    
    # Centered Custom button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h3 style='text-align: center;'>Please Log In to Continue</h3>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="display:flex; justify-content:center;">'
            f'<a href="{auth_url}" target="_self" '
            'style="padding:10px 20px; background-color:#ff4b4b; '
            'color:white; text-decoration:none; border-radius:5px; font-weight:bold; '
            'text-align:center;">Sign in with Google</a>'
            f'</div>', 
            unsafe_allow_html=True
        )
    return None

def logout():
    st.session_state["user_email"] = None
    st.rerun()
