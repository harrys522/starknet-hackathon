# scripts/cairo_interactions.py
import json
import random
import json
import traceback
from typing import Optional, Tuple, List, Union

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
from utils import FALCON_KEY_REGISTRY_ABI, FALCON_VERIFIER_ABI, FALCON_ESCROW_ABI
from poseidon_py import poseidon_hash
from starknet_py.net.client_models import Call, ResourceBounds, ResourceBoundsMapping
from starknet_py.contract import Contract
from utils import (
    FALCON_KEY_REGISTRY_ABI,
    FALCON_VERIFIER_ABI,
    FALCON_ESCROW_ABI,
    MSG_POINT,
)

# --- Configuration ---
# Class hashes are defined as strings with "0x" prefix
FALCON_KEY_REGISTRY_CONTRACT_HASH = (  # Renamed in app.py to FALCON_KEY_REGISTRY_CLASS_HASH_HEX
    "0x022A351AB5F1AC13352A3792BE246D8C6513D9029F3674608AC4CD7944AA702E"
)
FALCON_ADDRESS_BASED_VERIFIER_CONTRACT_HASH = (
    "0x0396507525F71D979D306DF5B72C568DFCCA173158086D73806E496B054670A3"
)
ESCROW_CONTRACT_HASH = (
    "0x0028172888cc58dece1ccaaadcd0b8076eb85f0284f95aecd28027042b0f64a9"
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


def _hex_str_to_int(hex_str: str) -> int:
    """Helper to convert hex string (with or without 0x) to int."""
    if not isinstance(hex_str, str):
        raise ValueError(f"Input must be a string, got {type(hex_str)}")
    return int(hex_str, 16)


async def get_deployer_account(
    private_key_hex: str, account_address_hex: str
) -> Optional[Account]:
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
    constructor_args: Optional[List[Union[str, int]]] = None,
) -> Tuple[Optional[str], Optional[str]]:
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

    try:
        class_hash_int = _hex_str_to_int(class_hash_hex)
    except ValueError:
        return f"Error: Invalid class_hash_hex format: {class_hash_hex}", None

    if constructor_args is None:
        constructor_args = []

    try:
        prepared_constructor_calldata = []
        for arg in constructor_args:
            if isinstance(arg, str) and arg.startswith("0x"):
                # Convert hex strings to integers
                prepared_constructor_calldata.append(_hex_str_to_int(arg))
            elif isinstance(arg, str) and arg.isdigit():
                # Convert numeric strings to integers
                prepared_constructor_calldata.append(int(arg))
            elif isinstance(arg, (int, float)):
                # Pass numbers directly
                prepared_constructor_calldata.append(int(arg))
            else:
                raise ValueError(
                    f"Unsupported constructor argument type or format: {type(arg)} - {arg}"
                )

        print(f"Deploying contract with class hash: {class_hash_hex}")
        print(f"Constructor args: {prepared_constructor_calldata}")

        # Select the appropriate ABI based on the class hash
        if class_hash_hex == FALCON_KEY_REGISTRY_CONTRACT_HASH:
            abi = FALCON_KEY_REGISTRY_ABI
        elif class_hash_hex == FALCON_ADDRESS_BASED_VERIFIER_CONTRACT_HASH:
            abi = FALCON_VERIFIER_ABI
        elif class_hash_hex == ESCROW_CONTRACT_HASH:
            abi = FALCON_ESCROW_ABI
        else:
            raise ValueError(f"Unknown contract class hash: {class_hash_hex}")

        deploy_result = await Contract.deploy_contract_v3(
            account=deployer_account,
            class_hash=class_hash_int,
            abi=abi,
            constructor_args=prepared_constructor_calldata,
            auto_estimate=True,
        )

        await deploy_result.wait_for_acceptance()
        contract = deploy_result.deployed_contract
        contract_address = hex(contract.address)

        # If this is an escrow contract, set the message points
        if class_hash_hex == ESCROW_CONTRACT_HASH:
            print("Setting message points for escrow contract...")

            tx_hash, error = await call_msg_points(
                contract_address, deployer_account, MSG_POINT
            )
            tx_hash, error = await Stark_Token_Approve(
                "0x04718f5a0fc34cc1af16a1cdee98ffb20c31f5cd61d6ab07201858f4287c938d",
                contract_address,
                deployer_account,
                constructor_args[1],
            )
            tx_hash, error = await deposit_stark_token(
                contract_address, deployer_account
            )
            if error:
                print(f"Warning: Failed to set message points: {error}")
            else:
                print(f"Successfully set message points. Transaction hash: {tx_hash}")

        return contract_address, hex(deploy_result.hash)

    except Exception as e:
        print(f"Error during contract deployment: {e}")
        traceback.print_exc()
        return f"Deployment Error: {e}", None


