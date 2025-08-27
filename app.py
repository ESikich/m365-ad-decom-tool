# app.py - Full M365 Support with Azure OAuth
import os
import logging
import urllib.parse
import uuid
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_session import Session
import msal
from config import Config
from user_deprovisioning_service import UserDeprovisioningService


# Configure logging
logging.basicConfig(
	level=getattr(logging, Config.LOG_LEVEL),
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


app = Flask(__name__)
app.config.from_object(Config)
Session(app)


def _load_cache():
	"""Load token cache from session"""
	cache = msal.SerializableTokenCache()
	if session.get("token_cache"):
		cache.deserialize(session["token_cache"])
	return cache


def _save_cache(cache):
	"""Save token cache to session"""
	if cache.has_state_changed:
		session["token_cache"] = cache.serialize()


def _build_msal_app(cache=None):
	"""Build MSAL application for user authentication"""
	return msal.ConfidentialClientApplication(
		Config.GRAPH_CLIENT_ID,
		authority=Config.GRAPH_AUTHORITY,
		client_credential=Config.GRAPH_CLIENT_SECRET,
		token_cache=cache
	)


@app.route('/')
def index():
	"""Main dashboard page"""
	# Check if user is authenticated
	if not session.get("user"):
		return redirect(url_for("login"))
	
	# Check configuration status
	missing_config = Config.validate_config()
	config_status = {
		'is_configured': len(missing_config) == 0,
		'missing_fields': missing_config,
		'user_authenticated': True,
		'user_name': session.get("user", {}).get("name", "Unknown"),
		'user_email': session.get("user", {}).get("preferred_username", "")
	}
	
	return render_template('index.html', config_status=config_status)


@app.route('/login')
def login():
	"""Initiate login process"""
	# Microsoft Graph scopes needed
	scopes = [
		"User.ReadWrite.All",
		"Directory.ReadWrite.All",
		"UserAuthenticationMethod.ReadWrite.All",
		"Group.ReadWrite.All"
	]
	
	# Generate state and save to session
	state = str(uuid.uuid4())
	session["flow"] = {
		"state": state,
		"redirect_uri": url_for("auth_response", _external=True)
	}
	
	# Build authorization URL
	auth_app = _build_msal_app()
	auth_url = auth_app.get_authorization_request_url(
		scopes,
		state=state,
		redirect_uri=url_for("auth_response", _external=True)
	)
	
	return redirect(auth_url)


@app.route('/auth-response')
def auth_response():
	"""Handle authentication response"""
	try:
		# Verify state parameter
		if request.args.get('state') != session.get("flow", {}).get("state"):
			return render_template('error.html', error="Invalid state parameter"), 400
   	 
		if "error" in request.args:
			return render_template('error.html', error=request.args["error"]), 400
   	 
		cache = _load_cache()
		auth_app = _build_msal_app(cache=cache)
   	 
		# Get token using authorization code
		result = auth_app.acquire_token_by_authorization_code(
			request.args['code'],
			scopes=[
				"User.ReadWrite.All",
				"Directory.ReadWrite.All",
				"UserAuthenticationMethod.ReadWrite.All",
				"Group.ReadWrite.All"
			],
			redirect_uri=url_for("auth_response", _external=True)
		)
   	 
		if "error" in result:
			logger.error(f"Authentication failed: {result}")
			return render_template('error.html', error="Authentication failed"), 400
   	 
		# Save user information to session
		session["user"] = result.get("id_token_claims")
		session["access_token"] = result.get("access_token")
   	 
		_save_cache(cache)
   	 
		return redirect(url_for("index"))
   	 
	except Exception as e:
		logger.exception("Auth response error")
		return render_template('error.html', error=str(e)), 500


@app.route('/logout')
def logout():
	"""Logout user"""
	session.clear()
	return redirect(Config.GRAPH_AUTHORITY + "/oauth2/v2.0/logout" +
			   	"?post_logout_redirect_uri=" +
			   	urllib.parse.quote(url_for("login", _external=True)))


@app.route('/test-connections', methods=['POST'])
def test_connections():
	"""Test connections to AD and Microsoft Graph"""
	if not session.get("user"):
		return jsonify({'error': 'Not authenticated to Microsoft 365'}), 401
	
	try:
		data = request.get_json()
		ad_username = data.get('adUsername', '').strip()
		ad_password = data.get('adPassword', '').strip()
   	 
		if not ad_username or not ad_password:
			return jsonify({'error': 'AD credentials required for testing'}), 400
   	 
		service = UserDeprovisioningService()
		results = {}
   	 
		# Test Microsoft 365 with user's OAuth token
		try:
			access_token = session.get("access_token")
			if access_token:
				service.graph_client = access_token
				results['graph'] = True
				service.add_result("Graph Auth", "success", f"Using OAuth token for user: {session.get('user', {}).get('preferred_username', 'Unknown')}")
			else:
				results['graph'] = False
				service.add_result("Graph Auth", "error", "No valid OAuth token found")
		except Exception as e:
			logger.error(f"Graph connection test failed: {e}")
			results['graph'] = False
	   	 
		# Test AD connection with provided credentials
		try:
			ad_success = service.connect_ad_with_credentials(ad_username, ad_password)
			results['ad'] = ad_success
			if ad_success and service.ad_connection:
				service.ad_connection.unbind()
		except Exception as e:
			logger.error(f"AD connection test failed: {e}")
			results['ad'] = False
	   	 
		# Test permissions based on successful connections
		results['service'] = results['ad'] and results['graph']
		results['ou'] = results['ad']
   	 
		# Return results with log messages
		return jsonify({
			**results,
			'messages': [{'message': r['message'], 'status': r['status']}
						for r in service.results]
		}), 200
   	 
	except Exception as e:
		logger.exception("Connection test error")
		return jsonify({'error': str(e)}), 500


@app.route('/deprovision', methods=['POST'])
def deprovision_user():
	"""Main deprovisioning endpoint with full M365 support"""
	if not session.get("user"):
		return jsonify({'error': 'Not authenticated to Microsoft 365'}), 401
	
	try:
		data = request.get_json()
		user_email = data.get('userEmail', '').strip()
		actions = data.get('actions', {})
		ad_username = data.get('adUsername', '').strip()
		ad_password = data.get('adPassword', '').strip()
   	 
		if not user_email:
			return jsonify({'error': 'User email is required'}), 400
	   	 
		if not ad_username or not ad_password:
			return jsonify({'error': 'AD credentials are required'}), 400
   	 
		# Log the action with user context
		current_user = session.get("user", {})
		logger.info(f"User {current_user.get('preferred_username', 'unknown')} starting deprovisioning for: {user_email}")
   	 
		# Initialize service with user's credentials
		service = UserDeprovisioningService()
   	 
		# Set user's Graph token for M365 operations
		service.graph_client = session.get("access_token")
		service.add_result("Auth", "success", f"Authenticated as: {current_user.get('name', 'Unknown User')}")
   	 
		# Connect to AD if needed
		ad_needed = any([
			actions.get('adActions', False),
			actions.get('orgActions', False)
		])
   	 
		if ad_needed:
			if not service.connect_ad_with_credentials(ad_username, ad_password):
				return jsonify({
					'results': service.results,
					'password': None
				}), 200
   	 
		# User lookup phase
		ad_user = None
		graph_user = None
   	 
		if ad_needed:
			ad_user = service.find_ad_user(user_email)
	   	 
		# Look up M365 user if M365 actions are needed
		m365_needed = any([
			actions.get('m365Actions', False),
			actions.get('mfaActions', False)
		])
   	 
		if m365_needed:
			graph_user = service.find_graph_user(user_email)
   	 
		if not ad_user and not graph_user:
			service.add_result("User Search", "error", "User not found in any connected system")
			return jsonify({'results': service.results, 'password': None}), 200
   	 
		# Password generation
		exclude_names = []
		if graph_user:
			exclude_names.extend([
				graph_user.get('givenName', ''),
				graph_user.get('surname', '')
			])
		elif ad_user:
			exclude_names.extend([
				str(getattr(ad_user, 'givenName', '')),
				str(getattr(ad_user, 'sn', ''))
			])
   	 
		password = service.generate_password(exclude_names=exclude_names)
		service.add_result("Password", "success", "Secure password generated (excluding user names)")
   	 
		# Execute Active Directory actions
		if actions.get('adActions') and ad_user:
			user_dn = str(ad_user.distinguishedName)
	   	 
			if actions.get('disableAD'):
				service.disable_ad_account(user_dn)
		   	 
			if actions.get('expireAD'):
				service.set_ad_expiration(user_dn)
		   	 
			if actions.get('resetADPassword'):
				service.reset_ad_password(user_dn, password)
   	 
		# Execute Microsoft 365 actions (now with real Graph API calls)
		if actions.get('m365Actions') and graph_user:
			user_id = graph_user['id']
	   	 
			if actions.get('disableM365'):
				service.disable_m365_account(user_id)
		   	 
			if actions.get('revokeSessions'):
				service.revoke_m365_sessions(user_id)
   	 
		# Execute MFA cleanup (now with real Graph API calls)
		if actions.get('mfaActions') and graph_user:
			user_id = graph_user['id']
	   	 
			if actions.get('removeMFA'):
				service.remove_mfa_methods(user_id)
   	 
		# Execute organizational actions
		if actions.get('orgActions'):
			if actions.get('moveToTerminated') and ad_user:
				service.move_ad_user(str(ad_user.distinguishedName))
   	 
		# Cleanup connections
		if service.ad_connection:
			service.ad_connection.unbind()
   	 
		service.add_result("Complete", "success", "User deprovisioning process completed successfully!")
   	 
		logger.info(f"Deprovisioning completed for {user_email} by {current_user.get('preferred_username')}. Total actions: {len(service.results)}")
   	 
		return jsonify({
			'results': service.results,
			'password': password
		}), 200
   	 
	except Exception as e:
		logger.exception("Deprovisioning error")
		return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/health', methods=['GET'])
def health_check():
	"""Health check endpoint"""
	return jsonify({
		'status': 'healthy',
		'version': '2.1',
		'config_valid': len(Config.validate_config()) == 0,
		'auth_method': 'oauth_with_ad_credentials'
	}), 200


@app.errorhandler(404)
def not_found(error):
	return render_template('error.html', error="Page not found"), 404


@app.errorhandler(500)
def internal_error(error):
	return render_template('error.html', error="Internal server error"), 500


if __name__ == '__main__':
	# Validate configuration on startup
	missing_config = Config.validate_config()
	if missing_config:
		logger.warning(f"Missing configuration: {missing_config}")
		logger.warning("Please update your .env file with the required settings")
	
	logger.info("Starting User Deprovisioning Tool with full M365 support")
	logger.info("OAuth authentication required for Microsoft 365 operations")
	
	# Enable HTTPS
	app.run(
		debug=True,
		host='0.0.0.0',
		port=5000,
		ssl_context=('cert.pem', 'key.pem')  # HTTPS with self-signed cert
	)

