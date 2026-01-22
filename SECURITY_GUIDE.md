# Security & Proprietary Protection Guide

This guide explains how to keep your pothole detection system private and proprietary.

## 1. Make GitHub Repository Private

### Option A: Through GitHub Web Interface

1. **Go to your repository**: https://github.com/jwsqueaker/git-down
2. **Click "Settings"** (top right of repository page)
3. **Scroll to "Danger Zone"** (bottom of settings)
4. **Click "Change repository visibility"**
5. **Select "Make private"**
6. **Type the repository name to confirm**
7. **Click "I understand, change repository visibility"**

✅ **Your repository is now private!** Only you and invited collaborators can see it.

### Option B: Through GitHub CLI

```bash
gh repo edit jwsqueaker/git-down --visibility private
```

### What This Does:
- ✅ Hides all code from public view
- ✅ Removes from Google search results
- ✅ Only invited collaborators can access
- ✅ Protects your intellectual property

## 2. Secure Streamlit Cloud Deployment

### Make Streamlit App Private

**Option 1: Password Protection (Free Tier)**

Add to your `streamlit_app.py` at the very top, before any other code:

```python
import streamlit as st

def check_password():
    """Returns True if the user has entered the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input + error
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

if not check_password():
    st.stop()

# Rest of your app code below...
```

Then add to `.streamlit/secrets.toml`:
```toml
app_password = "your-secure-password-here"
```

**Option 2: Email-Based Access (Streamlit Teams - Paid)**

1. Upgrade to Streamlit Teams/Enterprise plan
2. In app settings, configure allowed email domains
3. Users must sign in with Google/GitHub to access
4. Restrict to your company domain only

**Option 3: Deploy to Private Infrastructure**

Instead of public Streamlit Cloud:
- Deploy to your own AWS/GCP/Azure server
- Put behind VPN or firewall
- Use your company's authentication system
- Complete control over access

## 3. Protect Your Code

### Add .gitignore (Already Done)

Ensure these are never committed:
```
.streamlit/secrets.toml
*.pth  # Model weights
*.tif  # Imagery data
data/la_city_boundary.geojson
```

### Remove Git History (If Secrets Were Committed)

If you accidentally committed secrets:

```bash
# WARNING: This rewrites history - coordinate with team!
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .streamlit/secrets.toml' \
  --prune-empty --tag-name-filter cat -- --all

git push origin --force --all
```

Better: **Rotate all exposed secrets immediately!**

## 4. Manage Access

### GitHub Collaborators

**Add authorized users:**
1. Go to Settings → Collaborators
2. Click "Add people"
3. Enter GitHub username or email
4. Select permission level:
   - **Read**: View code only
   - **Write**: Can push changes
   - **Admin**: Full control

**Best practice:** Use teams for group management

### Streamlit Cloud Sharing

**Control who can view your app:**
1. Go to Streamlit Cloud dashboard
2. Select your app
3. Click "⚙️ Settings" → "Sharing"
4. Options:
   - **Private**: Only you
   - **Invited users**: Specific emails only
   - **Public**: Anyone (avoid for proprietary apps!)

## 5. Secure Your Secrets

### Never Commit Secrets

❌ **Don't do this:**
```python
PL_API_KEY = "pl_abc123..."  # DON'T HARDCODE!
```

✅ **Do this:**
```python
PL_API_KEY = st.secrets["PL_API_KEY"]  # From secrets.toml
```

### Rotate Credentials Regularly

- Change Planet API keys every 90 days
- Update app passwords monthly
- Revoke access for former team members immediately

### Use Environment-Specific Secrets

Different credentials for:
- Development (personal test account)
- Staging (shared test environment)
- Production (real deployment)

## 6. Monitor Access

### GitHub Audit Log

Check who accessed your code:
1. Settings → Security → Audit log
2. Review recent activity
3. Look for suspicious access

### Streamlit Analytics

