"""Example Globus Compute function."""


def process_data(input_path: str, output_path: str, params: dict | None = None) -> dict:
    """Template compute function to be registered with Globus Compute.

    This function runs on a remote Globus Compute endpoint.

    Parameters
    ----------
    input_path : str
        Path to the input data on the compute endpoint.
    output_path : str
        Path to write results on the compute endpoint.
    params : dict, optional
        Additional processing parameters.

    Returns
    -------
    dict
        A summary of the processing result.
    """
    import os

    # Replace with actual processing logic
    result = {
        "input_path": input_path,
        "output_path": output_path,
        "params": params or {},
        "status": "completed",
        "files_processed": len(os.listdir(input_path)) if os.path.isdir(input_path) else 1,
    }
    return result
