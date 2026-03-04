import argparse
import json
import sys
import yaml
from pathlib import Path

import globus_sdk
from globus_sdk.scopes import MutableScope
from globus_sdk import SpecificFlowClient

from globus_auth import build_transfer_scope, build_scope_requirements, get_user_app
from utils import load_config


class FlowConfig:
    """Configuration and state for Globus flow operations."""
    
    def __init__(self, config_path: Path = None):
        if config_path is None:
            config_path = Path(__file__).parent / "flow_config.yaml"
        
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
        # Store raw config for scope-building helpers
        self._config = config
        
        # Collection/Endpoint IDs that need data_access consent
        self.source_collection_id = config["endpoints"]["source_collection_id"]
        self.dest_collection_id = config["endpoints"]["dest_collection_id"]
        self.compute_endpoint_id = config["endpoints"]["compute_endpoint_id"]
        
        # Paths
        self.source_path = config["paths"]["source_path"]
        self.dest_path = config["paths"]["dest_path"]
        self.model_source_path = config["paths"]["model_source_path"]
        self.model_dest_path = config["paths"]["model_dest_path"]
        
        # Globus client and flow settings
        self.client_id = config["globus"]["client_id"]
        self.flow_id = config["globus"]["flow_id"]
        self.app_name = config["globus"]["app_name"]
        self.flow_run_label = config["flow"]["run_label"]
        self.command_pbs_job_script = config["flow"]["command_pbs_job_script"]
        self.command_prune_dir_script = config["flow"]["command_prune_dir_script"]
        self.command_prune_post_finetuning = config["flow"]["command_prune_post_finetuning"]
        
        # Deployed function IDs (populated by deploy.py)
        deployment = config.get("deployment", {}) or {}
        self.func_id_run_terminal_command = deployment.get("func_id_run_terminal_command")
        
        # Build scopes
        self._build_scopes()
    
    def _build_scopes(self):
        """Build data_access scopes for each collection."""
        self.transfer_scope = build_transfer_scope(self._config)
        self.scope_requirements = build_scope_requirements(self._config)


def run_orchestrated_flow(cfg: FlowConfig):
    """Run the orchestrated Globus flow."""
    # Build flow-specific scope with transfer data_access dependencies
    flow_scope = MutableScope(f"https://auth.globus.org/scopes/{cfg.flow_id}/flow_{cfg.flow_id.replace('-', '_')}_user")
    flow_scope.add_dependency(cfg.transfer_scope)
    
    # Add flow scope to requirements
    flow_scope_requirements = dict(cfg.scope_requirements)
    flow_scope_requirements[cfg.flow_id] = [flow_scope]
    
    app = get_user_app(cfg._config, scope_requirements=flow_scope_requirements)

    # Initialization
    flows_client = SpecificFlowClient(flow_id=cfg.flow_id, app=app)

    # Define flow input
    flow_input = {
        "source_endpoint_id": cfg.source_collection_id,
        "destination_endpoint_id": cfg.dest_collection_id,
        "source_path": cfg.source_path,
        "destination_path": cfg.dest_path,
        "model_source_path": cfg.model_source_path,
        "model_destination_path": cfg.model_dest_path,
        "command_pbs_job_script": cfg.command_pbs_job_script,
        "command_prune_dir_script": cfg.command_prune_dir_script,
		"command_prune_post_finetuning": cfg.command_prune_post_finetuning,
        "compute_endpoint_id": cfg.compute_endpoint_id,
        "compute_function_id": cfg.func_id_run_terminal_command
    }
    
    # Start the flow
    run = flows_client.run_flow(
        body = flow_input,  # Passing data TO the flow
        label = cfg.flow_run_label
    )
    print(f"Flow sequence started! Run ID: {run['run_id']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Globus flow for ptychography fine tuning")
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=Path(__file__).parent / "flow_config.yaml",
        help="Path to the configuration file (default: ./flow_config.yaml)"
    )
    args = parser.parse_args()
    
    cfg = FlowConfig(config_path=Path(args.config))
    
    if not cfg.flow_id:
        print("ERROR: flow_id is not set. Run 'python deploy.py --flow' first.", file=sys.stderr)
        sys.exit(1)
    if not cfg.func_id_run_terminal_command:
        print("ERROR: Compute function IDs are not set. Run 'python deploy.py --funcs' first.", file=sys.stderr)
        sys.exit(1)

    run_orchestrated_flow(cfg)

