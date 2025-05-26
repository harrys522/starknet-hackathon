import json
import traceback
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.account.account import Account
from starknet_py.net.models import StarknetChainId, InvokeV3
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.constants import (
    DEFAULT_DEPLOYER_ADDRESS,
)
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.hash.address import compute_address
from starknet_py.net.client_models import Call, ResourceBounds, ResourceBoundsMapping
from starknet_py.contract import Contract
import time
from starknet_py.common import create_sierra_compiled_contract
from pathlib import Path
from utils import FALCON_KEY_REGISTRY_ABI

# --- Configuration ---
# Class hashes are defined as strings with "0x" prefix
FALCON_KEY_REGISTRY_CONTRACT_HASH = (  # Renamed in app.py to FALCON_KEY_REGISTRY_CLASS_HASH_HEX
    "0x022A351AB5F1AC13352A3792BE246D8C6513D9029F3674608AC4CD7944AA702E"
)
FALCON_ADDRESS_BASED_VERIFIER_CONTRACT_HASH = (
    "0x0396507525F71D979D306DF5B72C568DFCCA173158086D73806E496B054670A3"
)
ESCROW_CONTRACT_HASH = (
    "0x03C435E79CB8246F1351C5CFE92DD7D1FF6D2A684395E5BC7D5F0792ED46B147"
)

# IMPORTANT: Configure your Node URL properly.
# Using a node that supports RPC v0.8.1+ is recommended for newer starknet-py versions.
NODE_URL = (
    "https://starknet-sepolia.public.blastapi.io/"  # Or your preferred Sepolia node
)
# NODE_URL = "https://rpc.starknet-testnet.lava.build:443"
CHAIN_ID = StarknetChainId.SEPOLIA

# DEFAULT_SIERRA_PATH = "./scripts/Utils/abi/moosh_id_FalconPublicKeyRegistry.contract_class.json"  # Contains ABI + Sierra
DEFAULT_CASM_PATH = (
    "./scripts/Utils/abi/moosh_id_FalconPublicKeyRegistry.contract_class.json"  # CASM
)
# moosh_id_FalconPublicKeyRegistry.compiled_contract_class.json


async def get_deployer_account(
    private_key_hex: str, account_address_hex: str
) -> Account | None:
    """
    Initializes and returns an Account instance for deploying contracts,
    using the provided private key and account address.
    """
    if not private_key_hex:
        print("Error: Deployer private key not provided.")
        return None
    if not account_address_hex:
        print("Error: Deployer account address not provided.")
        return None
    if not NODE_URL or NODE_URL == "YOUR_STARKNET_NODE_URL":  # Placeholder check
        print("CRITICAL Error: NODE_URL is not configured or is a placeholder.")
        return None

    client = FullNodeClient(node_url=NODE_URL)
    try:
        key_pair = KeyPair.from_private_key(private_key_hex)

        account = Account(
            client=client,
            address=account_address_hex,
            key_pair=key_pair,
            chain=CHAIN_ID,
        )
        print(f"Deployer account initialized for address: {hex(account.address)}")
        return account
    except ValueError as e:
        print(f"Error: Invalid private key or account address format: {e}")
        return None
    except Exception as e:
        print(f"Error creating deployer account object: {e}")
        traceback.print_exc()
        return None


# def read_contract(file_name: Path) -> str:
#     """
#     Return contents of file_name from directory.
#     """
#     return (file_name).read_text("utf-8")


async def deploy_new_contract_instance(
    class_hash_hex: str,
    deployer_private_key_hex: str,
    deployer_account_address_hex: str,
    constructor_args: list | None = None,
) -> tuple[str | None, str | None]:
    """
    Deploys a new contract instance using its class hash via the Universal Deployer Contract (UDC).
    Returns (deployed_contract_address_hex, transaction_hash_hex) or (error_message_str, None).
    """
    deployer_account = await get_deployer_account(
        deployer_private_key_hex, deployer_account_address_hex
    )
    if not deployer_account:
        print("Deployer account failed:", deployer_account)
        return "Error: Deployer account not initialized.", None

    # compiled_contract = read_contract(
    #     "./Utils/abi/moosh_id_FalconPublicKeyRegistry.contract_class.json"
    # )
    # abi = create_sierra_compiled_contract(compiled_contract).abi

    # Deploy using pre-declared contract_hash
    resp = await Contract.deploy_contract_v3(
        account=deployer_account,
        class_hash=class_hash_hex,
        constructor_args=[],
        l1_resource_bounds=ResourceBounds(
            max_amount=int(30000), max_price_per_unit=int(25 * 10**14)
        ),
        abi=FALCON_KEY_REGISTRY_ABI,
    )
    time.sleep(5)
    print("Deploy contract attempt complete")
    tx = await resp.wait_for_acceptance()
    print("Successfully deployed")

    contract_address = hex(tx.deployed_contract.address)
    url = f"https://sepolia.starkscan.co/contract/{contract_address}"

    tx_hash_hex = hex(tx.hash)
    print("output: ", resp, tx)
    print("Contract deployed successfully:", url)
    return (url, tx_hash_hex)
