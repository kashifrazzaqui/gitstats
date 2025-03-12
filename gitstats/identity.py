"""
Author identity management functionality.
"""

import os
import json
from pathlib import Path

def get_config_dir():
    """Get the directory for storing configuration files."""
    # Use XDG_CONFIG_HOME if available, otherwise use ~/.config
    config_home = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
    config_dir = os.path.join(config_home, 'gitstats')
    
    # Create the directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    
    return config_dir

def get_identity_file(repo_path):
    """Get the path to the identity mapping file for a repository."""
    # Get the absolute path to the repository
    repo_abs_path = os.path.abspath(repo_path)
    
    # Create a sanitized filename based on the repository path
    repo_id = repo_abs_path.replace('/', '_').replace('\\', '_').replace(':', '_')
    
    # Get the config directory
    config_dir = get_config_dir()
    
    # Return the path to the identity mapping file
    return os.path.join(config_dir, f"{repo_id}_identities.json")

def load_identity_mappings(repo_path):
    """Load identity mappings for a repository."""
    identity_file = get_identity_file(repo_path)
    
    # Initialize empty mappings
    mappings = {
        'canonical_names': {},  # Maps author identifiers to canonical names
        'canonical_emails': {}  # Maps email addresses to canonical emails
    }
    
    # Load mappings from file if it exists
    if os.path.exists(identity_file):
        try:
            with open(identity_file, 'r') as f:
                mappings = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load identity mappings: {str(e)}")
    
    return mappings

def save_identity_mappings(repo_path, mappings):
    """Save identity mappings for a repository."""
    identity_file = get_identity_file(repo_path)
    
    try:
        with open(identity_file, 'w') as f:
            json.dump(mappings, f, indent=2)
        return True
    except IOError as e:
        print(f"Error: Failed to save identity mappings: {str(e)}")
        return False

def add_identity_mapping(repo_path, name_or_email, canonical_identity):
    """Add an identity mapping for a repository."""
    # Load existing mappings
    mappings = load_identity_mappings(repo_path)
    
    # Determine if this is an email address or a name
    if '@' in name_or_email:
        # This is an email address
        mappings['canonical_emails'][name_or_email.lower()] = canonical_identity
    else:
        # This is an author name
        mappings['canonical_names'][name_or_email] = canonical_identity
    
    # Save the updated mappings
    return save_identity_mappings(repo_path, mappings)

def remove_identity_mapping(repo_path, name_or_email):
    """Remove an identity mapping for a repository."""
    # Load existing mappings
    mappings = load_identity_mappings(repo_path)
    
    # Determine if this is an email address or a name
    if '@' in name_or_email:
        # This is an email address
        if name_or_email.lower() in mappings['canonical_emails']:
            del mappings['canonical_emails'][name_or_email.lower()]
    else:
        # This is an author name
        if name_or_email in mappings['canonical_names']:
            del mappings['canonical_names'][name_or_email]
    
    # Save the updated mappings
    return save_identity_mappings(repo_path, mappings)

def list_identity_mappings(repo_path):
    """List all identity mappings for a repository."""
    # Load existing mappings
    mappings = load_identity_mappings(repo_path)
    
    # Return the mappings
    return mappings

def get_canonical_identity(mappings, name, email):
    """Get the canonical identity for an author based on name or email."""
    # Check if the email has a mapping
    if email and email.lower() in mappings['canonical_emails']:
        return mappings['canonical_emails'][email.lower()]
    
    # Check if the name has a mapping
    if name and name in mappings['canonical_names']:
        return mappings['canonical_names'][name]
    
    # No mapping found, use the original name
    return name 