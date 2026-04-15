#!/usr/bin/env python3
"""
Generate teams.yaml from existing GitHub organization teams
Usage: python3 scripts/generate-teams-config.py <org-name> <github-token>
"""

import sys
import os
import json
import requests
import yaml

def fetch_teams(org_name, token):
    """Fetch all teams from a GitHub organization"""
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    teams = []
    page = 1
    
    while True:
        url = f'https://api.github.com/orgs/{org_name}/teams?per_page=100&page={page}'
        print(url)
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Error: {response.status_code} - {response.text}", file=sys.stderr)
            sys.exit(1)
        
        data = response.json()
        if not data:
            break
            
        teams.extend(data)
        page += 1
    
    return teams

def fetch_team_members(org_name, team_slug, token):
    """Fetch members of a team"""
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    url = f'https://api.github.com/orgs/{org_name}/teams/{team_slug}/members'
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return []
    
    members = response.json()
    result = []
    
    # Get membership details for each member to determine role
    for member in members:
        membership_url = f'https://api.github.com/orgs/{org_name}/teams/{team_slug}/memberships/{member["login"]}'
        membership_response = requests.get(membership_url, headers=headers)
        
        if membership_response.status_code == 200:
            membership_data = membership_response.json()
            result.append({
                'username': member['login'],
                'role': membership_data.get('role', 'member')
            })
        else:
            result.append({
                'username': member['login'],
                'role': 'member'
            })
    
    return result

def generate_config(teams, org_name, token):
    """Generate teams.yaml configuration"""
    config = {'teams': []}
    
    for team in teams:
        print(f"Processing team: {team['name']}...", file=sys.stderr)
        
        # Fetch members for this team
        members = fetch_team_members(org_name, team['slug'], token)
        
        team_config = {
            'name': team['name'],
            'description': team['description'] or '',
            'privacy': team['privacy'],
        }
        
        if members:
            team_config['members'] = members
        
        config['teams'].append(team_config)
    
    return config

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 scripts/generate-teams-config.py <org-name> <github-token>")
        print("Or set GITHUB_TOKEN environment variable")
        sys.exit(1)
    
    org_name = sys.argv[1]
    token = sys.argv[2]

    # Determine the output file path (parent directory of scripts/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    output_file = os.path.join(parent_dir, 'teams.yaml')
    
    print(f"Fetching teams from {org_name}...", file=sys.stderr)
    teams = fetch_teams(org_name, token)
    print(f"Found {len(teams)} teams", file=sys.stderr)
    
    print("Generating configuration...", file=sys.stderr)
    config = generate_config(teams, org_name, token)
    
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
            print(f"  Teams: {len(config['teams'])}", file=sys.stderr)
            
        else:
            print("\nPrinting configuration to stdout:", file=sys.stderr)
            print(yaml_content)
            
    except (KeyboardInterrupt, EOFError):
        print("\n\nSave cancelled. Printing to stdout instead:", file=sys.stderr)
        print(yaml_content)

if __name__ == '__main__':
    main()

# Made with Bob
