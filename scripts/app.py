import gradio as gr
import asyncio
import time
import traceback

# Import functions from your scripts directory
from cairo_interactions import (
    deploy_new_contract_instance,
    FALCON_KEY_REGISTRY_CONTRACT_HASH,
    FALCON_ADDRESS_BASED_VERIFIER_CONTRACT_HASH,
    ESCROW_CONTRACT_HASH,
    NODE_URL,
    ESCROW_CONTRACT_HASH,
    get_deployer_account,
    call_register_public_key,
    call_escrow_claim,
)
import utils
from falcon import SecretKey
from generate_inputs import generate_attestation
from starknet_py.contract import Contract
from starknet_py.net.full_node_client import FullNodeClient
from utils import FALCON_ESCROW_ABI


def sepolia_url_from_contract_address(contract_address):
    url = f"https://sepolia.starkscan.co/contract/{contract_address}"
    return url


def mainnnet_url_from_contract_address(contract_address):
    url = f"https://starkscan.co/contract/{contract_address}"
    return url


# --- Gradio UI Definition ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:  # Added a soft theme for better visuals
    # --- State Variables to hold credentials and contract info ---
    user_private_key_state = gr.State(None)
    user_account_address_state = gr.State(None)
    deployed_contract_address_state = gr.State(None)
    service_period_state = gr.State(None)
    service_start_block_state = gr.State(None)

    # --- UI Element Definitions (for referencing in callbacks) ---
    # Entry Screen Elements
    input_account_address_comp = gr.Textbox(
        label="Your StarkNet Account Address (hex)",
        placeholder="0x...",
        info="Ensure this is the address corresponding to the private key.",
    )
    input_private_key_comp = gr.Textbox(
        label="Your Private Key (hex)",
        type="password",
        placeholder="0x...",
        info="Your private key will be used to sign transactions.",
    )

    # Page Group Elements
    entry_screen_group_comp = None
    client_page_group_comp = None
    provider_page_group_comp = None

    # --- Page Navigation and State Update Functions ---
    def set_creds_and_navigate_to_page(
        pk_from_input, aa_from_input, target_page_visible_updates
    ):
        if not pk_from_input or not aa_from_input:
            print("Warning: Private Key or Account Address is empty during navigation.")

        updates = {
            entry_screen_group_comp: gr.update(visible=False),
            client_page_group_comp: gr.update(visible=False),
            provider_page_group_comp: gr.update(visible=False),
            user_private_key_state: pk_from_input,
            user_account_address_state: aa_from_input,
        }
        updates.update(target_page_visible_updates)
        return updates

    def show_client_page_action(pk_in, aa_in):
        print("Navigating to Client Page")
        return set_creds_and_navigate_to_page(
            pk_in, aa_in, {client_page_group_comp: gr.update(visible=True)}
        )

    def show_provider_page_action(pk_in, aa_in):
        print("Navigating to Provider Page")
        return set_creds_and_navigate_to_page(
            pk_in, aa_in, {provider_page_group_comp: gr.update(visible=True)}
        )

    def show_entry_screen_action():
        return {
            entry_screen_group_comp: gr.update(visible=True),
            client_page_group_comp: gr.update(visible=False),
            provider_page_group_comp: gr.update(visible=False),
            input_account_address_comp: gr.update(value=""),
            input_private_key_comp: gr.update(value=""),
            # user_private_key_state: None, # Optionally clear state too
            # user_account_address_state: None,
        }

    async def get_contract_status(
        contract_address: str, private_key: str, account_address: str
    ):
        """Fetches the current status of the escrow contract"""
        if not contract_address:
            return "No contract deployed", 0, 0, 0, False, 0

        try:
            deployer_account = await get_deployer_account(private_key, account_address)
            if not deployer_account:
                return "Failed to initialize account", 0, 0, 0, False, 0

            contract = Contract(
                address=int(contract_address, 16),
                abi=FALCON_ESCROW_ABI,
                provider=deployer_account,
            )

            # Get current block number
            client = FullNodeClient(node_url=NODE_URL)
            current_block = await client.get_block_number()

            # Get escrow details - returns a single struct
            details = (await contract.functions["get_escrow_details"].call())[0]

            # Access struct fields
            service_start_block = details["service_start_block"]
            service_period_blocks = details["service_period_blocks"]
            is_disputed = details["is_disputed"]
            is_deposited = details["is_deposited"]
            total_amount = details["total_amount"]

            if service_start_block == 0:
                return (
                    "Service not started",
                    0,
                    service_period_blocks,
                    0,
                    is_disputed,
                    total_amount,
                )

            blocks_elapsed = current_block - service_start_block
            blocks_remaining = max(0, service_period_blocks - blocks_elapsed)

            status = "In Progress"
            if blocks_remaining == 0:
                status = "Completed"
            elif is_disputed:
                status = "Disputed"
            elif not is_deposited:
                status = "Awaiting Deposit"

            return (
                status,
                blocks_elapsed,
                service_period_blocks,
                blocks_remaining,
                is_disputed,
                total_amount,
            )

        except Exception as e:
            print(f"Error getting contract status: {e}")
            traceback.print_exc()
            return f"Error: {str(e)}", 0, 0, 0, False, 0

    async def handle_dispute_action(
        contract_address: str, private_key: str, account_address: str
    ) -> str:
        """Handles the dispute action for the escrow contract"""
        if not contract_address:
            return "No contract deployed"

        try:
            deployer_account = await get_deployer_account(private_key, account_address)
            if not deployer_account:
                return "Failed to initialize account"

            contract = Contract(
                address=int(contract_address, 16),
                abi=FALCON_ESCROW_ABI,
                provider=deployer_account,
            )

            # Call dispute function
            invoke_result = await contract.functions["dispute"].invoke_v3(
                auto_estimate=True
            )

            await invoke_result.wait_for_acceptance()
            return f"Dispute initiated successfully. Transaction hash: {hex(invoke_result.hash)}"

        except Exception as e:
            print(f"Error disputing contract: {e}")
            return f"Error: {str(e)}"

    def update_countdown(contract_address: str, private_key: str, account_address: str):
        """Updates the countdown display"""
        if not contract_address:
            return (
                "No contract deployed",
                "",
                gr.update(visible=False),
                "No amount to display",
            )

        (
            status,
            blocks_elapsed,
            total_blocks,
            blocks_remaining,
            is_disputed,
            total_amount,
        ) = asyncio.run(
            get_contract_status(contract_address, private_key, account_address)
        )

        progress = f"Blocks elapsed: {blocks_elapsed} / {total_blocks}"
        # Calculate refund amount with proper STRK decimal handling (18 decimals)
        if blocks_elapsed > 0 and total_blocks > 0:
            earned_amount = (total_amount * blocks_elapsed) // total_blocks
            earned_amount_strk = earned_amount / (10**18)
            total_amount_strk = total_amount / (10**18)  # Convert from wei to STRK
            amount_refund = (
                f"Amount to refund : {total_amount_strk - earned_amount_strk:.6f} STRK"
            )
        else:
            amount_refund = f"Total escrow amount: {total_amount / (10**18):.6f} STRK"

        dispute_visible = not is_disputed and blocks_remaining > 0

        return status, progress, gr.update(visible=dispute_visible), amount_refund

    def handle_deploy_escrow_action(
        private_key: str,
        account_address: str,
        provider_key_hash: str,
        total_amount: float,
        service_period: int,
        verifier_address: str,
        key_registry_address: str,
        strk_token_address: str,
        provider_address: str,
        listing_id: str,
    ) -> tuple:
        """
        Handles the deployment of a new escrow contract.
        Returns (status_message, contract_address)
        """
        print("Pressed deploy escrow")
        if not all(
            [
                private_key,
                account_address,
                provider_key_hash,
                verifier_address,
                key_registry_address,
                strk_token_address,
                provider_address,
                listing_id,
            ]
        ):
            return "Error: All fields are required", None, None

        try:
            # Ensure hex strings start with 0x
            provider_key_hash = (
                provider_key_hash
                if provider_key_hash.startswith("0x")
                else f"0x{provider_key_hash}"
            )
            verifier_address = (
                verifier_address
                if verifier_address.startswith("0x")
                else f"0x{verifier_address}"
            )
            key_registry_address = (
                key_registry_address
                if key_registry_address.startswith("0x")
                else f"0x{key_registry_address}"
            )
            strk_token_address = (
                strk_token_address
                if strk_token_address.startswith("0x")
                else f"0x{strk_token_address}"
            )
            provider_address = (
                provider_address
                if provider_address.startswith("0x")
                else f"0x{provider_address}"
            )

            # Convert total_amount from float to u128 (assuming STRK has 18 decimals)
            total_amount_u128 = int(total_amount * 10**18)

            # Convert service_period to u64
            service_period_u64 = int(service_period)

            # Prepare constructor arguments
            constructor_args = [
                provider_key_hash,  # felt252 (hex string)
                total_amount_u128,  # u128 (integer)
                service_period_u64,  # u64 (integer)
                verifier_address,  # ContractAddress (hex string)
                key_registry_address,  # ContractAddress (hex string)
                strk_token_address,  # ContractAddress (hex string)
                account_address,  # client_address (hex string)
                provider_address,  # provider_address (hex string)
            ]

            # Deploy the contract
            result = asyncio.run(
                deploy_new_contract_instance(
                    ESCROW_CONTRACT_HASH,
                    private_key,
                    account_address,
                    constructor_args,
                )
            )

            contract_address, tx_hash = result
            if tx_hash:
                status_msg = f"Escrow deployment successful!\nContract Address: {contract_address}\nTransaction Hash: {tx_hash}\nListing ID: {listing_id}"
                return status_msg, contract_address, service_period
            else:
                return f"Deployment failed: {contract_address}", None, None

        except Exception as e:
            return f"Error deploying escrow contract: {str(e)}", None, None

    # --- Action Handler for Deployments (Provider Page) ---
    def handle_deploy_contracts_action(current_pk_state, current_aa_state):
        if not current_pk_state or not current_aa_state:
            return "Error: Private Key or Account Address not set. Please go back and configure them."

        results_log = []
        final_message = ""
        contract_address = ""

        # 1. Deploy Key Registry
        print(f"Deploying Falcon Key Registry. Account: {current_aa_state[:10]}...")
        # Constructor args are empty for this example
        kr_constructor_args = []
        try:
            contract_address_kr, tx_hash_kr = asyncio.run(
                deploy_new_contract_instance(
                    FALCON_KEY_REGISTRY_CONTRACT_HASH,
                    current_pk_state,
                    current_aa_state,
                    kr_constructor_args,
                )
            )
            if tx_hash_kr:
                contract_address = contract_address_kr
                contract_url = sepolia_url_from_contract_address(contract_address_kr)
                results_log.append(
                    f"Key Registry Deployment Initiated!\nContract Link: {contract_url}\nTx Hash: {tx_hash_kr}"
                )
            else:
                results_log.append(f"Key Registry Deployment Failed: {contract_url}")
        except Exception as e:
            results_log.append(f"Key Registry Deployment Exception: {str(e)}")
            print(f"Exception during Key Registry deployment: {e}")

        # 2. Deploy Address-Based Verifier
        print(f"Deploying Address-Based Verifier. Account: {current_aa_state[:10]}...")
        # Assuming empty constructor args for verifier as well for this minimal example
        contract_address = int(contract_address, 16)
        ab_verifier_constructor_args = [contract_address]
        try:
            result_msg_verifier, tx_hash_verifier = asyncio.run(
                deploy_new_contract_instance(
                    FALCON_ADDRESS_BASED_VERIFIER_CONTRACT_HASH,
                    current_pk_state,
                    current_aa_state,
                    ab_verifier_constructor_args,
                )
            )
            if tx_hash_verifier:
                results_log.append(
                    f"Address Verifier Deployment Initiated!\nContract Link: {result_msg_verifier}\nTx Hash: {tx_hash_verifier}"
                )
            else:
                results_log.append(
                    f"Address Verifier Deployment Failed: {result_msg_verifier}"
                )
        except Exception as e:
            results_log.append(f"Address Verifier Deployment Exception: {str(e)}")
            print(f"Exception during Address Verifier deployment: {e}")

        # Register a the provider key to use the hash in client escrow contract deployment
        try:
            N_FOR_KEY = 512  # Or 1024, or make it configurable in the UI
            results_log.append(
                f"\nGenerating Falcon-{N_FOR_KEY} public key coefficients..."
            )

            pk_coeffs = generate_falcon_pk_coefficients(N_FOR_KEY)  # Call the function

            results_log.append(f"Successfully generated {len(pk_coeffs)} coefficients.")
            results_log.append(
                f"Attempting to register public key on: {contract_address_kr}..."
            )

            # You'll need to create 'call_register_public_key' in cairo_interactions.py
            # It will take the registry address, coefficients, and user credentials.
            reg_status_msg, reg_tx_hash = asyncio.run(
                call_register_public_key(  # This is a NEW function for cairo_interactions.py
                    key_registry_contract_address=contract_address,
                    pk_coefficients=pk_coeffs,
                    deployer_private_key_hex=current_pk_state,
                    deployer_account_address_hex=current_aa_state,
                )
            )
            if reg_tx_hash:
                results_log.append(
                    f"Public Key Registration Call Sent!\nStatus: {reg_status_msg}\nTransaction Hash: {reg_tx_hash}"
                )
            else:
                results_log.append(
                    f"Public Key Registration Call Failed: {reg_status_msg}"
                )

        except ValueError as ve:  # Catch errors from generate_falcon_pk_coefficients
            results_log.append(f"Error generating public key: {str(ve)}")
            print(f"ValueError during PK generation: {ve}")
        except Exception as e:
            error_msg = f"An error occurred during public key generation or registration: {str(e)}"
            results_log.append(error_msg)
            print(f"Exception during PK generation/registration step: {e}")

        final_message = "\n\n---\n\n".join(results_log)
        return final_message

    # --- Action Handler for Claim (Provider Page) ---
    def handle_claim_action(current_pk_state, current_aa_state):
        if not current_pk_state or not current_aa_state:
            return "Error: Private Key or Account Address not set."

        # This is a stub function. Implement actual claim logic here.
        print(
            f"Claim button clicked. Account: {current_aa_state[:10]}... PK used (not shown)"
        )
        # Simulate a call or return a message
        # For now, just a placeholder message
        return "Claim functionality is not yet implemented. This is a stub."

    # --- UI Structure ---
    # Screen 1: Entry Screen
    with gr.Group(visible=True) as es_group_ui:
        entry_screen_group_comp = es_group_ui
        gr.Markdown("<h1 style='text-align: center;'>Account Configuration</h1>")
        gr.Markdown(
            "Please enter your StarkNet account details. These will be used to sign transactions."
        )
        # input_account_address_comp defined at the top is implicitly added here
        # input_private_key_comp defined at the top is implicitly added here

        gr.Markdown(
            "<h1 style='text-align: center; margin-top: 30px; margin-bottom: 20px;'>Choose Your Role</h1>"
        )
        with gr.Row(equal_height=False):
            with gr.Column(scale=1, min_width=250):
                client_btn = gr.Button("Client", variant="primary")
            with gr.Column(scale=1, min_width=250):
                provider_btn = gr.Button("Provider", variant="primary")
        gr.HTML("""
        <style>
            .gradio-container .gr-button { 
                min-height: 100px !important;
                font-size: 1.2em !important; 
                display: flex;
                justify-content: center;
                align-items: center;
            }
        </style>""")

    # Screen 2: Client Page
    with gr.Group(visible=False) as cp_group_ui:
        client_page_group_comp = cp_group_ui
        with gr.Column():
            gr.Markdown("<h1 style='text-align: center;'>Client Page</h1>")
            gr.Markdown("This is where client-specific interactions will go.")

            # Deploy Escrow Section
            with gr.Accordion("Deploy Escrow Contract", open=True):
                gr.Markdown(
                    "Deploy a new escrow contract to secure your service agreement."
                )

                # Input fields for constructor arguments
                provider_key_hash_input = gr.Textbox(
                    label="Provider's Key Hash (hex)",
                    placeholder="0x...",
                    info="The hash of the provider's public key",
                )
                total_amount_input = gr.Number(
                    label="Total Amount (STRK)",
                    value=1,
                    minimum=0,
                    info="Amount of STRK tokens to be held in escrow",
                )
                service_period_input = gr.Number(
                    label="Service Period (blocks)",
                    value=100,
                    minimum=1,
                    info="Duration of service in blocks",
                )
                verifier_address_input = gr.Textbox(
                    label="Verifier Contract Address (hex)",
                    placeholder="0x...",
                    info="Address of the Falcon signature verifier contract",
                )
                key_registry_address_input = gr.Textbox(
                    label="Key Registry Contract Address (hex)",
                    placeholder="0x...",
                    info="Address of the Falcon public key registry contract",
                )
                strk_token_address_input = gr.Textbox(
                    label="STRK Token Contract Address (hex)",
                    placeholder="0x...",
                    info="Address of the STRK token contract",
                )
                provider_address_input = gr.Textbox(
                    label="Provider Address (hex)",
                    placeholder="0x...",
                    info="Starknet address of the service provider",
                )
                listing_id_input = gr.Textbox(
                    label="Listing ID",
                    placeholder="Enter the listing ID",
                    info="Identifier for this service agreement",
                )

                deploy_escrow_btn = gr.Button("🚀 Deploy Escrow")
                deploy_escrow_output = gr.Textbox(
                    label="Deployment Status", lines=4, interactive=False
                )

            # Contract Status Section
            with gr.Accordion("Contract Status", open=True):
                status_text = gr.Textbox(
                    label="Status", interactive=False, value="No contract deployed"
                )
                progress_text = gr.Textbox(
                    label="Progress", interactive=False, value=""
                )
                amount_refund = gr.Textbox(
                    label="Amount Status",
                    interactive=False,
                    value="No amount to display",
                )
                dispute_btn = gr.Button("🚫 Dispute Contract", visible=False)
                dispute_output = gr.Textbox(
                    label="Dispute Status", interactive=False, visible=True
                )

            gr.Markdown("---")  # Separator
            back_btn_client = gr.Button("⬅️ Back to Home")

    # Screen 3: Provider Page
    with gr.Group(visible=False) as pp_group_ui:
        provider_page_group_comp = pp_group_ui
        with gr.Column():
            gr.Markdown("<h1 style='text-align: center;'>Provider Page</h1>")

            with gr.Accordion(
                "Deploy Key Registry & Address Verifier Contracts", open=True
            ):
                deploy_contracts_btn = gr.Button("🚀 Deploy Key Registry & Verifier")
                deploy_contracts_output = gr.Textbox(
                    label="Deployment Status", lines=6, interactive=False
                )

            gr.Markdown("---")

            with gr.Accordion("Claim Rewards", open=True):  # New section for Claim
                claim_rewards_btn = gr.Button("💰 Claim Rewards")
                claim_rewards_output = gr.Textbox(
                    label="Claim Status", lines=2, interactive=False
                )

            gr.Markdown("---")
            back_btn_provider = gr.Button("⬅️ Back to Home")

    # --- Event Handlers ---
    navigation_outputs_from_entry = [
        entry_screen_group_comp,
        client_page_group_comp,
        provider_page_group_comp,
        user_private_key_state,
        user_account_address_state,
    ]
    navigation_outputs_to_entry = [
        entry_screen_group_comp,
        client_page_group_comp,
        provider_page_group_comp,
        input_account_address_comp,
        input_private_key_comp,
    ]

    client_btn.click(
        fn=show_client_page_action,
        inputs=[input_private_key_comp, input_account_address_comp],
        outputs=navigation_outputs_from_entry,
    )
    provider_btn.click(
        fn=show_provider_page_action,
        inputs=[input_private_key_comp, input_account_address_comp],
        outputs=navigation_outputs_from_entry,
    )
    back_btn_client.click(
        fn=show_entry_screen_action, inputs=None, outputs=navigation_outputs_to_entry
    )
    back_btn_provider.click(
        fn=show_entry_screen_action, inputs=None, outputs=navigation_outputs_to_entry
    )

    deploy_contracts_btn.click(
        fn=handle_deploy_contracts_action,
        inputs=[user_private_key_state, user_account_address_state],
        outputs=[deploy_contracts_output],
    )

    claim_rewards_btn.click(
        fn=handle_claim_action,
        inputs=[user_private_key_state, user_account_address_state],
        outputs=[claim_rewards_output],
    )
    # Event handler for the escrow deployment button on the Client page
    deploy_escrow_btn.click(
        fn=handle_deploy_escrow_action,
        inputs=[
            user_private_key_state,
            user_account_address_state,
            provider_key_hash_input,
            total_amount_input,
            service_period_input,
            verifier_address_input,
            key_registry_address_input,
            strk_token_address_input,
            provider_address_input,
            listing_id_input,
        ],
        outputs=[
            deploy_escrow_output,
            deployed_contract_address_state,
            service_period_state,
        ],
    )

    # Event handler for dispute button
    dispute_btn.click(
        fn=lambda x, y, z: asyncio.run(handle_dispute_action(x, y, z)),
        inputs=[
            deployed_contract_address_state,
            user_private_key_state,
            user_account_address_state,
        ],
        outputs=[dispute_output],
    )

    # Setup auto-updating countdown
    demo.load(
        fn=update_countdown,
        inputs=[
            deployed_contract_address_state,
            user_private_key_state,
            user_account_address_state,
        ],
        outputs=[status_text, progress_text, dispute_btn, amount_refund],
        # every=5,  # Update every 5 seconds
    )


