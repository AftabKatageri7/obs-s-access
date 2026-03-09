"""Command-line interface for GitHub Collaborator Manager.

This module provides the CLI entry point and argument parsing for the tool.
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Optional

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass

from .config_loader import load_team_configs
from .github_client import GitHubClient
from .manager import CollaboratorManager
from .audit_logger import AuditLogger
from .models import ValidationResult


def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.
    
    Args:
        args: List of arguments (defaults to sys.argv[1:])
        
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="github-collab-manager",
        description="Manage GitHub repository collaborators using YAML team definitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage - Apply team configurations
  # (requires GITHUB_TOKEN and GITHUB_ORG environment variables)
  github-collab-manager --teams-dir ./teams

  # Dry run - Preview changes without applying them
  github-collab-manager --teams-dir ./teams --dry-run

  # Validate only - Check YAML syntax and structure without GitHub connection
  github-collab-manager --teams-dir ./teams --validate-only

  # Report stale collaborators - Show users not in any team config
  github-collab-manager --teams-dir ./teams --report-stale

  # Remove stale collaborators - Clean up users not in team configs
  github-collab-manager --teams-dir ./teams --remove-stale --dry-run
  github-collab-manager --teams-dir ./teams --remove-stale  # Actually remove

  # Use custom GitHub credentials
  github-collab-manager --teams-dir ./teams \\
    --github-token ghp_xxxxxxxxxxxx \\
    --github-org my-organization

  # Enable debug logging for troubleshooting
  github-collab-manager --teams-dir ./teams --log-level DEBUG

  # Complete example with all options
  github-collab-manager \\
    --teams-dir ./config/teams \\
    --github-token ghp_xxxxxxxxxxxx \\
    --github-org observability-s \\
    --dry-run \\
    --report-stale \\
    --log-level INFO

Environment Variables:
  GITHUB_TOKEN    GitHub personal access token (required unless --github-token used)
  GITHUB_ORG      GitHub organization name (required unless --github-org used)
  LOG_LEVEL       Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)

Required Permissions:
  Your GitHub token must have the following scopes:
  - repo (full control of private repositories)
  - read:org (read organization membership)

Exit Codes:
  0   Success - all operations completed successfully
  1   Failure - validation errors, API errors, or operation failures
  130 Interrupted - user cancelled with Ctrl+C

For more information, visit: https://github.com/observability-s/obs-s-access
        """
    )
    
    parser.add_argument(
        "--teams-dir",
        type=str,
        required=True,
        help="Directory containing team YAML configuration files"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them to GitHub"
    )
    
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate team configurations without connecting to GitHub"
    )
    
    parser.add_argument(
        "--remove-stale",
        action="store_true",
        help="Remove collaborators not defined in any team configuration"
    )
    
    parser.add_argument(
        "--report-stale",
        action="store_true",
        help="Report stale collaborators without removing them"
    )
    
    parser.add_argument(
        "--github-token",
        type=str,
        help="GitHub personal access token (overrides GITHUB_TOKEN env var)"
    )
    
    parser.add_argument(
        "--github-org",
        type=str,
        help="GitHub organization name (overrides GITHUB_ORG env var)"
    )
    
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (overrides LOG_LEVEL env var)"
    )
    
    return parser.parse_args(args)


def get_github_credentials(args: argparse.Namespace) -> tuple[Optional[str], Optional[str]]:
    """Get GitHub credentials from arguments or environment.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Tuple of (token, org_name)
    """
    # Token: CLI arg > env var
    token = args.github_token or os.getenv("GITHUB_TOKEN")
    
    # Organization: CLI arg > env var
    org_name = args.github_org or os.getenv("GITHUB_ORG")
    
    return token, org_name


def get_log_level(args: argparse.Namespace) -> str:
    """Get log level from arguments or environment.
    
    Args:
        args: Parsed command-line arguments
        
    Returns:
        Log level string (DEBUG, INFO, WARNING, ERROR)
    """
    # CLI arg > env var > default INFO
    return args.log_level or os.getenv("LOG_LEVEL", "INFO")


