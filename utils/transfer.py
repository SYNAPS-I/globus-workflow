"""Transfer task helpers."""

import globus_sdk

from utils.auth import get_transfer_client


def submit_transfer(
    source_endpoint: str,
    dest_endpoint: str,
    source_path: str,
    dest_path: str,
    label: str = "globus-workflow transfer",
    recursive: bool = True,
) -> globus_sdk.response.GlobusHTTPResponse:
    """Submit a Globus transfer task.

    Parameters
    ----------
    source_endpoint : str
        Source collection/endpoint UUID.
    dest_endpoint : str
        Destination collection/endpoint UUID.
    source_path : str
        Path on the source endpoint.
    dest_path : str
        Path on the destination endpoint.
    label : str
        Human-readable label for the task.
    recursive : bool
        Whether to transfer directories recursively.

    Returns
    -------
    GlobusHTTPResponse
        The transfer submission response containing the task_id.
    """
    tc = get_transfer_client()

    transfer_data = globus_sdk.TransferData(
        source_endpoint=source_endpoint,
        destination_endpoint=dest_endpoint,
        label=label,
    )
    transfer_data.add_item(source_path, dest_path, recursive=recursive)

    return tc.submit_transfer(transfer_data)
