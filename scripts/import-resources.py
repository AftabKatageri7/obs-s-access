#!/usr/bin/env python3
"""
Automated Terraform Import Script for GitHub Access Management
Imports teams, team members, and external collaborators.
Usage: python3 scripts/import-resources.py <org-name>
"""

import sys
import os
import subprocess
import json
import yaml
import requests
from typing import Dict, List, Optional

class TerraformImporter:
    def __init__(self, org_name: str, github_token: str):
        self.org_name = org_name
        self.github_token = github_token
        self.headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        self.teams_cache = None
        
    def print_header(self, text: str):
        """Print a formatted header"""
        print(f"\n{text}")
        print("-" * len(text))
        
    def print_success(self, text: str):
        """Print success message"""
        print(f"  ✓ {text}")
        
    def print_info(self, text: str):
        """Print info message"""
        print(f"  ℹ {text}")
        
    def print_error(self, text: str):
        """Print error message"""
        print(f"  ✗ {text}")
        
    def print_progress(self, text: str):
        """Print progress message"""
        print(f"  → {text}")
        
    def check_prerequisites(self) -> bool:
        """Check if all prerequisites are met"""
        # Check if terraform is initialized
        if not os.path.exists('.terraform'):
            self.print_error("Terraform not initialized. Run 'terraform init' first.")
            return False
            
        # Check if YAML files exist
        if not os.path.exists('teams.yaml'):
            self.print_error("teams.yaml not found")
            return False
        
        # collaborators.yaml is optional
        if not os.path.exists('collaborators.yaml'):
            self.print_info("collaborators.yaml not found (optional)")
            
        return True
        
    def fetch_teams(self) -> List[Dict]:
        """Fetch all teams from GitHub"""
        if self.teams_cache is not None:
            return self.teams_cache
            
        teams = []
        page = 1
        
        while True:
            url = f'https://api.github.com/orgs/{self.org_name}/teams?per_page=100&page={page}'
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                self.print_error(f"Failed to fetch teams: {response.status_code}")
                break
                
            data = response.json()
            if not data:
                break
                
            teams.extend(data)
            page += 1
            
        self.teams_cache = teams
        return teams
        
    def get_team_id(self, team_name: str) -> Optional[str]:
        """Get team ID by name"""
        teams = self.fetch_teams()
        for team in teams:
            if team['name'] == team_name:
                return str(team['id'])
        return None
        
    def is_in_state(self, resource_address: str) -> bool:
        """Check if resource is already in Terraform state"""
        try:
            result = subprocess.run(
                ['terraform', 'state', 'show', resource_address],
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
            
    def import_resource(self, resource_address: str, resource_id: str, use_target: bool = True) -> bool:
        """Import a resource into Terraform state"""
        # Check if already in state
        if self.is_in_state(resource_address):
            self.print_success(f"Already in state: {resource_address}")
            return True
            
        self.print_progress(f"Importing: {resource_address}")
        
        try:
            # Use -target to avoid evaluating unrelated resources during import
            cmd = ['terraform', 'import']
            if use_target:
                cmd.extend(['-target', resource_address])
            cmd.extend([resource_address, resource_id])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.print_success(f"Imported: {resource_address}")
                return True
            else:
                self.print_error(f"Failed to import: {resource_address}")
                if result.stderr:
                    print(f"    Error: {result.stderr.strip()}")
                return False
                
        except Exception as e:
            self.print_error(f"Exception importing {resource_address}: {e}")
            return False
            
    def import_teams(self, teams_config: Dict) -> int:
        """Import all teams"""
        self.print_header("Step 2: Importing teams")
        
        teams = teams_config.get('teams', [])
        if not teams:
            self.print_info("No teams defined in teams.yaml")
            return 0
            
        imported = 0
        for team in teams:
            team_name = team['name']
            team_id = self.get_team_id(team_name)
            
            if not team_id:
                self.print_error(f"Team not found in GitHub: {team_name}")
                continue
                
            resource_address = f'module.teams.github_team.team["{team_name}"]'
            if self.import_resource(resource_address, team_id):
                imported += 1
                
        return imported
        
    def import_team_members(self, teams_config: Dict) -> int:
        """Import all team members"""
        self.print_header("Step 3: Importing team members")
        
        teams = teams_config.get('teams', [])
        if not teams:
            self.print_info("No teams defined in teams.yaml")
            return 0
        
        # Check if any teams have members
        has_members = any(team.get('members') for team in teams)
        
        if not has_members:
            self.print_info("No team members defined in teams.yaml, skipping...")
            return 0
            
        imported = 0
        teams_without_members = []
        
        for team in teams:
            team_name = team.get('name')
            if not team_name:
                self.print_error("Team without name found, skipping")
                continue
                
            members = team.get('members', [])
            
            # Track teams without members for reporting
            if not members:
                teams_without_members.append(team_name)
                continue
                
            team_id = self.get_team_id(team_name)
            if not team_id:
                self.print_error(f"Team not found in GitHub: {team_name}")
                continue
                
            for member in members:
                if not isinstance(member, dict):
                    self.print_error(f"Invalid member format in team {team_name}")
                    continue
                    
                username = member.get('username')
                if not username:
                    self.print_error(f"Member without username in team {team_name}")
                    continue
                    
                resource_address = f'module.teams.github_team_membership.membership["{team_name}-{username}"]'
                resource_id = f'{team_id}:{username}'
                
                if self.import_resource(resource_address, resource_id):
                    imported += 1
        
        # Report teams without members
        if teams_without_members:
            self.print_info(f"Teams with no members (skipped): {', '.join(teams_without_members)}")
                    
        return imported
    
    def import_collaborators(self, collaborators_config: Dict) -> int:
        """Import repository collaborators"""
        self.print_header("Step 4: Importing repository collaborators")
        
        repositories = collaborators_config.get('repositories', [])
        if not repositories:
            self.print_info("No collaborators defined in collaborators.yaml")
            return 0
        
        imported = 0
        for repo in repositories:
            if not isinstance(repo, dict):
                self.print_error("Invalid repository format")
                continue
            
            repo_name = repo.get('name')
            collaborators = repo.get('collaborators', [])
            
            if not repo_name:
                self.print_error("Repository missing name")
                continue
            
            if not collaborators:
                continue
            
            for collab in collaborators:
                if not isinstance(collab, dict):
                    self.print_error(f"Invalid collaborator format in repository {repo_name}")
                    continue
                
                username = collab.get('username')
                
                if not username:
                    self.print_error(f"Collaborator missing username in repository {repo_name}")
                    continue
                
                resource_address = f'module.collaborators.github_repository_collaborator.collaborator["{repo_name}-{username}"]'
                resource_id = f'{repo_name}:{username}'
                
                if self.import_resource(resource_address, resource_id):
                    imported += 1
        
        return imported
        
    def run(self):
        """Run the import process"""
        print("=" * 60)
        print("GitHub Access Management Import Script")
        print(f"Organization: {self.org_name}")
        print("=" * 60)
        
        # Check prerequisites
        if not self.check_prerequisites():
            return 1
            
        # Load configuration files
        try:
            with open('teams.yaml', 'r') as f:
                teams_config = yaml.safe_load(f)
            
            # Load collaborators.yaml if it exists
            collaborators_config = {'repositories': []}
            if os.path.exists('collaborators.yaml'):
                with open('collaborators.yaml', 'r') as f:
                    collaborators_config = yaml.safe_load(f) or {'repositories': []}
        except Exception as e:
            self.print_error(f"Failed to load configuration files: {e}")
            return 1
            
        # Fetch teams from GitHub
        self.print_header("Step 1: Fetching teams from GitHub")
        teams = self.fetch_teams()
        print(f"  Found {len(teams)} teams in GitHub")
        
        # Import resources
        teams_imported = self.import_teams(teams_config)
        members_imported = self.import_team_members(teams_config)
        collabs_imported = self.import_collaborators(collaborators_config)
        
        # Summary
        print("\n" + "=" * 60)
        print("Import process complete!")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  Teams imported: {teams_imported}")
        print(f"  Team members imported: {members_imported}")
        print(f"  Collaborators imported: {collabs_imported}")
        
        print("\nNext steps:")
        print("1. Run 'terraform state list' to verify imports")
        print("2. Run 'terraform plan' to check for any differences")
        print("3. Review the plan output carefully")
        print("4. If plan looks good, you can now use 'terraform apply'")
        
        return 0

def main():
    # Get organization name
    org_name = sys.argv[1] if len(sys.argv) > 1 else 'observability-s'
    
    # Get GitHub token from environment
    github_token = os.environ.get('GITHUB_TOKEN')
    
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable not set")
        print(f"Usage: export GITHUB_TOKEN=your_token && python3 {sys.argv[0]} <org-name>")
        return 1
        
    # Run importer
    importer = TerraformImporter(org_name, github_token)
    return importer.run()

if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
