# scripts/cairo_interactions.py
import random
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
from starknet_py.net.client_models import Call, ResourceBounds

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
CHAIN_ID = StarknetChainId.SEPOLIA


def _hex_str_to_int(hex_str: str) -> int:
    """Helper to convert hex string (with or without 0x) to int."""
    if not isinstance(hex_str, str):
        raise ValueError(f"Input must be a string, got {type(hex_str)}")
    return int(hex_str, 16)


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
        # Robust conversion for hex strings (with or without "0x")
        account_address_int = _hex_str_to_int(account_address_hex)
        private_key_int = _hex_str_to_int(private_key_hex)

        key_pair = KeyPair.from_private_key(private_key_int)

        account = Account(
            client=client,
            address=account_address_int,
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
            if isinstance(arg, str):
                prepared_constructor_calldata.append(_hex_str_to_int(arg))
            elif isinstance(arg, int):
                prepared_constructor_calldata.append(arg)
            else:
                raise ValueError(f"Unsupported constructor argument type: {type(arg)}")

        salt = random.randint(0, 2**128 - 1)
        unique_flag = (
            0  # Common for UDC deployments to make address dependent on salt & calldata
        )

        # Use compute_contract_address for UDC deployments for semantic clarity
        expected_address = compute_address(
            salt=salt,
            class_hash=class_hash_int,
            constructor_calldata=prepared_constructor_calldata,
            deployer_address=int(
                DEFAULT_DEPLOYER_ADDRESS, 16
            ),  # This is the UDC's address
        )

        print(f"Attempting to deploy contract with class hash: {hex(class_hash_int)}")
        print(f"Salt: {salt}")
        print(f"Constructor Calldata: {prepared_constructor_calldata}")
        print(f"Expected Contract Address: {hex(expected_address)}")

        udc_calldata = [
            class_hash_int,
            salt,
            unique_flag,
            len(prepared_constructor_calldata),
            *prepared_constructor_calldata,
        ]

        udc_deploy_call = Call(
            to_addr=int(DEFAULT_DEPLOYER_ADDRESS, 16),
            selector=get_selector_from_name("deployContract"),
            calldata=udc_calldata,
        )

        # print("Estimating fee for V3 transaction...")
        # try:
        #     # Pass the Call object directly as the first positional argument
        #     transaction = InvokeV3(
        #         calldata=udc_deploy_call,
        #         resource_bounds=ResourceBoundsMapping.init_with_zeros(),
        #         signature=[],
        #         nonce=nonce,
        #         sender_address=self.address,
        #         version=3,
        #     )
        #     estimated_fee = await deployer_account.estimate_fee(transaction)
        #     print(f"Raw estimated fee object: {estimated_fee}")

        #     # Try to use resource_bounds directly from the estimate if available (common in newer starknet-py)
        #     if hasattr(estimated_fee, "resource_bounds") and isinstance(
        #         estimated_fee.resource_bounds, dict
        #     ):
        #         resource_bounds_dict = estimated_fee.resource_bounds
        #         # Apply a buffer to max_amount for safety
        #         if "l1_gas" in resource_bounds_dict and hasattr(
        #             resource_bounds_dict["l1_gas"], "max_amount"
        #         ):
        #             resource_bounds_dict["l1_gas"].max_amount = int(
        #                 resource_bounds_dict["l1_gas"].max_amount * 1.5
        #             )
        #         if "l2_gas" in resource_bounds_dict and hasattr(
        #             resource_bounds_dict["l2_gas"], "max_amount"
        #         ):
        #             resource_bounds_dict["l2_gas"].max_amount = int(
        #                 resource_bounds_dict["l2_gas"].max_amount * 1.5
        #             )
        #         print(
        #             f"Using resource_bounds from estimate_fee: {resource_bounds_dict}"
        #         )
        #     elif hasattr(estimated_fee, "l1_gas_usage") and hasattr(
        #         estimated_fee, "l1_gas_price"
        #     ):  # Example for older structure
        #         # This part is more speculative as EstimatedFee structure can vary.
        #         # You might need to adjust based on the actual attributes of `estimated_fee`.
        #         print(
        #             "Constructing resource_bounds from detailed fee components (experimental)."
        #         )
        #         l1_max_amount = int(estimated_fee.l1_gas_usage * 1.5)
        #         l1_max_price = int(
        #             estimated_fee.l1_gas_price * 1.5
        #         )  # Or use current L1 gas price
        #         l2_max_amount = int(estimated_fee.gas_usage * 1.5)  # L2 gas (steps)
        #         l2_max_price = int(
        #             estimated_fee.gas_price * 1.5
        #         )  # L2 gas price (FRI/step)
        #         resource_bounds_dict = {
        #             "l1_gas": ResourceBounds(
        #                 max_amount=l1_max_amount, max_price_per_unit=l1_max_price
        #             ),
        #             "l2_gas": ResourceBounds(
        #                 max_amount=l2_max_amount, max_price_per_unit=l2_max_price
        #             ),
        #         }
        #         print(f"Manually constructed resource_bounds: {resource_bounds_dict}")
        #     else:
        #         # Fallback if structure is unknown or very minimal (e.g., only overall_fee)
        #         # This requires making broad assumptions and is less reliable.
        #         print(
        #             "Warning: Could not determine detailed resource bounds from estimate_fee. Using fallback."
        #         )
        #         # This will likely fail if node expects explicit l1_gas and l2_gas bounds.
        #         # For V3, you typically need to provide both L1 and L2 gas bounds.
        #         # Using overall_fee directly is more like V1's max_fee.
        #         # A more robust fallback would query current L1 gas price.
        #         # Placeholder to illustrate structure, actual values need to be sensible.
        #         example_l1_max_amount = 30000  # Placeholder value for L1 gas units
        #         example_l1_max_price = int(10 * 10**9)  # Placeholder: 10 Gwei in Wei
        #         example_l2_max_amount = (
        #             int(estimated_fee.gas_usage * 1.5)
        #             if hasattr(estimated_fee, "gas_usage")
        #             else 500000
        #         )
        #         example_l2_max_price = (
        #             int(estimated_fee.gas_price * 1.5)
        #             if hasattr(estimated_fee, "gas_price")
        #             else int(10 * 10**9)
        #         )

        #         resource_bounds_dict = {
        #             "l1_gas": ResourceBounds(
        #                 max_amount=example_l1_max_amount,
        #                 max_price_per_unit=example_l1_max_price,
        #             ),
        #             "l2_gas": ResourceBounds(
        #                 max_amount=example_l2_max_amount,
        #                 max_price_per_unit=example_l2_max_price,
        #             ),
        #         }
        #         print(f"Fallback resource_bounds: {resource_bounds_dict}")

        # except Exception as fee_error:
        #     print(f"Error during fee estimation: {fee_error}")
        #     traceback.print_exc()
        #     return f"Deployment Error: Fee estimation failed - {fee_error}", None

        print("Signing and sending V3 deployment transaction via UDC...")
        resp = await deployer_account.sign_invoke_v3(
            calls=udc_deploy_call,
            # resource_bounds=resource_bounds_dict,
            auto_estimate=True,  # DOESNT WORK! unexpected field l1_data_gas
        )

        print(f"Deployment transaction sent. Hash: {hex(resp.transaction_hash)}")
        print("Waiting for transaction acceptance...")
        receipt = await deployer_account.client.wait_for_tx(
            resp.transaction_hash, wait_for_accept=True
        )

        # Try to get deployed address from receipt directly first
        actual_deployed_address = (
            receipt.contract_address
            if receipt.contract_address and receipt.contract_address != 0
            else None
        )

        if (
            not actual_deployed_address
        ):  # Fallback to event parsing if not in receipt directly
            contract_deployed_event_selector = get_selector_from_name(
                "ContractDeployed"
            )
            for event in receipt.events:
                if (
                    event.from_address == DEFAULT_DEPLOYER_ADDRESS
                    and event.keys
                    and event.keys[0] == contract_deployed_event_selector
                ):
                    # Standard UDC ContractDeployed event data[0] is the deployed contract address
                    if event.data and len(event.data) > 0:
                        actual_deployed_address = event.data[0]
                        break

        if actual_deployed_address:
            deployed_address_hex = hex(actual_deployed_address)
            print(
                f"Transaction accepted! Contract deployed at address: {deployed_address_hex}"
            )
            if deployed_address_hex.lower() != hex(expected_address).lower():
                print(
                    f"Warning: Deployed address {deployed_address_hex} differs from pre-computed address {hex(expected_address)}! This can happen due to different address computation versions or parameters."
                )
            return deployed_address_hex, hex(resp.transaction_hash)
        else:
            # If still no address, rely on precomputed but warn heavily.
            print(
                f"Transaction accepted. Using precomputed address: {hex(expected_address)}. (Could not parse address from UDC events or receipt details)"
            )
            return hex(expected_address), hex(resp.transaction_hash)

    except Exception as e:
        print(f"Error during contract deployment: {e}")
        traceback.print_exc()
        return f"Deployment Error: {e}", None
