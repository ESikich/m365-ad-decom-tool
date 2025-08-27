# config.py - Full M365 Support Configuration
import os
from decouple import config


class Config:
	# Flask Configuration
	SECRET_KEY = config('SECRET_KEY', default='dev-key-change-in-production')
	SESSION_TYPE = 'filesystem'
	SESSION_PERMANENT = False
	
	# Microsoft Graph Configuration (for OAuth)
	GRAPH_CLIENT_ID = config('GRAPH_CLIENT_ID', default='')
	GRAPH_CLIENT_SECRET = config('GRAPH_CLIENT_SECRET', default='')
	GRAPH_TENANT_ID = config('GRAPH_TENANT_ID', default='')
	GRAPH_AUTHORITY = f"https://login.microsoftonline.com/{config('GRAPH_TENANT_ID', default='common')}"
	
	# Active Directory Configuration
	AD_SERVER = config('AD_SERVER', default='')
	AD_PORT = config('AD_PORT', default=389, cast=int)
	AD_USE_SSL = config('AD_USE_SSL', default=False, cast=bool)
	AD_SEARCH_BASE = config('AD_SEARCH_BASE', default='')
	AD_TERMINATED_OU = config('AD_TERMINATED_OU', default='OU=Terminated Users,DC=domain,DC=com')
	
	# Application Settings
	REQUIRE_CONFIRMATION = config('REQUIRE_CONFIRMATION', default=True, cast=bool)
	LOG_LEVEL = config('LOG_LEVEL', default='INFO')
	
	@classmethod
	def validate_config(cls):
		"""Validate that required configuration is present"""
		required_fields = [
			'GRAPH_CLIENT_ID',
			'GRAPH_CLIENT_SECRET',
			'GRAPH_TENANT_ID',
			'AD_SERVER',
			'AD_SEARCH_BASE'
		]
   	 
		missing = []
		for field in required_fields:
			if not getattr(cls, field):
				missing.append(field)
		   	 
		return missing
