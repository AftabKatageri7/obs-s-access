#!/usr/bin/env python3
"""
Generate collaborators.yaml from existing GitHub repository collaborators
Usage: python3 scripts/generate-collaborators-config.py <org-name> <github-token>
"""

import sys
import os
import json
import requests
import yaml

def fetch_repos(org_name, token):
    """Fetch all repositories from a GitHub organization"""
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    repos = []
    page = 1
    
    while True:
        url = f'https://api.github.com/orgs/{org_name}/repos?per_page=100&page={page}&type=all'
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}", file=sys.stderr)
            sys.exit(1)
        
        data = response.json()
        if not data:
            break
            
        repos.extend(data)
        page += 1
    
    return repos

def fetch_org_members(org_name, token):
    """Fetch all organization members to filter out from collaborators"""
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    members = set()
    page = 1
    
    while True:
        url = f'https://api.github.com/orgs/{org_name}/members?per_page=100&page={page}'
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Warning: Could not fetch org members: {response.status_code}", file=sys.stderr)
            break
        
        data = response.json()
        if not data:
            break
            
        members.update(member['login'] for member in data)
        page += 1
    
    return members

def fetch_repo_collaborators(org_name, repo_name, token, org_members):
    """Fetch external collaborators for a repository (excluding org members)"""
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    url = f'https://api.github.com/repos/{org_name}/{repo_name}/collaborators?affiliation=direct'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return []
    
    try:
        collaborators = response.json()
        external_collaborators = []
        
        for collab in collaborators:
            username = collab.get('login')
            
            # Skip if user is an organization member
            if username in org_members:
                continue
            
            # Get detailed permissions for this collaborator
            perms_url = f'https://api.github.com/repos/{org_name}/{repo_name}/collaborators/{username}/permission'
            perms_response = requests.get(perms_url, headers=headers)
            
            if perms_response.status_code == 200:
                perms_data = perms_response.json()
                permission = perms_data.get('permission', 'pull')
                
                external_collaborators.append({
                    'username': username,
                    'permission': permission
                })
            else:
                # Fallback to basic permission from collaborators list
                permissions = collab.get('permissions', {})
                if permissions.get('admin'):
                    permission = 'admin'
                elif permissions.get('maintain'):
                    permission = 'maintain'
                elif permissions.get('push'):
                    permission = 'push'
                elif permissions.get('triage'):
                    permission = 'triage'
                else:
                    permission = 'pull'
                
                external_collaborators.append({
                    'username': username,
                    'permission': permission
                })
        
        return external_collaborators
        
    except (ValueError, KeyError) as e:
        print(f"  Warning: Error parsing collaborators for {repo_name}: {e}", file=sys.stderr)
        return []

def generate_config(repos, org_name, token):
    """Generate collaborators.yaml configuration grouped by repository"""
    config = {'repositories': []}
    
    # First, fetch all organization members to filter them out
    print("Fetching organization members...", file=sys.stderr)
    org_members = fetch_org_members(org_name, token)
    print(f"Found {len(org_members)} organization members (will be excluded)", file=sys.stderr)
    print("", file=sys.stderr)
    
    repos_with_collaborators = 0
    total_collaborators = 0
    
    for repo in repos:
        repo_name = repo.get('name', 'unknown')
        print(f"Processing {repo_name}...", file=sys.stderr)
        
        try:
            # Fetch external collaborators for this repository
            collaborators = fetch_repo_collaborators(org_name, repo_name, token, org_members)
            
            if collaborators:
                repos_with_collaborators += 1
                total_collaborators += len(collaborators)
                print(f"  Found {len(collaborators)} external collaborator(s)", file=sys.stderr)
            else:
                print(f"  No external collaborators", file=sys.stderr)
            
            # Include all repositories, even those without external collaborators
            repo_config = {
                'name': repo_name,
                'collaborators': [
                    {
                        'username': collab['username'],
                        'permission': collab['permission']
                    }
                    for collab in collaborators
                ]
            }
            config['repositories'].append(repo_config)
                
        except Exception as e:
            print(f"  Error processing {repo_name}: {e}", file=sys.stderr)
            continue
    
    print("", file=sys.stderr)
    print(f"Summary:", file=sys.stderr)
    print(f"  Total repositories: {len(config['repositories'])}", file=sys.stderr)
    print(f"  Repositories with external collaborators: {repos_with_collaborators}", file=sys.stderr)
    print(f"  Total external collaborators: {total_collaborators}", file=sys.stderr)
    
    return config

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/generate-collaborators-config.py <org-name> <github-token>")
        print("Or set GITHUB_TOKEN environment variable")
        sys.exit(1)
    
    org_name = sys.argv[1]
    token = sys.argv[2]

    # Determine the output file path (parent directory of scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    output_file = os.path.join(parent_dir, 'collaborators.yaml')
    
    print(f"Fetching repositories from {org_name}...", file=sys.stderr)
    repos = fetch_repos(org_name, token)
    print(f"Found {len(repos)} repositories", file=sys.stderr)
    print("", file=sys.stderr)
    
    print("Generating configuration...", file=sys.stderr)
    config = generate_config(repos, org_name, token)
    
    # Generate YAML content
    yaml_content = yaml.dump(config, default_flow_style=False, sort_keys=False)
    
    print(f"\nConfiguration generated successfully!", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    
    # Prompt user to save
    print(f"\nWould you like to save the configuration to {output_file}?", file=sys.stderr)
    print("(y/n): ", end='', file=sys.stderr)
    sys.stderr.flush()
    
    try:
        response = input().strip().lower()
        
        if response in ['y', 'yes']:
            # Check if file exists
            if os.path.exists(output_file):
                print(f"\nWarning: {output_file} already exists!", file=sys.stderr)
                print("Overwrite? (y/n): ", end='', file=sys.stderr)
                sys.stderr.flush()
                overwrite = input().strip().lower()
                
                if overwrite not in ['y', 'yes']:
                    print("\nSave cancelled. Printing to stdout instead:", file=sys.stderr)
                    print(yaml_content)
                    return
            
            # Save to file
            with open(output_file, 'w') as f:
                f.write(yaml_content)
            
            print(f"\n✓ Configuration saved to {output_file}", file=sys.stderr)
            print(f"  Repositories with collaborators: {len(config['repositories'])}", file=sys.stderr)
            print(f"\nNext steps:", file=sys.stderr)
            print(f"  1. Review {output_file} and adjust as needed", file=sys.stderr)
            print(f"  2. Run 'terraform plan' to preview changes", file=sys.stderr)
            print(f"  3. Use scripts/import-resources.py to import existing collaborators", file=sys.stderr)
            
        else:
            print("\nPrinting configuration to stdout:", file=sys.stderr)
            print(yaml_content)
            
    except (KeyboardInterrupt, EOFError):
        print("\n\nSave cancelled. Printing to stdout instead:", file=sys.stderr)
        print(yaml_content)

if __name__ == '__main__':
    main()

# Made with Bob