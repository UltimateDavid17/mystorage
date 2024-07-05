import os
import requests

from flask import Blueprint, render_template, redirect, url_for, session, request, Response
from dotenv import load_dotenv

load_dotenv()

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")

API_BASE_URL = "https://discord.com/api"
AUTHORIZATION_BASE_URL = "https://discord.com/api/oauth2/authorize"
TOKEN_URL = "https://discord.com/api/oauth2/token"

auth_routes = Blueprint('auth_routes', __name__, template_folder='templates')

@auth_routes.route('/login')
def login():
    return redirect(f"{AUTHORIZATION_BASE_URL}?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify")

@auth_routes.route('/callback')
def callback():
    code = request.args.get('code')
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'scope': 'identify'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(TOKEN_URL, data=data, headers=headers)
    response_data = response.json()
    access_token = response_data.get('access_token')

    user_info = requests.get(f"{API_BASE_URL}/users/@me", headers={
        'Authorization': f'Bearer {access_token}'
    }).json()

    session['user'] = user_info
    return redirect(url_for('upload'))

@auth_routes.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@auth_routes.route('/api/avatar.png')
def api_avatar():
    if 'user' not in session:
        return Response(status=401)
    user = session['user']
    avatar_url = f"https://cdn.discordapp.com/avatars/{user['id']}/{user['avatar']}.png"
    return requests.get(avatar_url).content
