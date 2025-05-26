# scripts/cairo_interactions.py
import json
import random
from starknet_py.contract import Contract
from starknet_py.net.full_node_client import FullNodeClient
from starknet_py.net.account.account import Account
from starknet_py.net.models import StarknetChainId
from starknet_py.net.signer.stark_curve_signer import KeyPair
from starknet_py.constants import (
    DEFAULT_DEPLOYER_ADDRESS,
)  # Standard UDC address
from starknet_py.hash.selector import get_selector_from_name
from starknet_py.hash.address import compute_address
from starknet_py.net.client_models import Call

# --- Configuration (Replace with your actual values or load from env/config) ---
NODE_URL = "YOUR_STARKNET_NODE_URL"  # e.g., Infura, Alchemy, or local node
CONTRACT_ADDRESS = "YOUR_DEPLOYED_CONTRACT_ADDRESS"
ACCOUNT_ADDRESS = "YOUR_STARKNET_ACCOUNT_ADDRESS"
PRIVATE_KEY = "YOUR_STARKNET_ACCOUNT_PRIVATE_KEY"
CHAIN_ID = (
    StarknetChainId.SEPOLIA
)  # Or StarknetChainId.MAINNET, StarknetChainId.SEPOLIA_TESTNET etc.

FALCON_KEY_REGISTRY_CLASS_HASH_HEX = (
    0x022A351AB5F1AC13352A3792BE246D8C6513D9029F3674608AC4CD7944AA702E
)
# Path to your ABI file
ABI_PATH = "abis/my_cairo_contract.abi.json"  # Adjust path as needed


