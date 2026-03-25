"""Collaborator management logic for GitHub repositories and projects.

This module handles the business logic for processing team configurations,
resolving conflicts, detecting changes, and applying access grants to both
repositories and GitHub Projects v2.
"""

from typing import List, Dict, Set, Tuple, Optional
from collections import defaultdict

from .models import TeamConfig, AccessGrant, OperationResult, ProjectConfig
from .github_client import GitHubClient
from .projects_client import ProjectsClient
from .audit_logger import AuditLogger


class CollaboratorManager:
    """Manages collaborator access across GitHub repositories and projects."""
    
    def __init__(self, github_client: GitHubClient, logger: AuditLogger,
                 projects_client: Optional[ProjectsClient] = None):
        """Initialize collaborator manager.
        
        Args:
            github_client: Authenticated GitHub client
            logger: Audit logger instance
            projects_client: Optional GitHub Projects v2 client for project access management
        """
        self.github_client = github_client
        self.logger = logger
        self.projects_client = projects_client
    
    def process_team_configs(self, team_configs: List[TeamConfig]) -> Dict[str, Dict[str, str]]:
        """Process team configurations and resolve conflicts.
        
        Team configs are processed in alphabetical order by source file.
        For duplicate user-repository pairs, the last file wins.
        
        Args:
            team_configs: List of TeamConfig objects
            
        Returns:
            Dictionary mapping repository -> {user: role}
        """
        # Sort team configs by source file (alphabetical order)
        sorted_configs = sorted(team_configs, key=lambda tc: tc.source_file)
        
        self.logger.log_info(
            f"Processing {len(sorted_configs)} team configurations",
            team_count=len(sorted_configs)
        )
        
        # Track all access grants with source information
        # Key: (user, repository) -> (role, source_file, team_name)
        access_map: Dict[Tuple[str, str], Tuple[str, str, str]] = {}
        
        # Process each team config in order
        for team_config in sorted_configs:
            grants = team_config.get_access_grants()
            
            self.logger.log_debug(
                f"Processing team '{team_config.team_name}' from {team_config.source_file}",
                team_name=team_config.team_name,
                source_file=team_config.source_file,
                grant_count=len(grants)
            )
            
            for grant in grants:
                key = (grant.user, grant.repository)
                
                # Check if this is a conflict (overwrite)
                if key in access_map:
                    old_role, old_file, old_team = access_map[key]
                    self.logger.log_warning(
                        f"Conflict: {grant.user} access to {grant.repository} "
                        f"changed from {old_role} (in {old_file}) "
                        f"to {grant.role} (in {team_config.source_file})",
                        user=grant.user,
                        repository=grant.repository,
                        old_role=old_role,
                        new_role=grant.role,
                        old_source=old_file,
                        new_source=team_config.source_file
                    )
                
                # Last wins - overwrite with current grant
                access_map[key] = (grant.role, team_config.source_file, team_config.team_name)
        
        # Convert to repository-centric structure
        repo_access: Dict[str, Dict[str, str]] = defaultdict(dict)
        for (user, repository), (role, source_file, team_name) in access_map.items():
            repo_access[repository][user] = role
        
        self.logger.log_info(
            f"Processed access grants for {len(repo_access)} repositories",
            repository_count=len(repo_access),
            total_grants=len(access_map)
        )
        
        return dict(repo_access)
    
    def detect_changes(self, repository: str, desired_access: Dict[str, str]) -> Tuple[
        List[Tuple[str, str]],  # additions: [(user, role)]
        List[Tuple[str, str]],  # updates: [(user, role)]
        List[str]               # no-ops: [user]
    ]:
        """Detect what changes need to be made to a repository.
        
        Args:
            repository: Repository name
            desired_access: Dictionary of {user: role} for desired state
            
        Returns:
            Tuple of (additions, updates, no-ops)
        """
        additions = []
        updates = []
        no_ops = []
        
        # Get repository object
        repo = self.github_client.get_repository(repository)
        if not repo:
            self.logger.log_error(
                f"Cannot detect changes - repository not found: {repository}",
                repository=repository
            )
            return additions, updates, no_ops
        
        # Get current collaborators
        current_collaborators = self.github_client.list_collaborators(repo)
        
        # Analyze each desired access grant
        for user, desired_role in desired_access.items():
            if user not in current_collaborators:
                # User not currently a collaborator - addition
                additions.append((user, desired_role))
                self.logger.log_debug(
                    f"Change detected: ADD {user} to {repository} with {desired_role}",
                    action="add",
                    user=user,
                    repository=repository,
                    role=desired_role
                )
            elif current_collaborators[user] != desired_role:
                # User exists but with different role - update
                updates.append((user, desired_role))
                self.logger.log_debug(
                    f"Change detected: UPDATE {user} on {repository} "
                    f"from {current_collaborators[user]} to {desired_role}",
                    action="update",
                    user=user,
                    repository=repository,
                    old_role=current_collaborators[user],
                    new_role=desired_role
                )
            else:
                # User exists with correct role - no-op
                no_ops.append(user)
                self.logger.log_debug(
                    f"No change needed: {user} already has {desired_role} on {repository}",
                    action="no-op",
                    user=user,
                    repository=repository,
                    role=desired_role
                )
        
        self.logger.log_info(
            f"Change detection for {repository}: "
            f"{len(additions)} additions, {len(updates)} updates, {len(no_ops)} no-ops",
            repository=repository,
            additions=len(additions),
            updates=len(updates),
            no_ops=len(no_ops)
        )
        
        return additions, updates, no_ops
    
    def apply_access_grants(self, repo_access: Dict[str, Dict[str, str]], 
                           dry_run: bool = False) -> List[OperationResult]:
        """Apply access grants to GitHub repositories.
        
        Args:
            repo_access: Dictionary mapping repository -> {user: role}
            dry_run: If True, only log planned changes without applying
            
        Returns:
            List of OperationResult objects
        """
        results = []
        
        self.logger.log_info(
            f"{'[DRY RUN] ' if dry_run else ''}Applying access grants to {len(repo_access)} repositories",
            dry_run=dry_run,
            repository_count=len(repo_access)
        )
        
        for repository, user_roles in repo_access.items():
            # Get repository object
            repo = self.github_client.get_repository(repository)
            
            if not repo:
                # Repository doesn't exist - log error for each user
                for user, role in user_roles.items():
                    result = OperationResult(
                        success=False,
                        action="add_collaborator" if dry_run else "error",
                        user=user,
                        repository=repository,
                        role=role,
                        message=f"Repository not found: {repository}"
                    )
                    results.append(result)
                    self.logger.log_error(
                        f"Cannot apply access - repository not found: {repository}",
                        repository=repository,
                        user=user,
                        role=role
                    )
                continue
            
            # Detect changes needed
            additions, updates, no_ops = self.detect_changes(repository, user_roles)
            
            # Process additions
            for user, role in additions:
                if dry_run:
                    result = OperationResult(
                        success=True,
                        action="add_collaborator_dry_run",
                        user=user,
                        repository=repository,
                        role=role,
                        message=f"[DRY RUN] Would add {user} to {repository} with {role}"
                    )
                    self.logger.log_info(
                        f"[DRY RUN] Would add {user} to {repository} with {role}",
                        action="add_collaborator_dry_run",
                        user=user,
                        repository=repository,
                        role=role
                    )
                else:
                    result = self.github_client.add_collaborator(repo, user, role)
                    self.logger.log_operation_result(result)
                
                results.append(result)
            
            # Process updates
            for user, role in updates:
                if dry_run:
                    result = OperationResult(
                        success=True,
                        action="update_collaborator_dry_run",
                        user=user,
                        repository=repository,
                        role=role,
                        message=f"[DRY RUN] Would update {user} on {repository} to {role}"
                    )
                    self.logger.log_info(
                        f"[DRY RUN] Would update {user} on {repository} to {role}",
                        action="update_collaborator_dry_run",
                        user=user,
                        repository=repository,
                        role=role
                    )
                else:
                    result = self.github_client.update_collaborator(repo, user, role)
                    self.logger.log_operation_result(result)
                
                results.append(result)
            
            # Log no-ops
            for user in no_ops:
                role = user_roles[user]
                self.logger.log_debug(
                    f"No change needed for {user} on {repository} (already {role})",
                    action="no-op",
                    user=user,
                    repository=repository,
                    role=role
                )
        
        # Summary
        success_count = sum(1 for r in results if r.success)
        failure_count = len(results) - success_count
        
        self.logger.log_info(
            f"{'[DRY RUN] ' if dry_run else ''}Completed: "
            f"{success_count} successful, {failure_count} failed",
            dry_run=dry_run,
            total=len(results),
            success=success_count,
            failure=failure_count
        )
        
        return results
    
    def detect_stale_collaborators(self, repo_access: Dict[str, Dict[str, str]]) -> Dict[str, List[str]]:
        """Detect collaborators not defined in any team configuration.
        
        Args:
            repo_access: Dictionary mapping repository -> {user: role}
            
        Returns:
            Dictionary mapping repository -> list of stale usernames
        """
        stale_collaborators = {}
        
        self.logger.log_info(
            f"Detecting stale collaborators across {len(repo_access)} repositories",
            repository_count=len(repo_access)
        )
        
        for repository, desired_users in repo_access.items():
            # Get repository object
            repo = self.github_client.get_repository(repository)
            
            if not repo:
                self.logger.log_warning(
                    f"Cannot detect stale collaborators - repository not found: {repository}",
                    repository=repository
                )
                continue
            
            # Get current collaborators
            current_collaborators = self.github_client.list_collaborators(repository)
            
            if current_collaborators is None:
                self.logger.log_warning(
                    f"Cannot detect stale collaborators - failed to list collaborators: {repository}",
                    repository=repository
                )
                continue
            
            # Find collaborators not in desired set
            current_usernames = {collab.login for collab in current_collaborators}
            desired_usernames = set(desired_users.keys())
            stale = current_usernames - desired_usernames
            
            # Filter out organization members (they have implicit access)
            filtered_stale = self._filter_org_members(stale)
            
            if filtered_stale:
                stale_collaborators[repository] = sorted(filtered_stale)
                self.logger.log_info(
                    f"Found {len(filtered_stale)} stale collaborator(s) in {repository}",
                    repository=repository,
                    stale_count=len(filtered_stale),
                    stale_users=sorted(filtered_stale)
                )
        
        total_stale = sum(len(users) for users in stale_collaborators.values())
        self.logger.log_info(
            f"Stale collaborator detection complete: {total_stale} total across {len(stale_collaborators)} repositories",
            total_stale=total_stale,
            affected_repos=len(stale_collaborators)
        )
        
        return stale_collaborators
    
    def _filter_org_members(self, usernames: Set[str]) -> Set[str]:
        """Filter out organization members from a set of usernames.
        
        Organization members have implicit access and should not be removed.
        
        Args:
            usernames: Set of usernames to filter
            
        Returns:
            Set of usernames that are not organization members
        """
        if not usernames:
            return set()
        
        try:
            # Get organization members
            org = self.github_client._org
            if not org:
                self.logger.log_warning("Cannot filter org members - organization not available")
                return usernames
            
            org_members = {member.login for member in org.get_members()}
            
            # Return only non-members
            filtered = usernames - org_members
            
            if len(filtered) < len(usernames):
                removed_count = len(usernames) - len(filtered)
                self.logger.log_debug(
                    f"Filtered out {removed_count} organization member(s)",
                    filtered_count=removed_count
                )
            
            return filtered
            
        except Exception as e:
            self.logger.log_warning(
                f"Error filtering organization members: {e}. Proceeding without filtering.",
                error=str(e)
            )
            return usernames
    
    def remove_stale_collaborators(self, stale_collaborators: Dict[str, List[str]],
                                   dry_run: bool = False) -> List[OperationResult]:
        """Remove stale collaborators from repositories.
        
        Args:
            stale_collaborators: Dictionary mapping repository -> list of stale usernames
            dry_run: If True, only log planned removals without applying
            
        Returns:
            List of OperationResult objects
        """
        results = []
        
        total_removals = sum(len(users) for users in stale_collaborators.values())
        
        self.logger.log_info(
            f"{'[DRY RUN] ' if dry_run else ''}Removing {total_removals} stale collaborator(s) from {len(stale_collaborators)} repositories",
            dry_run=dry_run,
            total_removals=total_removals,
            repository_count=len(stale_collaborators)
        )
        
        for repository, usernames in stale_collaborators.items():
            for username in usernames:
                if dry_run:
                    # Dry run - just log the planned removal
                    result = OperationResult(
                        success=True,
                        action="remove_collaborator",
                        user=username,
                        repository=repository,
                        role="",  # Role not relevant for removal
                        message=f"[DRY RUN] Would remove {username} from {repository}"
                    )
                    results.append(result)
                    
                    self.logger.log_info(
                        f"[DRY RUN] Would remove stale collaborator: {username} from {repository}",
                        action="remove_collaborator",
                        user=username,
                        repository=repository,
                        dry_run=True
                    )
                else:
                    # Actually remove the collaborator
                    success = self.github_client.remove_collaborator(repository, username)
                    
                    result = OperationResult(
                        success=success,
                        action="remove_collaborator",
                        user=username,
                        repository=repository,
                        role="",
                        message=f"Removed {username} from {repository}" if success else f"Failed to remove {username} from {repository}"
                    )
                    results.append(result)
        
        # Summary
        success_count = sum(1 for r in results if r.success)
        failure_count = len(results) - success_count
        
        self.logger.log_info(
            f"{'[DRY RUN] ' if dry_run else ''}Stale collaborator removal complete: "
            f"{success_count} successful, {failure_count} failed",
            dry_run=dry_run,
            total=len(results),
            success=success_count,
            failure=failure_count
        )
        
        return results
    
    def apply_project_access(self, team_configs: List[TeamConfig],
                            organization: str, dry_run: bool = False) -> List[str]:
        """Apply project access grants from team configurations.
        
        Args:
            team_configs: List of TeamConfig objects with project definitions
            organization: Organization name
            dry_run: If True, only log planned changes without applying
            
        Returns:
            List of error messages (empty if all successful)
        """
        if not self.projects_client:
            self.logger.log_warning("Projects client not initialized - skipping project access")
            return ["Projects client not initialized"]
        
        errors = []
        
        # Sort team configs by source file (alphabetical order for deterministic processing)
        sorted_configs = sorted(team_configs, key=lambda tc: tc.source_file)
        
        # Count total project grants to process
        total_grants = sum(
            len(tc.users) * len(tc.projects)
            for tc in sorted_configs
            if tc.projects
        )
        
        if total_grants == 0:
            self.logger.log_info("No project access grants to process")
            return errors
        
        self.logger.log_info(
            f"{'[DRY RUN] ' if dry_run else ''}Processing {total_grants} project access grant(s) from {len(sorted_configs)} team(s)",
            dry_run=dry_run,
            total_grants=total_grants,
            team_count=len(sorted_configs)
        )
        
        # Process each team configuration
        for team_config in sorted_configs:
            if not team_config.projects:
                continue
            
            self.logger.log_debug(
                f"Processing project access for team '{team_config.team_name}'",
                team_name=team_config.team_name,
                source_file=team_config.source_file,
                project_count=len(team_config.projects),
                user_count=len(team_config.users)
            )
            
            # Process each project in the team configuration
            for project_config in team_config.projects:
                # Determine project type and fetch project list
                project_type = "unknown"  # Initialize to handle errors before type is determined
                try:
                    if project_config.repository:
                        # Repository-level project
                        projects = self.projects_client.list_repository_projects(
                            organization, project_config.repository
                        )
                        project_type = "repository"
                    else:
                        # Organization-level project
                        projects = self.projects_client.list_organization_projects(organization)
                        project_type = "organization"
                    
                    # Find the specific project by number
                    project = next(
                        (p for p in projects if p['number'] == project_config.number),
                        None
                    )
                    
                    if not project:
                        error_msg = (
                            f"Project #{project_config.number} not found in "
                            f"{'repository ' + project_config.repository if project_config.repository else 'organization'}"
                        )
                        errors.append(error_msg)
                        self.logger.log_error(
                            error_msg,
                            project_number=project_config.number,
                            project_type=project_type,
                            repository=project_config.repository,
                            team_name=team_config.team_name
                        )
                        continue
                    
                    # Grant access to each user in the team
                    for username in team_config.users:
                        try:
                            # Get user ID (required for GraphQL mutations)
                            user_id = self.projects_client.get_user_id(username)
                            
                            if dry_run:
                                # Dry run - just log the planned operation
                                self.logger.log_info(
                                    f"[DRY RUN] Would grant {username} {project_config.permission.value} access to project #{project['number']}",
                                    action="grant_project_access_dry_run",
                                    user=username,
                                    project_number=project['number'],
                                    permission=project_config.permission.value,
                                    project_type=project_type,
                                    repository=project_config.repository
                                )
                            else:
                                # Actually grant/update project access
                                self.projects_client.update_project_collaborator(
                                    project['id'],
                                    user_id,
                                    project_config.permission.value
                                )
                                
                                # Log successful operation
                                self.logger.log_project_operation(
                                    action="grant_project_access",
                                    user=username,
                                    organization=organization,
                                    project_number=project['number'],
                                    permission=project_config.permission.value,
                                    result="success",
                                    message=f"Granted {username} {project_config.permission.value} access to project #{project['number']}",
                                    source_team=team_config.team_name,
                                    source_file=team_config.source_file,
                                    project_type=project_type,
                                    project_repository=project_config.repository
                                )
                        
                        except Exception as e:
                            error_msg = (
                                f"Failed to grant {username} access to project #{project_config.number}: {e}"
                            )
                            errors.append(error_msg)
                            self.logger.log_error(
                                error_msg,
                                error=e,
                                user=username,
                                project_number=project_config.number,
                                permission=project_config.permission.value,
                                project_type=project_type,
                                repository=project_config.repository
                            )
                
                except Exception as e:
                    error_msg = (
                        f"Failed to process project #{project_config.number}: {e}"
                    )
                    errors.append(error_msg)
                    self.logger.log_error(
                        error_msg,
                        error=e,
                        project_number=project_config.number,
                        project_type=project_type,
                        repository=project_config.repository
                    )
        
        # Summary
        success_count = total_grants - len(errors)
        self.logger.log_info(
            f"{'[DRY RUN] ' if dry_run else ''}Project access processing complete: "
            f"{success_count} successful, {len(errors)} failed",
            dry_run=dry_run,
            total=total_grants,
            success=success_count,
            failure=len(errors)
        )
        
        return errors

# Made with Bob