def generate_falcon_pk_coefficients(n_value: int) -> list[int]:
    """
    Generates Falcon public key coefficients for a given N (e.g., 512 or 1024).
    These coefficients are intended for the 'register_public_key' StarkNet contract function
    which expects a Span<u16>.

    Args:
        n_value (int): The Falcon parameter N. Your contract likely supports 512 or 1024.
                       The falcon-py library supports N = 8, 16, ..., 1024.

    Returns:
        list[int]: A list of public key coefficients. Each coefficient is an integer
                   expected to be within the range [0, Q-1) where Q=12289 for Falcon,
                   making them suitable for u16 representation.

    Raises:
        ValueError: If an unsupported n_value is provided or if key generation fails.
    """
    # Validate n_value based on common Falcon parameters, ensure it matches your contract's needs
    if n_value not in [512, 1024]:  # As per your initial context
        # You can expand this list if your contract/system supports other N values
        # supported by falcon-py: 8, 16, 32, 64, 128, 256, 512, 1024
        raise ValueError(
            f"N value for Falcon public key must be 512 or 1024, got {n_value}."
        )

    try:
        sk = SecretKey(n_value)
        # sk.h contains the public key coefficients. These are integers.
        # For Falcon, coefficients are in Z_Q where Q=12289.
        # The falcon-py library typically provides these as integers within [0, Q-1)
        # or a symmetric range like [-(Q-1)/2, (Q-1)/2].
        # Since StarkNet's u16 expects values in [0, 65535], and Falcon coeffs are < 12289,
        # they fit. If negative values are possible from sk.h, they should be converted
        # to their positive representation modulo Q (e.g., coeff + Q if coeff < 0).
        # However, your example `format_array(arg["pk"], ...)` uses `sk.h` directly,
        # suggesting they are already in a suitable positive form (e.g. [0, Q-1]).
        public_key_coeffs = sk.h

        if not isinstance(public_key_coeffs, list) or not all(
            isinstance(c, int) for c in public_key_coeffs
        ):
            raise ValueError(
                "Generated public key coefficients are not a list of integers."
            )

        if len(public_key_coeffs) != n_value:
            # This would be unexpected if SecretKey(n_value) works as specified by the library
            raise ValueError(
                f"Generated public key has {len(public_key_coeffs)} coefficients, but expected {n_value} for N={n_value}."
            )

        # Ensure all coefficients are positive and fit u16 (Falcon Q=12289, so they will)
        # This step might be needed if sk.h can return small negative numbers for coefficients in Z_q.
        # For StarkNet u16, values should be in [0, 12288].
        # Q = 12289
        # processed_coeffs = [c % Q for c in public_key_coeffs] # Ensures positive and within [0, Q-1]
        # For now, assuming sk.h from falcon-py is already in [0,Q-1] or that the contract handles Z_q.
        # Based on your example, direct usage of sk.h is implied.

        print(
            f"Generated Falcon-{n_value} public key with {len(public_key_coeffs)} coefficients. Example: {public_key_coeffs[:3]}..."
        )
        return public_key_coeffs

    except Exception as e:
        print(f"Error generating Falcon public key coefficients for N={n_value}: {e}")
        raise  # Re-raise the exception to be caught by the caller


def generate_claim_signature(sk):
    generate_attestation(sk, "message #1")


if __name__ == "__main__":
    if NODE_URL == "YOUR_STARKNET_NODE_URL":
        print("\n\nCRITICAL: NODE_URL is not set in cairo_interactions.py!")
        print("Please configure it before running the application.\n\n")

    demo.launch()
