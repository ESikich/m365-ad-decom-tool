# User Deprovisioning Tool Setup Guide - User Authentication Version


## Overview


This version uses **user authentication** instead of service accounts:
- **Microsoft 365**: Users log in with their M365 account via OAuth
- **Active Directory**: Users enter their AD credentials at runtime
- **No service accounts needed** - uses the authenticated user's permissions


## Quick Start


1. **Create project directory:**
```bash
mkdir user-deprovisioning-tool
cd user-deprovisioning-tool
```


2. **Create file structure:**
```bash
mkdir templates static static/css static/js
```


3. **Install dependencies:**
```bash
pip install -r requirements.txt
```


4. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your Azure app registration details
```


5. **Run the application:**
```bash
python app.py
```


## Prerequisites


### Python Requirements
- Python 3.8 or higher
- pip package manager


### System Requirements
- Network access to Active Directory domain controllers
- Internet access for Microsoft Graph API
- Users need appropriate permissions in both AD and M365


## Azure App Registration Setup


### Step 1: Create App Registration
1. Go to Azure AD > App registrations in Azure Portal
2. Click "New registration"
3. Name: "User Deprovisioning Tool"
4. Supported account types: "Accounts in this organizational directory only"
5. Redirect URI:
   - Type: Web
   - URL: `http://localhost:5000/auth-response` (change for production)
6. Click "Register"


### Step 2: Configure Authentication
1. Go to "Authentication" in your app
2. Under "Web" redirect URIs, ensure you have:
   - `http://localhost:5000/auth-response` (development)
   - `https://your-domain.com/auth-response` (production)
3. Under "Front-channel logout URL": `http://localhost:5000/logout`
4. Under "Implicit grant and hybrid flows": Check "ID tokens"


### Step 3: Configure API Permissions
1. Go to "API permissions" in your app
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Choose "Delegated permissions" (NOT Application permissions)
5. Add these permissions:
   - `User.ReadWrite.All`
   - `Directory.ReadWrite.All`
   - `UserAuthenticationMethod.ReadWrite.All`
   - `Group.ReadWrite.All` (optional)
6. Click "Grant admin consent" (admin consent required)


### Step 4: Create Client Secret
1. Go to "Certificates & secrets"
2. Click "New client secret"
3. Description: "Deprovisioning Tool Secret"
4. Expires: Choose appropriate timeframe
5. Click "Add"
6. **IMPORTANT**: Copy the secret value immediately


### Step 5: Note Required Values
From the app registration overview page, copy:
- Application (client) ID
- Directory (tenant) ID
- Client secret (from step 4)


## Environment Configuration


Create `.env` file with these variables:


```bash
# Microsoft Graph Configuration
GRAPH_CLIENT_ID=your-azure-app-client-id
GRAPH_CLIENT_SECRET=your-azure-app-client-secret
GRAPH_TENANT_ID=your-tenant-id-or-domain.onmicrosoft.com


# Active Directory Configuration
AD_SERVER=dc01.yourdomain.com
AD_PORT=389
AD_USE_SSL=False
AD_SEARCH_BASE=DC=yourdomain,DC=com
AD_TERMINATED_OU=OU=Terminated Users,DC=yourdomain,DC=com


# Flask Security Settings
SECRET_KEY=your-random-secret-key-here-change-this-in-production
REQUIRE_CONFIRMATION=True
LOG_LEVEL=INFO
```


## User Permission Requirements


### Microsoft 365 Permissions
Users need these roles/permissions in M365:
- **User Administrator** or **Global Administrator** role
- Or custom role with permissions to:
  - Read and write all users
  - Manage user authentication methods
  - Revoke user sessions


### Active Directory Permissions
Users need these AD permissions:
- **Reset password** on target user accounts
- **Modify user account properties** (userAccountControl, accountExpires)
- **Move objects** to the Terminated Users OU
- **Read user attributes** (mail, sAMAccountName, etc.)


## Installation Steps


### 1. Create all required files:
- `app.py` (main Flask application)
- `config.py` (configuration management)
- `user_deprovisioning_service.py` (core service)
- `requirements.txt` (Python dependencies)
- `.env` (environment variables - copy from .env.example)
- `templates/index.html` (main interface)
- `templates/error.html` (error page)
- `static/css/style.css` (styles)
- `static/js/app.js` (JavaScript functionality)


### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```


### 3. Configure Environment
```bash
# Copy example and edit with your values
cp .env.example .env
nano .env  # or your preferred editor
```


### 4. Test Configuration
```bash
python app.py
```