Monitor app usage:
1. Streamlit Cloud dashboard
2. View analytics tab
3. Check who's using the app
4. Monitor unusual patterns

## 7. Data Protection

### Protect Training Data

If you have proprietary training data:
```bash
# Add to .gitignore
training_data/
*.npz
datasets/
```

### Protect Model Weights

Your trained models are valuable IP:
```bash
# Store models securely
models/*.pth  # Already in .gitignore

# Consider encrypting large files
gpg -c models/unet_potholes.pth
```

### Protect Results

Detection results may contain sensitive info:
- Don't commit GeoJSON outputs
- Store results in private S3 bucket
- Encrypt sensitive location data

## 8. Legal Protection

### Add Copyright Notices

Already done in:
- ✅ LICENSE file (proprietary license)
- ✅ README.md (copyright notice)

**Add to each source file:**
```python
"""
Copyright (c) 2024-2026 [Your Company]. All Rights Reserved.
Proprietary and Confidential.
"""
```

### Non-Disclosure Agreements

Require team members to sign:
- Employment agreements with IP clauses
- Contractor NDAs
- Partner confidentiality agreements

### Patent Considerations

If your detection method is novel:
- Consult with patent attorney
- File provisional patent application
- Document invention dates

## 9. Deployment Checklist

Before deploying:

- [ ] GitHub repository is private
- [ ] All secrets are in `.streamlit/secrets.toml` (not committed)
- [ ] `.gitignore` excludes all sensitive files
- [ ] LICENSE file is proprietary
- [ ] README indicates proprietary nature
- [ ] Streamlit app has password protection (or email auth)
- [ ] Only authorized collaborators have access
- [ ] Audit logging is enabled
- [ ] Team members have signed NDAs
- [ ] API keys are restricted to your IP/domain
- [ ] Backup credentials stored securely
- [ ] Incident response plan documented

## 10. What If Code Leaks?

If your code is exposed:

### Immediate Actions:
1. **Rotate all credentials** (API keys, passwords, tokens)
2. **Document the breach** (when, what, how much)
3. **Notify stakeholders** (management, legal, customers)
4. **Remove exposed code** (DMCA takedown if needed)
5. **Review access logs** (find the source)

### Preventive Measures:
- Use branch protection rules
- Require code review before merge
- Enable 2FA for all team members
- Limit repository access to minimum necessary
- Regular security training for team

## 11. Recommended Tools

### Secret Scanning
```bash
# Install git-secrets
git secrets --install
git secrets --register-aws
git secrets --scan
```

### Private Package Registry
For Python dependencies:
- AWS CodeArtifact
- Azure Artifacts
- GitHub Packages (private)
- Private PyPI server

### Code Signing
Sign your releases:
```bash
git tag -s v1.0.0 -m "Release 1.0.0"
```

## 12. Compliance

### ITAR/Export Control
If deploying imagery analysis:
- Check export control regulations
- Restrict access by country
- Document compliance

### Data Privacy
If processing personal data:
- GDPR compliance (EU)
- CCPA compliance (California)
- Data retention policies

## Summary Quick Actions

**Right Now:**
```bash
# 1. Make repo private (do this on GitHub.com in Settings)

# 2. Add password protection to Streamlit app
# (edit streamlit_app.py with password check)

# 3. Commit security updates
git add LICENSE SECURITY_GUIDE.md README.md
git commit -m "Add proprietary license and security protections"
git push origin claude/build-from-conversation-vjhRB
```

**On GitHub.com:**
1. Settings → Change repository visibility → **Make private**
2. Settings → Collaborators → Add authorized team members only
3. Enable branch protection on main branch

**On Streamlit Cloud:**
1. Deploy app to private workspace
2. Add password protection or email auth
3. Configure secrets (PL_API_KEY, app_password)
4. Set sharing to "Invited users only"

---

**Your code is now secure and proprietary!** 🔒

For questions about security, consult your legal and IT security teams.