async def call_msg_points(
    contract_address: str, deployer_account, msg_points: List[int]
) -> Tuple[Optional[str], Optional[str]]:
    """
    Calls the set_message_points function on the escrow contract.
    Args:
        contract_address: The hex address of the escrow contract
        msg_points: List of u16 integers representing the message points
    Returns:
        Tuple of (transaction_hash_hex, error_message)
    """
    try:
        contract_address_int = _hex_str_to_int(contract_address)

        # Create contract instance with escrow ABI
        contract = Contract(
            address=contract_address_int,
            abi=FALCON_ESCROW_ABI,
            provider=deployer_account,
        )

        # Call set_message_points with the msg_points array
        invoke_result = await contract.functions["set_message_points"].invoke_v3(
            msg_points, auto_estimate=True
        )

        await invoke_result.wait_for_acceptance()
        print(
            f"Successfully set message points. Transaction hash: {hex(invoke_result.hash)}"
        )
        return hex(invoke_result.hash), None

    except Exception as e:
        print(f"Error in call_msg_points: {e}")
        traceback.print_exc()
        return None, f"Error: {str(e)}"


async def Stark_Token_Approve(
    stark_contract_address: str,
    escrow_contract_address: str,
    deployer_account,
    amount: int,
):
    try:
        stark_contract_address_int = _hex_str_to_int(stark_contract_address)
        escrow_contract_address_int = _hex_str_to_int(escrow_contract_address)

        stark_contract = await Contract.from_address(
            provider=deployer_account, address=stark_contract_address_int
        )

        invoke_result = await stark_contract.functions["approve"].invoke_v3(
            escrow_contract_address_int, amount, auto_estimate=True
        )

        await invoke_result.wait_for_acceptance()
        print(f"Successfully approved. Transaction hash: {hex(invoke_result.hash)}")
        return hex(invoke_result.hash), None
    except Exception as e:
        print(f"Error in Stark_Token_Approve: {e}")
        traceback.print_exc()
        return None, f"Error: {str(e)}"


async def deposit_stark_token(
    escrow_contract_address: str,
    deployer_account,
):
    try:
        escrow_contract_address_int = _hex_str_to_int(escrow_contract_address)
        # Create contract instance with escrow ABI
        contract = Contract(
            address=escrow_contract_address_int,
            abi=FALCON_ESCROW_ABI,
            provider=deployer_account,
        )

        # Call set_message_points with the msg_points array
        invoke_result = await contract.functions["deposit"].invoke_v3(
            auto_estimate=True
        )

        await invoke_result.wait_for_acceptance()
        print(f"Successfully deposited. Transaction hash: {hex(invoke_result.hash)}")
        return hex(invoke_result.hash), None
    except Exception as e:
        print(f"Error in deposit_stark_token: {e}")
        traceback.print_exc()
        return None, f"Error: {str(e)}"


