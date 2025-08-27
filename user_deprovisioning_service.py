# user_deprovisioning_service.py - Simple Version (No Azure OAuth)
import secrets
import string
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import ldap3
from ldap3 import Server, Connection, ALL, MODIFY_REPLACE, MODIFY_DELETE
from config import Config
import requests


logger = logging.getLogger(__name__)


class UserDeprovisioningService:
	def __init__(self):
		self.ad_connection = None
		self.results = []
		self.config = Config()
		self.m365_username = None
		self.m365_password = None
   	 
	def add_result(self, action: str, status: str, message: str, details: Optional[Dict] = None):
		"""Add a result to the results list"""
		self.results.append({
			'action': action,
			'status': status,  # success, error, warning, info
			'message': message,
			'details': details or {},
			'timestamp': datetime.now().isoformat()
		})
		logger.info(f"{action} - {status}: {message}")
   	 
	def generate_password(self, length: int = 16, exclude_names: Optional[List[str]] = None) -> str:
		"""Generate a complex password excluding specified names"""
		if exclude_names is None:
			exclude_names = []
	   	 
		upper = string.ascii_uppercase
		lower = string.ascii_lowercase
		digits = string.digits
		special = '@#$%&*?!'
   	 
		max_attempts = 100
		for attempt in range(max_attempts):
			# Ensure at least one character from each category
			password = [
				secrets.choice(upper),
				secrets.choice(lower),
				secrets.choice(digits),
				secrets.choice(special)
			]
	   	 
			# Fill remaining length
			all_chars = upper + lower + digits + special
			for _ in range(length - 4):
				password.append(secrets.choice(all_chars))
		   	 
			# Shuffle the password
			secrets.SystemRandom().shuffle(password)
			password_str = ''.join(password)
	   	 
			# Check if password contains any excluded names
			if not any(name.lower() in password_str.lower()
				  	for name in exclude_names if name and len(name) > 2):
				return password_str
		   	 
		# Fallback password if we can't exclude names
		return ''.join(secrets.choice(all_chars) for _ in range(length))
	
	def find_graph_user(self, email: str):
		"""Find user in Microsoft Graph by email using OAuth token"""
		try:
			headers = {
				'Authorization': f'Bearer {self.graph_client}',
				'Content-Type': 'application/json'
			}
	   	 
			url = f"https://graph.microsoft.com/v1.0/users/{email}"
			response = requests.get(url, headers=headers)
	   	 
			if response.status_code == 200:
				user = response.json()
				self.add_result("Graph User Search", "success", f"Found M365 user: {user['displayName']}")
				return user
			elif response.status_code == 404:
				self.add_result("Graph User Search", "warning", f"User not found in M365: {email}")
				return None
			elif response.status_code == 401:
				self.add_result("Graph User Search", "error", "Access token expired or insufficient permissions")
				return None
			else:
				self.add_result("Graph User Search", "error", f"Graph user search failed: {response.text}")
				return None
		   	 
		except Exception as e:
			self.add_result("Graph User Search", "error", f"Graph user search exception: {str(e)}")
			return None
	
	def disable_m365_account(self, user_id: str) -> bool:
		"""Disable Microsoft 365 account using OAuth token"""
		try:
			headers = {
				'Authorization': f'Bearer {self.graph_client}',
				'Content-Type': 'application/json'
			}
	   	 
			data = {'accountEnabled': False}
			url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
			response = requests.patch(url, json=data, headers=headers)
	   	 
			if response.status_code == 204:
				self.add_result("M365 Disable", "success", "M365 account disabled successfully")
				return True
			elif response.status_code == 403:
				self.add_result("M365 Disable", "error", "Insufficient permissions to disable M365 account")
				return False
			else:
				self.add_result("M365 Disable", "error", f"Failed to disable M365 account: {response.text}")
				return False
		   	 
		except Exception as e:
			self.add_result("M365 Disable", "error", f"M365 disable exception: {str(e)}")
			return False
	
	def revoke_m365_sessions(self, user_id: str) -> bool:
		"""Revoke all Microsoft 365 sessions using OAuth token"""
		try:
			headers = {
				'Authorization': f'Bearer {self.graph_client}',
				'Content-Type': 'application/json'
			}
	   	 
			url = f"https://graph.microsoft.com/v1.0/users/{user_id}/revokeSignInSessions"
			response = requests.post(url, headers=headers)
	   	 
			if response.status_code == 200:
				result = response.json()
				self.add_result("M365 Sessions", "success", f"All M365 sessions revoked successfully: {result.get('value', 'Success')}")
				return True
			elif response.status_code == 403:
				self.add_result("M365 Sessions", "error", "Insufficient permissions to revoke sessions")
				return False
			else:
				self.add_result("M365 Sessions", "error", f"Failed to revoke sessions: {response.text}")
				return False
		   	 
		except Exception as e:
			self.add_result("M365 Sessions", "error", f"M365 session revocation exception: {str(e)}")
			return False
	
	def remove_mfa_methods(self, user_id: str) -> bool:
		"""Remove all MFA authentication methods using OAuth token"""
		try:
			headers = {
				'Authorization': f'Bearer {self.graph_client}',
				'Content-Type': 'application/json'
			}
	   	 
			removed_count = 0
	   	 
			# Remove phone methods
			phone_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/authentication/phoneMethods"
			phone_response = requests.get(phone_url, headers=headers)
	   	 
			if phone_response.status_code == 200:
				phone_methods = phone_response.json().get('value', [])
				for method in phone_methods:
					delete_url = f"{phone_url}/{method['id']}"
					delete_response = requests.delete(delete_url, headers=headers)
					if delete_response.status_code == 204:
						removed_count += 1
						self.add_result("MFA Cleanup", "success", f"Removed phone method: {method.get('phoneType', 'Unknown')}")
					else:
						self.add_result("MFA Cleanup", "warning", f"Failed to remove phone method: {method['id']}")
			elif phone_response.status_code == 403:
				self.add_result("MFA Cleanup", "error", "Insufficient permissions to access MFA methods")
				return False
	   	 
			# Remove Microsoft Authenticator methods
			auth_url = f"https://graph.microsoft.com/v1.0/users/{user_id}/authentication/microsoftAuthenticatorMethods"
			auth_response = requests.get(auth_url, headers=headers)
	   	 
			if auth_response.status_code == 200:
				auth_methods = auth_response.json().get('value', [])
				for method in auth_methods:
					delete_url = f"{auth_url}/{method['id']}"
					delete_response = requests.delete(delete_url, headers=headers)
					if delete_response.status_code == 204:
						removed_count += 1
						self.add_result("MFA Cleanup", "success", f"Removed authenticator method: {method['id']}")
					else:
						self.add_result("MFA Cleanup", "warning", f"Failed to remove authenticator method: {method['id']}")
	   	 
			if removed_count > 0:
				self.add_result("MFA Cleanup", "success", f"Successfully removed {removed_count} MFA methods")
			else:
				self.add_result("MFA Cleanup", "info", "No MFA methods found to remove")
	   	 
			return True
	   	 
		except Exception as e:
			self.add_result("MFA Cleanup", "error", f"MFA cleanup exception: {str(e)}")
			return False
	
	def connect_ad_with_credentials(self, username: str, password: str) -> bool:
		"""Connect to Active Directory with user-provided credentials"""
		try:
			server = Server(
				self.config.AD_SERVER,
				get_info=ALL,
				use_ssl=self.config.AD_USE_SSL,
				port=self.config.AD_PORT
			)
	   	 
			# Try to format the username properly for AD
			if '@' not in username:
				# Assume it's just the username, try to add domain
				domain_parts = self.config.AD_SEARCH_BASE.replace('DC=', '').replace(',', '.').split('.')
				domain_name = '.'.join([part for part in domain_parts if part])
				formatted_username = f"{username}@{domain_name}"
			else:
				formatted_username = username
	   	 
			self.ad_connection = Connection(
				server,
				formatted_username,
				password,
				auto_bind=True
			)
	   	 
			self.add_result(
				"AD Connection",
				"success",
				f"Successfully connected to Active Directory as: {formatted_username}"
			)
			return True
	   	 
		except ldap3.core.exceptions.LDAPBindError as e:
			self.add_result(
				"AD Connection",
				"error",
				f"AD authentication failed - invalid credentials: {str(e)}"
			)
			return False
		except Exception as e:
			self.add_result(
				"AD Connection",
				"error",
				f"AD connection failed: {str(e)}"
			)
			return False
	
	def find_ad_user(self, email: str):
		"""Find user in Active Directory by email"""
		try:
			search_filter = f'(mail={email})'
			self.ad_connection.search(
				self.config.AD_SEARCH_BASE,
				search_filter,
				attributes=['sAMAccountName', 'mail', 'givenName', 'sn', 'distinguishedName', 'userAccountControl']
			)
	   	 
			if self.ad_connection.entries:
				user = self.ad_connection.entries[0]
				self.add_result("AD User Search", "success", f"Found AD user: {user.sAMAccountName}")
				return user
			else:
				self.add_result("AD User Search", "warning", f"User not found in AD: {email}")
				return None
		   	 
		except Exception as e:
			self.add_result("AD User Search", "error", f"AD user search failed: {str(e)}")
			return None
	
	def disable_ad_account(self, user_dn: str) -> bool:
		"""Disable Active Directory account"""
		try:
			changes = {'userAccountControl': [(MODIFY_REPLACE, [514])]}  # 514 = disabled account
	   	 
			if self.ad_connection.modify(user_dn, changes):
				self.add_result("AD Disable", "success", "AD account disabled successfully")
				return True
			else:
				self.add_result("AD Disable", "error", f"Failed to disable AD account: {self.ad_connection.result}")
				return False
		   	 
		except Exception as e:
			self.add_result("AD Disable", "error", f"AD disable exception: {str(e)}")
			return False
	
	def set_ad_expiration(self, user_dn: str) -> bool:
		"""Set AD account expiration to yesterday"""
		try:
			yesterday = datetime.now() - timedelta(days=1)
			# Convert to AD timestamp (100-nanosecond intervals since Jan 1, 1601)
			ad_timestamp = str(int((yesterday - datetime(1601, 1, 1)).total_seconds() * 10000000))
	   	 
			changes = {'accountExpires': [(MODIFY_REPLACE, [ad_timestamp])]}
	   	 
			if self.ad_connection.modify(user_dn, changes):
				self.add_result("AD Expiration", "success", "Account expiration set to yesterday")
				return True
			else:
				self.add_result("AD Expiration", "error", f"Failed to set expiration: {self.ad_connection.result}")
				return False
		   	 
		except Exception as e:
			self.add_result("AD Expiration", "error", f"AD expiration exception: {str(e)}")
			return False
	
	def reset_ad_password(self, user_dn: str, password: str) -> bool:
		"""Reset Active Directory password"""
		try:
			# AD password must be enclosed in quotes and UTF-16LE encoded
			password_value = f'"{password}"'.encode('utf-16le')
			changes = {'unicodePwd': [(MODIFY_REPLACE, [password_value])]}
	   	 
			if self.ad_connection.modify(user_dn, changes):
				self.add_result("AD Password", "success", "AD password reset successfully")
				return True
			else:
				self.add_result("AD Password", "error", f"Failed to reset AD password: {self.ad_connection.result}")
				return False
		   	 
		except Exception as e:
			self.add_result("AD Password", "error", f"AD password reset exception: {str(e)}")
			return False
	
	def move_ad_user(self, user_dn: str) -> bool:
		"""Move AD user to terminated OU"""
		try:
			# Extract CN from current DN
			cn = user_dn.split(',')[0]  # Get the CN part
	   	 
			if self.ad_connection.modify_dn(user_dn, cn, new_superior=self.config.AD_TERMINATED_OU):
				self.add_result("AD Move", "success", f"User moved to terminated OU")
				return True
			else:
				self.add_result("AD Move", "error", f"Failed to move user: {self.ad_connection.result}")
				return False
		   	 
		except Exception as e:
			self.add_result("AD Move", "error", f"AD move exception: {str(e)}")
			return False
