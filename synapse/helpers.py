import binascii
import gzip
import io
import json

from .const import SynapseApplication

def hex_to_object(hex_str: str) -> SynapseApplication:
    """Convert a hex-encoded gzipped JSON string to a SynapseApplication object.

    Used during app discovery to decode compressed application metadata
    sent over the event bus. The data is hex-encoded for safe transmission.

    Args:
        hex_str: Hex-encoded gzipped JSON string containing app metadata

    Returns:
        SynapseApplication: Decoded application metadata object

    Raises:
        ValueError: If the hex string cannot be decoded or JSON is invalid
    """
    compressed_data = binascii.unhexlify(hex_str)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed_data)) as f:
        json_str = f.read().decode('utf-8')
    return json.loads(json_str)
