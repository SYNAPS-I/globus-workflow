import argparse
import globus_sdk
from globus_sdk.globus_app import UserApp
from globus_sdk import FlowsClient, TransferClient
from globus_sdk.scopes import TransferScopes, FlowsScopes, ComputeScopes, GCSCollectionScopeBuilder, MutableScope
from globus_compute_sdk import Client
from globus_sdk import SpecificFlowClient
import json
import yaml
from pathlib import Path


class FlowConfig:
    """Configuration and state for Globus flow operations."""
    
    def __init__(self, config_path: Path = None):
        if config_path is None:
            config_path = Path(__file__).parent / "flow_config.yaml"
        
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        
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
        self.pi_precision = config["flow"]["pi_precision"]
        self.command_pbs_job_script = config["flow"]["command_pbs_job_script"]
        self.command_prune_dir_script = config["flow"]["command_prune_dir_script"]
        
        # Runtime state (populated during execution)
        self.flow = None
        self.compute_client = None
        self.func_id_file_process = None
        self.func_id_pi_calc = None
        self.func_id_run_terminal_command = None
        
        # Build scopes
        self._build_scopes()
    
    def _build_scopes(self):
        """Build data_access scopes for each collection."""
        source_data_access = GCSCollectionScopeBuilder(self.source_collection_id).data_access
        dest_data_access = GCSCollectionScopeBuilder(self.dest_collection_id).data_access
        
        # Transfer scope with data_access dependencies
        self.transfer_scope = MutableScope(TransferScopes.all)
        self.transfer_scope.add_dependency(source_data_access)
        self.transfer_scope.add_dependency(dest_data_access)
        
        self.scope_requirements = {
            TransferScopes.resource_server: [self.transfer_scope],
            FlowsScopes.resource_server: [FlowsScopes.manage_flows, FlowsScopes.run],
            # Use the official Compute resource server and scope
            ComputeScopes.resource_server: [ComputeScopes.all]
        }


def deploy_flow(cfg: FlowConfig):
    """Deploy a new Globus flow."""
    app = UserApp("ComputeFlowApp", client_id=cfg.client_id, scope_requirements=cfg.scope_requirements)
    flows_client = FlowsClient(app=app)

    # 1. Load the flow definition
    with open("flow.json", "r") as f:
        flow_definition = json.load(f)

    # Create/Deploy the Flow
    cfg.flow = flows_client.create_flow(
        title="Ptychography fine tuning flow",
        definition=flow_definition,
        input_schema={} # Optional: define schema for validation
    )
    cfg.flow_id = cfg.flow["id"]
    print(f"Flow deployed! ID: {cfg.flow_id}")


# Define and Register the function
def process_file(input_path):
    import os
    # Example: count lines in the transferred file
    with open(input_path, 'r') as f:
        return f"Line count: {len(f.readlines())}"


# Define and Register another function
def pi_calc(num_points=10**8):
    from random import random
    inside = 0
    for i in range(num_points):
        x, y = random(), random()  # Drop a random point in the box.
        if x**2 + y**2 < 1:        # Count points within the circle.
            inside += 1
    return (inside*4 / num_points)


def run_terminal_command(command_pbs_job_script):
    import subprocess
    try:
        # Executes the command and captures the output
        result = subprocess.run(
            command_pbs_job_script, 
            shell=True, 
            capture_output=True, 
            text=True
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)


def deploy_funcs(cfg: FlowConfig):
    """Deploy compute functions to Globus."""
    cfg.compute_client = Client()
    cfg.func_id_file_process = cfg.compute_client.register_function(process_file)
    cfg.func_id_pi_calc = cfg.compute_client.register_function(pi_calc)
    cfg.func_id_run_terminal_command = cfg.compute_client.register_function(run_terminal_command)


def run_orchestrated_flow(cfg: FlowConfig):
    """Run the orchestrated Globus flow."""
    # Build flow-specific scope with transfer data_access dependencies
    flow_scope = MutableScope(f"https://auth.globus.org/scopes/{cfg.flow_id}/flow_{cfg.flow_id.replace('-', '_')}_user")
    flow_scope.add_dependency(cfg.transfer_scope)
    
    # Add flow scope to requirements
    flow_scope_requirements = dict(cfg.scope_requirements)
    flow_scope_requirements[cfg.flow_id] = [flow_scope]
    
    app = UserApp("ComputeFlowApp", client_id=cfg.client_id, scope_requirements=flow_scope_requirements)

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
        "compute_endpoint_id": cfg.compute_endpoint_id,
        "compute_function_id": cfg.func_id_run_terminal_command
    }
    
    # Start the flow
    run = flows_client.run_flow(
        body = flow_input,  # Passing data TO the flow
        label = "Ptychography fine tuning flow run"
    )
    print(f"Flow sequence started! Run ID: {run['run_id']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Globus flow for ptychography fine tuning")
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=Path.cwd() / "flow_config.yaml",
        help="Path to the configuration file (default: ./flow_config.yaml)"
    )
    args = parser.parse_args()
    
    cfg = FlowConfig(config_path=Path(args.config))
    
    if cfg.flow_id is None:
        deploy_flow(cfg)
    if cfg.func_id_run_terminal_command is None:
        deploy_funcs(cfg)
    run_orchestrated_flow(cfg)