async def call_register_public_key(
    key_registry_contract_address: str,
    pk_coefficients: list[int],
    deployer_private_key_hex: str,
    deployer_account_address_hex: str,
) -> tuple[str | None, str | None]:
    """
    Calls the 'register_public_key' function on the deployed Key Registry contract.

    Args:
        key_registry_contract_address (str): Address of the Key Registry contract.
        pk_coefficients (list[int]): List of public key coefficients (e.g., N elements for Falcon-N).
        deployer_private_key_hex (str): Private key of the account sending the transaction.
        deployer_account_address_hex (str): Address of the account sending the transaction.

    Returns:
        tuple[str | None, str | None]: (Message, Transaction_Hash_Hex) or (Error_Message, None)
    """
    account = await get_deployer_account(
        deployer_private_key_hex, deployer_account_address_hex
    )
    if not account:
        return "Error: Deployer account not initialized for key registration.", None

    try:
        # Ensure the ABI for the Key Registry is available.
        # If FALCON_KEY_REGISTRY_ABI is correctly defined in utils.py and imported:
        key_registry_contract = await Contract.from_address(
            address=key_registry_contract_address,
            provider=account,  # Using account as provider also sets up the signer for invokes
            # proxy_config=False # Set to True if it's a proxy and you want to use the implementation ABI
        )
        # If from_address doesn't fetch ABI, or you want to be explicit:
        # key_registry_contract = Contract(
        #    address=key_registry_contract_address,
        #    abi=FALCON_KEY_REGISTRY_ABI, # Make sure this ABI matches your KeyRegistry
        #    provider=account,
        # )

        print(
            f"Calling 'register_public_key' on {key_registry_contract_address} with {len(pk_coefficients)} coefficients."
        )

        # The Cairo function is: fn register_public_key(ref self: ContractState, pk_coefficients_span: Span<u16>) -> bool
        # starknet-py handles Span<T> by accepting a list of T for the argument.
        # Max fee can be estimated or set to a reasonable upper bound.
        # For invoke_v1:
        # invocation = await key_registry_contract.functions["register_public_key"].invoke_v1(
        #     pk_coefficients_span=pk_coefficients,
        #     max_fee=int(2 * 10**14)  # Example max_fee, adjust as needed
        # )
        # For invoke_v3 (recommended for Sepolia):

        invocation = await key_registry_contract.functions[
            "register_public_key"
        ].invoke_v3(pk_coefficients_span=pk_coefficients, auto_estimate=True)

        print(f"Sent transaction with hash: {hex(invocation.hash)}")
        await account.client.wait_for_tx(tx_hash=invocation.hash)  # More robust wait
        print(f"Transaction {hex(invocation.hash)} accepted.")

        # Fetch the transaction receipt to get events
        receipt = await account.client.get_transaction_receipt(invocation.hash)

        key_hash = poseidon_hash.poseidon_hash_many(pk_coefficients)
        computed_pk_hash_hex = hex(key_hash)
        transaction_hash_hex = hex(invocation.hash)

        print(f"Off-chain computed PK Poseidon hash: {computed_pk_hash_hex}")

        registry_addr = hex(key_registry_contract_address)

        # Construct the success message
        explorer_link = f"https://sepolia.starkscan.co/tx/{transaction_hash_hex}"
        success_message = (
            f"Public key successfully registered!\n"
            f"Computed PK Poseidon Hash: {computed_pk_hash_hex}\n"
            f"You can retrieve the key from the hash here: https://sepolia.starkscan.co/contract/{registry_addr}#read-write-contract"
        )
        print(success_message)
        return success_message, transaction_hash_hex

    except Exception as e:
        print(f"Error calling 'register_public_key': {e}")
        import traceback

        traceback.print_exc()
        return f"Error during key registration: {str(e)}", None


async def call_escrow_claim(
    escrow_contract_address: str,
    s1_coefficients: list[int],
    deployer_private_key_hex: str,
    deployer_account_address_hex: str,
) -> tuple[str | None, str | None]:
    """
    Calls the 'claim' function on the specified Escrow contract.

    Args:
        escrow_contract_address (str): Address of the Escrow contract.
        s1_coefficients (list[int]): List of s1 signature coefficients.
        deployer_private_key_hex (str): Private key for the account.
        deployer_account_address_hex (str): Account address.

    Returns:
        tuple[str | None, str | None]: (Message, Transaction_Hash_Hex) or (Error_Message, None)
    """
    account = await get_deployer_account(
        deployer_private_key_hex, deployer_account_address_hex
    )
    if not account:
        return "Error: Deployer account not initialized for claim.", None

    try:
        escrow_contract = Contract(
            address=escrow_contract_address,  # Address can be hex string or int
            abi=FALCON_ESCROW_ABI,
            provider=account,
        )

        print(
            f"Calling 'claim' on Escrow contract {escrow_contract_address} with {len(s1_coefficients)} s1 coeffs."
        )

        # Assuming the Escrow's claim function is: fn claim(ref self: ContractState, s1_span: Span<u16>)
        # For invoke_v3 (recommended for Sepolia)
        invocation = await escrow_contract.functions[
            "claim"
        ].invoke_v3(
            s1_span=s1_coefficients,  # starknet-py handles Span<T> from list[T]
            l1_resource_bounds=ResourceBoundsMapping(  # Example, adjust based on typical cost
                max_amount=int(1 * 10**5),  # Max L1 gas amount
                max_price_per_unit=int(25 * 10**9),  # Max L1 gas price in wei
            ),
        )
        # Or for invoke_v1:
        # invocation = await escrow_contract.functions["claim"].invoke_v1(
        #    s1_span=s1_coefficients,
        #    max_fee=int(1 * 10**14)  # Example max_fee (0.0001 ETH at 1 Gwei gas price)
        # )

        print(f"Claim transaction sent with hash: {hex(invocation.hash)}")
        await account.client.wait_for_tx(
            tx_hash=invocation.hash
        )  # More robust wait for tx status
        print(f"Claim transaction {hex(invocation.hash)} accepted on-chain.")

        return "Claim transaction accepted.", hex(invocation.hash)

    except Exception as e:
        print(f"Error in deposit_stark_token: {e}")
        print(f"Error calling 'claim' on Escrow contract: {e}")
        traceback.print_exc()
        return None, f"Error: {str(e)}"

        return f"Error during claim: {str(e)}", None