### 5. Access Web Interface
1. Open browser to: `http://localhost:5000`
2. Click login to authenticate with Microsoft 365
3. Enter your AD credentials when prompted
4. Use "Test Connections" to verify everything works


## How User Authentication Works


### Login Flow:
1. User visits the application
2. Redirected to Microsoft 365 login
3. User authenticates with their M365 account
4. Application receives OAuth token with delegated permissions
5. User enters their AD credentials on the main page


### Security Benefits:
- **No stored service account credentials**
- **User-specific permissions** (can only do what they're authorized to do)
- **Audit trail** shows which user performed actions
- **Session-based** - credentials not permanently stored
- **Follows principle of least privilege**


## Testing Recommendations


### Before Production Use:
1. **Test with your own account** first
2. **Use dedicated test user** for deprovisioning tests
3. **Verify permissions** work correctly
4. **Test in non-production environment**
5. **Confirm audit logging** works


### Test Account Setup:
```powershell
# Create test user in PowerShell
New-ADUser -Name "Test User" -SamAccountName "testuser" -UserPrincipalName "testuser@yourdomain.com" -EmailAddress "testuser@yourdomain.com" -Enabled $true
```


## Production Deployment


### Security Considerations
- **HTTPS Only**: Must use SSL/TLS in production
- **Network Security**: Deploy on internal network
- **Access Control**: Limit to authorized personnel
- **Session Security**: Configure secure session settings
- **Audit Logging**: Enable comprehensive logging


### Production Web Server
Use a production WSGI server instead of Flask dev server:


```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```


### Production Environment Variables
Update redirect URI for production:
```bash
# In Azure App Registration, add production redirect URI:
https://your-domain.com/auth-response


# Update .env for production:
FLASK_ENV=production
SECRET_KEY=your-production-secret-key
```


## Troubleshooting


### Common Authentication Issues


**"Authentication failed" or redirect errors**
- Check redirect URI matches exactly in Azure app registration
- Verify client ID, secret, and tenant ID are correct
- Ensure app registration has correct permissions


**"Insufficient privileges" errors**
- User needs appropriate M365 admin roles
- Check that admin consent was granted for the app
- Verify delegated permissions (not application permissions)


**"AD connection failed"**
- Check AD server address and port
- Verify user's AD credentials are correct
- Test network connectivity to domain controller


**"User not found" errors**
- Verify email address format
- Check AD search base is correct
- Ensure user exists in both AD and M365


### Debug Mode
Enable debug logging:
```bash
LOG_LEVEL=DEBUG
```


## Security Best Practices


### User Guidelines:
- **Never share AD credentials** with others
- **Use the tool only with proper authorization**
- **Log out when finished** using the tool
- **Report any issues** immediately


### Administrator Guidelines:
- **Monitor usage logs** regularly
- **Review user permissions** periodically
- **Keep Azure app registration secure**
- **Update dependencies** regularly
- **Backup configurations**


### Audit and Compliance:
- All actions are logged with user context
- Timestamps and details recorded
- Export logs for compliance reporting
- Monitor for unauthorized usage


## Deployment Checklist


- [ ] Azure app registration configured
- [ ] Redirect URIs set correctly
- [ ] API permissions granted and consented
- [ ] Environment variables configured
- [ ] HTTPS enabled for production
- [ ] Network security configured
- [ ] User permissions verified
- [ ] Test connections successful
- [ ] Audit logging enabled
- [ ] Backup/recovery procedures documented


---


**⚠️ IMPORTANT SECURITY NOTES**


This user authentication model is more secure because:
- No service account credentials to manage or compromise
- Users can only perform actions they're authorized for
- Full audit trail of who did what
- Sessions expire automatically
- No permanent credential storage


Always ensure users have proper authorization before using this tool!


---


**📞 SUPPORT**


For issues or questions:
1. Check the troubleshooting section above
2. Review application logs (`LOG_LEVEL=DEBUG`)
3. Verify Azure app registration configuration
4. Test with minimal permissions first addresses processed
- Actions performed
- Timestamps
- Success/failure status
- Error details


## Version History


- **v2.1**: Initial production release
- Features: AD integration, Graph API, MFA cleanup, web interface
- Security: Confirmation dialogs, audit logging, input validation


---


**⚠️ IMPORTANT DISCLAIMER**


This tool performs permanent, irreversible changes to user accounts. Always:
- Test thoroughly in non-production environment
- Obtain proper authorization before use
- Verify configuration before processing
- Maintain audit logs for compliance
- Have recovery procedures ready


Use at your own risk. The authors are not responsible for any data loss or system damage.