def validate_teams_directory(teams_dir: str, logger: AuditLogger) -> bool:
    """Validate that teams directory exists and contains YAML files.
    
    Args:
        teams_dir: Path to teams directory
        logger: Audit logger instance
        
    Returns:
        True if valid, False otherwise
    """
    path = Path(teams_dir)
    
    if not path.exists():
        logger.log_error(
            f"Teams directory does not exist: {teams_dir}",
            teams_dir=teams_dir
        )
        return False
    
    if not path.is_dir():
        logger.log_error(
            f"Teams path is not a directory: {teams_dir}",
            teams_dir=teams_dir
        )
        return False
    
    # Check for YAML files
    yaml_files = list(path.glob("*.yaml")) + list(path.glob("*.yml"))
    if not yaml_files:
        logger.log_error(
            f"No YAML files found in teams directory: {teams_dir}",
            teams_dir=teams_dir
        )
        return False
    
    logger.log_info(
        f"Found {len(yaml_files)} YAML file(s) in teams directory",
        teams_dir=teams_dir,
        file_count=len(yaml_files)
    )
    
    return True


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for the CLI.
    
    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    # Parse arguments
    args = parse_arguments(argv)
    
    # Initialize logger
    log_level = get_log_level(args)
    logger = AuditLogger(log_level=log_level)
    
    logger.log_info(
        "GitHub Collaborator Manager started",
        teams_dir=args.teams_dir,
        dry_run=args.dry_run,
        validate_only=args.validate_only,
        log_level=log_level
    )
    
    try:
        # Validate teams directory
        if not validate_teams_directory(args.teams_dir, logger):
            return 1
        
        # Load and validate team configurations
        logger.log_info(f"Loading team configurations from {args.teams_dir}")
        team_configs, validation_result = load_team_configs(args.teams_dir)
        
        if not validation_result.valid:
            logger.log_error(
                "Team configuration validation failed",
                error_count=len(validation_result.errors)
            )
            for error in validation_result.errors:
                logger.log_error(f"  - {error}")
            return 1
        
        if validation_result.warnings:
            for warning in validation_result.warnings:
                logger.log_warning(f"  - {warning}")
        
        logger.log_info(
            f"Successfully loaded {len(team_configs)} team configuration(s)",
            team_count=len(team_configs)
        )
        
        # If validate-only mode, exit here
        if args.validate_only:
            logger.log_info("Validation complete (--validate-only mode)")
            return 0
        
        # Get GitHub credentials
        token, org_name = get_github_credentials(args)
        
        if not token:
            logger.log_error(
                "GitHub token not provided",
                error_type="MissingCredentials",
                help_text="Set GITHUB_TOKEN environment variable or use --github-token argument",
                example="export GITHUB_TOKEN=ghp_xxxxxxxxxxxx"
            )
            print("\n❌ ERROR: GitHub token is required", file=sys.stderr)
            print("   Set it using: export GITHUB_TOKEN=ghp_xxxxxxxxxxxx", file=sys.stderr)
            print("   Or use: --github-token ghp_xxxxxxxxxxxx", file=sys.stderr)
            print("   Get a token at: https://github.com/settings/tokens", file=sys.stderr)
            return 1
        
        if not org_name:
            logger.log_error(
                "GitHub organization not provided",
                error_type="MissingCredentials",
                help_text="Set GITHUB_ORG environment variable or use --github-org argument",
                example="export GITHUB_ORG=my-organization"
            )
            print("\n❌ ERROR: GitHub organization name is required", file=sys.stderr)
            print("   Set it using: export GITHUB_ORG=my-organization", file=sys.stderr)
            print("   Or use: --github-org my-organization", file=sys.stderr)
            return 1
        
        # Initialize GitHub client
        logger.log_info(f"Connecting to GitHub organization: {org_name}")
        github_client = GitHubClient(token, org_name, logger)
        
        if not github_client.authenticate():
            logger.log_error(
                "Failed to authenticate with GitHub",
                error_type="AuthenticationFailed",
                token_prefix=token[:7] + "..." if len(token) > 7 else "***",
                org_name=org_name
            )
            print("\n❌ ERROR: GitHub authentication failed", file=sys.stderr)
            print(f"   Organization: {org_name}", file=sys.stderr)
            print(f"   Token: {token[:7]}...", file=sys.stderr)
            print("\n   Possible causes:", file=sys.stderr)
            print("   1. Invalid or expired token", file=sys.stderr)
            print("   2. Token lacks required permissions (repo, read:org)", file=sys.stderr)
            print("   3. Organization name is incorrect", file=sys.stderr)
            print("   4. Network connectivity issues", file=sys.stderr)
            print("\n   Verify your token at: https://github.com/settings/tokens", file=sys.stderr)
            return 1
        
        logger.log_info("Successfully authenticated with GitHub")
        
        # Log rate limit status
        rate_limit = github_client.get_rate_limit()
        logger.log_info(
            f"GitHub API rate limit: {rate_limit['remaining']}/{rate_limit['limit']} remaining, "
            f"resets at {rate_limit['reset_timestamp']}",
            rate_limit_remaining=rate_limit['remaining'],
            rate_limit_total=rate_limit['limit']
        )
        
        # Initialize collaborator manager
        manager = CollaboratorManager(github_client, logger)
        
        # Process team configurations
        logger.log_info("Processing team configurations")
        repo_access = manager.process_team_configs(team_configs)
        
        # Apply access grants
        if args.dry_run:
            logger.log_info("Running in DRY RUN mode - no changes will be applied")
        
        results = manager.apply_access_grants(repo_access, dry_run=args.dry_run)
        
        # Handle stale collaborator detection and removal
        stale_results = []
        if args.remove_stale or args.report_stale:
            logger.log_info("Detecting stale collaborators")
            stale_collaborators = manager.detect_stale_collaborators(repo_access)
            
            if stale_collaborators:
                total_stale = sum(len(users) for users in stale_collaborators.values())
                logger.log_info(
                    f"Found {total_stale} stale collaborator(s) across {len(stale_collaborators)} repositories"
                )
                
                if args.report_stale:
                    # Report only mode
                    logger.log_info("Stale collaborators (--report-stale mode):")
                    for repo, users in sorted(stale_collaborators.items()):
                        logger.log_info(f"  {repo}: {', '.join(users)}")
                
                if args.remove_stale:
                    # Remove stale collaborators
                    logger.log_info("Removing stale collaborators")
                    stale_results = manager.remove_stale_collaborators(
                        stale_collaborators,
                        dry_run=args.dry_run
                    )
            else:
                logger.log_info("No stale collaborators found")
        
        # Analyze results and generate summary
        all_results = results + stale_results
        success_count = sum(1 for r in all_results if r.success)
        failure_count = len(all_results) - success_count
        
        # Categorize operations by type
        additions = sum(1 for r in results if r.success and r.action == "add")
        updates = sum(1 for r in results if r.success and r.action == "update")
        no_changes = sum(1 for r in results if r.success and r.action == "no-op")
        removals = sum(1 for r in stale_results if r.success and r.action == "remove")
        
        logger.log_info(
            f"Operation complete: {success_count} successful, {failure_count} failed",
            total_operations=len(all_results),
            successful=success_count,
            failed=failure_count,
            additions=additions,
            updates=updates,
            no_changes=no_changes,
            removals=removals
        )
        
        # Print operation summary
        print("\n" + "="*60)
        print("OPERATION SUMMARY")
        print("="*60)
        print(f"Total operations:     {len(all_results)}")
        print(f"  ✅ Successful:      {success_count}")
        print(f"  ❌ Failed:          {failure_count}")
        print()
        print("Operation breakdown:")
        print(f"  ➕ Additions:       {additions}")
        print(f"  🔄 Updates:         {updates}")
        print(f"  ⏭️  No changes:      {no_changes}")
        if removals > 0:
            print(f"  🗑️  Removals:        {removals}")
        print()
        
        # Show affected repositories
        affected_repos = set(r.repository for r in all_results if r.success)
        if affected_repos:
            print(f"Affected repositories: {len(affected_repos)}")
            for repo in sorted(affected_repos):
                repo_results = [r for r in all_results if r.repository == repo and r.success]
                print(f"  • {repo}: {len(repo_results)} operation(s)")
        print("="*60)
        
        # Exit with appropriate code
        if failure_count > 0:
            logger.log_warning(
                f"{failure_count} operation(s) failed",
                failed_count=failure_count,
                total_count=len(all_results)
            )
            print(f"\n⚠️  WARNING: {failure_count} operation(s) failed", file=sys.stderr)
            print("   Check the audit log above for details", file=sys.stderr)
            if args.dry_run:
                print("   Note: Running in dry-run mode - no actual changes were made", file=sys.stderr)
            return 1
        
        logger.log_info("All operations completed successfully")
        if args.dry_run:
            print("\n✅ Dry-run complete: All operations would succeed")
        else:
            print(f"\n✅ Success: {success_count} operation(s) completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.log_warning("Operation interrupted by user (Ctrl+C)")
        print("\n\n⚠️  Operation interrupted by user", file=sys.stderr)
        print("   No changes were applied", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
        
    except FileNotFoundError as e:
        logger.log_error(
            f"File not found: {str(e)}",
            error_type="FileNotFoundError",
            error_message=str(e)
        )
        print(f"\n❌ ERROR: File not found - {str(e)}", file=sys.stderr)
        print("   Check that all paths are correct", file=sys.stderr)
        return 1
        
    except PermissionError as e:
        logger.log_error(
            f"Permission denied: {str(e)}",
            error_type="PermissionError",
            error_message=str(e)
        )
        print(f"\n❌ ERROR: Permission denied - {str(e)}", file=sys.stderr)
        print("   Check file and directory permissions", file=sys.stderr)
        return 1
        
    except Exception as e:
        logger.log_error(
            f"Unexpected error: {str(e)}",
            error_type=type(e).__name__,
            error_message=str(e)
        )
        print(f"\n❌ ERROR: Unexpected error occurred", file=sys.stderr)
        print(f"   Type: {type(e).__name__}", file=sys.stderr)
        print(f"   Message: {str(e)}", file=sys.stderr)
        print("\n   Please report this issue with the full error log", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