def load_abi():
    """Loads the contract ABI from the JSON file."""
    try:
        with open(ABI_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: ABI file not found at {ABI_PATH}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode ABI JSON from {ABI_PATH}")
        return None


async def get_contract():
    """Initializes and returns a Contract instance."""
    abi = load_abi()
    if not abi:
        return None

    # For read-only calls, you might only need a client
    client = FullNodeClient(node_url=NODE_URL)

    # For transactions (write calls), you need an account
    # key_pair = KeyPair.from_private_key(int(PRIVATE_KEY, 16))
    # account = Account(
    #     client=client,
    #     address=int(ACCOUNT_ADDRESS, 16),
    #     key_pair=key_pair,
    #     chain=CHAIN_ID,
    # )

    contract = Contract(
        address=int(CONTRACT_ADDRESS, 16),
        abi=abi,
        provider=client,  # or provider=account if making transactions
    )
    return contract


async def call_my_contract_function(input_value: str) -> str:
    """
    Example function to call a read-only function on your Cairo contract.
    Adjust function name, inputs, and processing based on your contract.
    """
    contract = await get_contract()
    if not contract:
        return "Error: Could not initialize contract."

    try:
        # Assuming your contract has a view function like `get_value(some_input: felt252) -> felt252`
        # The exact syntax for calling functions depends on starknet-py version and your contract
        # For felt252, you might need to convert Python strings/numbers appropriately.
        # If input_value is a number string: int(input_value)
        # If it's a short string, it might need encoding.

        # Example: if your contract's function is `get_processed_value(user_input: felt252)`
        # and `input_value` is expected as a number (felt)
        prepared_input = int(input_value)

        invocation = await contract.functions["your_contract_view_function_name"].call(
            prepared_input
        )

        # The result might be a struct or a simple type. Adjust accordingly.
        # Example: if it returns a single felt value:
        return f"Contract returned: {invocation[0]}"  # Accessing the first element of the tuple result

    except Exception as e:
        return f"Error calling contract: {e}"


async def submit_transaction_to_contract(value_to_set: int) -> str:
    """
    Example function to submit a transaction (write call) to your Cairo contract.
    """
    abi = load_abi()
    if not abi:
        return "Error: ABI not loaded."

    client = FullNodeClient(node_url=NODE_URL)
    key_pair = KeyPair.from_private_key(int(PRIVATE_KEY, 16))
    account = Account(
        client=client,
        address=int(ACCOUNT_ADDRESS, 16),
        key_pair=key_pair,
        chain=CHAIN_ID,
    )

    contract = Contract(
        address=int(CONTRACT_ADDRESS, 16),
        abi=abi,
        provider=account,  # Use account as provider for transactions
    )

    try:
        # Assuming your contract has an external function like `set_value(new_value: u256)`
        # Ensure `value_to_set` is in the correct format (e.g., for u256, it might be a dict {'low': ..., 'high': ...} or just int)
        invocation = await contract.functions[
            "your_contract_write_function_name"
        ].invoke_v1(
            value_to_set,  # Pass the argument(s) for your contract function
            max_fee=int(1e16),  # Set an appropriate max fee
        )
        await (
            invocation.wait_for_acceptance()
        )  # Wait for the transaction to be accepted
        return f"Transaction submitted! Hash: {hex(invocation.hash)}"
    except Exception as e:
        return f"Error submitting transaction: {e}"


# You can add more functions here that call other scripts or perform other logic
# Function to get an Account instance (can be reused or adapted)
async def get_deployer_account():
    """Initializes and returns an Account instance for deploying contracts."""
    if any(
        val
        in [
            None,
            "YOUR_STARKNET_ACCOUNT_ADDRESS_HEX_OR_INT",
            "YOUR_STARKNET_ACCOUNT_PRIVATE_KEY_HEX",
        ]
        for val in [ACCOUNT_ADDRESS, PRIVATE_KEY]
    ):
        print("Error: Deployer account address or private key is not configured.")
        return None

    client = FullNodeClient(node_url=NODE_URL)
    try:
        account_address_int = (
            int(ACCOUNT_ADDRESS, 16)
            if isinstance(ACCOUNT_ADDRESS, str) and ACCOUNT_ADDRESS.startswith("0x")
            else int(ACCOUNT_ADDRESS)
        )
        private_key_int = (
            int(PRIVATE_KEY, 16)
            if isinstance(PRIVATE_KEY, str) and PRIVATE_KEY.startswith("0x")
            else int(PRIVATE_KEY)
        )

        account = Account(
            client=client,
            address=account_address_int,
            key_pair=KeyPair.from_private_key(private_key_int),
            chain=CHAIN_ID,
        )
        return account
    except Exception as e:
        print(f"Error creating deployer account object: {e}")
        return None


# New function to deploy a contract instance using its class hash via UDC
async def deploy_new_contract_instance(
    class_hash_hex: str, constructor_args: list = None
):
    """
    Deploys a new contract instance using its class hash via the Universal Deployer Contract (UDC).

    :param class_hash_hex: The class hash of the contract to deploy (hex string).
    :param constructor_args: A list of arguments for the contract's constructor.
                             Each argument should be in the format expected by StarkNet (usually integers).
                             Example: [provider_address, initial_value]
    :return: Tuple (deployed_contract_address_hex, transaction_hash_hex) or (None, None) on error.
    """
    deployer_account = await get_deployer_account()
    if not deployer_account:
        return "Error: Deployer account not initialized.", None

    if (
        class_hash_hex == "0xYOUR_ACTUAL_FALCON_KEY_REGISTRY_CLASS_HASH"
        or not class_hash_hex.startswith("0x")
    ):
        return (
            f"Error: Invalid or placeholder class hash provided: {class_hash_hex}",
            None,
        )

    if constructor_args is None:
        constructor_args = []

    try:
        class_hash_int = int(class_hash_hex, 16)

        # For constructor arguments, ensure they are integers if representing felts/u_types
        # More complex types (structs, arrays) require specific formatting.
        # For simplicity, assuming basic integer arguments here.
        prepared_constructor_calldata = []
        for arg in constructor_args:
            if isinstance(arg, str) and arg.startswith("0x"):
                prepared_constructor_calldata.append(int(arg, 16))
            elif isinstance(arg, str) and arg.isdigit():
                prepared_constructor_calldata.append(int(arg))
            elif isinstance(arg, int):
                prepared_constructor_calldata.append(arg)
            else:
                # Add more sophisticated parsing if needed, e.g. for short strings
                raise ValueError(f"Unsupported constructor argument type: {arg}")

        # Salt for deployment uniqueness. Random salt ensures a new address each time.
        salt = random.randint(0, 2**128 - 1)

        # `unique=0` means address computation doesn't depend on deployer address,
        # only on class_hash, salt, and constructor_calldata.
        # `unique=1` means it also depends on deployer address (caller of UDC).
        # For distinct new instances, random salt with unique=0 is common.
        unique_flag = 0

        # Pre-compute the expected contract address (optional but good for verification)
        expected_address = compute_address(
            salt=salt,
            class_hash=class_hash_int,
            constructor_calldata=prepared_constructor_calldata,
            deployer_address=DEFAULT_DEPLOYER_ADDRESS,  # Address of the UDC itself
        )
        print(f"Attempting to deploy contract with class hash: {hex(class_hash_int)}")
        print(f"Salt: {salt}")
        print(f"Constructor Calldata: {prepared_constructor_calldata}")
        print(f"Expected Contract Address: {hex(expected_address)}")

        # Prepare the call to UDC's 'deployContract' function
        # Calldata for deployContract: [classHash, salt, unique, constructor_calldata_len, ...constructor_calldata]
        udc_calldata = [
            class_hash_int,
            salt,
            unique_flag,
            len(prepared_constructor_calldata),
            *prepared_constructor_calldata,
        ]

        udc_deploy_call = Call(
            to_addr=DEFAULT_DEPLOYER_ADDRESS,
            selector=get_selector_from_name("deployContract"),
            calldata=udc_calldata,
        )

        print("Signing and sending deployment transaction via UDC...")
        # max_fee should be estimated or set appropriately for the network
        resp = await deployer_account.sign_invoke_transaction(
            calls=udc_deploy_call,
            max_fee=int(
                3e16
            ),  # Example fee, adjust based on network conditions and transaction complexity
        )

        print(f"Deployment transaction sent. Hash: {hex(resp.transaction_hash)}")
        print("Waiting for transaction acceptance...")
        receipt = await deployer_account.client.wait_for_tx(
            resp.transaction_hash, wait_for_accept=True
        )

        # The actual deployed address is emitted in the 'ContractDeployed' event by the UDC
        # It's typically the 4th element (index 3) in the event.data array.
        deployed_contract_address = None
        contract_deployed_event_selector = get_selector_from_name("ContractDeployed")

        for event in receipt.events:
            # Check if the event is ContractDeployed by comparing keys[0] with its selector
            if event.keys and event.keys[0] == contract_deployed_event_selector:
                if len(event.data) >= 4:  # class_hash, salt, deployer, address
                    # Address is usually at data[3] if keys = [ContractDeployed_selector]
                    # Or data[0] if keys = [ContractDeployed_selector, deployer, class_hash, salt]
                    # For standard UDC, address is at data[3] if keys[0] is selector
                    # and event.from_address is UDC_CONTRACT_ADDRESS
                    if event.from_address == DEFAULT_DEPLOYER_ADDRESS:
                        deployed_contract_address = event.data[
                            3
                        ]  # Address is the 4th field in data for UDC event
                        break

        if deployed_contract_address is not None:
            deployed_address_hex = hex(deployed_contract_address)
            print(
                f"Transaction accepted! Contract deployed at address: {deployed_address_hex}"
            )
            if deployed_address_hex != hex(expected_address):
                print(
                    f"Warning: Deployed address {deployed_address_hex} differs from pre-computed address {hex(expected_address)}."
                )
            return deployed_address_hex, hex(resp.transaction_hash)
        else:
            # Fallback to precomputed if event parsing fails, though this is less reliable
            print(
                "Transaction accepted. Could not reliably parse deployed address from events. Using precomputed address."
            )
            return hex(expected_address), hex(resp.transaction_hash)

    except Exception as e:
        print(f"Error during contract deployment: {e}")
        import traceback

        traceback.print_exc()
        return f"Deployment Error: {e}", None
