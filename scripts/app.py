import gradio as gr
import asyncio
import time
import traceback

# Import functions from your scripts directory
from cairo_interactions import (
    deploy_new_contract_instance,
    FALCON_KEY_REGISTRY_CONTRACT_HASH,
    NODE_URL,
    ESCROW_CONTRACT_HASH,
    get_deployer_account,
)

from starknet_py.contract import Contract
from starknet_py.net.full_node_client import FullNodeClient
from utils import FALCON_ESCROW_ABI
# --- Gradio UI Definition ---
with gr.Blocks(...) as demo:
    # --- State Variables to hold credentials and contract info ---
    user_private_key_state = gr.State(None)
    user_account_address_state = gr.State(None)
    deployed_contract_address_state = gr.State(None)
    service_period_state = gr.State(None)
    service_start_block_state = gr.State(None)

    # --- UI Element Definitions (for referencing in callbacks) ---
    # Entry Screen Elements
    input_account_address_comp = (
        gr.Textbox(  # DEFINED (and implicitly added to layout here, at the top)
            label="Your StarkNet Account Address (hex)",
            placeholder="0x...",
            info="Ensure this is the address corresponding to the private key.",
        )
    )
    input_private_key_comp = (
        gr.Textbox(  # DEFINED (and implicitly added to layout here, at the top)
            label="Your Private Key (hex)",
            type="password",
            placeholder="0x...",
            info="Your private key will be used to sign transactions.",
        )
    )

    # Page Group Elements (defined later but need vars now for function returns)
    # These will be assigned to the actual group components when they are created
    entry_screen_group_comp = None
    client_page_group_comp = None
    provider_page_group_comp = None

    # --- Page Navigation and State Update Functions ---
    def set_creds_and_navigate_to_page(
        pk_from_input, aa_from_input, target_page_visible_updates
    ):
        """
        Stores credentials from input fields into state and navigates to the target page.
        pk_from_input: Private key from the Textbox.
        aa_from_input: Account address from the Textbox.
        target_page_visible_updates: A dictionary like {client_page_group_comp: gr.update(visible=True)}
        """
        if not pk_from_input or not aa_from_input:
            # Simple validation - could be improved with gr.Warning or gr.Info
            # For now, we allow navigation but actions later will fail if these are bad
            print("Warning: Private Key or Account Address is empty during navigation.")

        updates = {
            entry_screen_group_comp: gr.update(visible=False),
            client_page_group_comp: gr.update(
                visible=False
            ),  # Ensure other pages are hidden
            provider_page_group_comp: gr.update(visible=False),
            user_private_key_state: pk_from_input,  # Set the state variable
            user_account_address_state: aa_from_input,  # Set the state variable
        }
        updates.update(
            target_page_visible_updates
        )  # Apply visibility for the target page
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
        """Navigates back to entry screen. Credentials in state are preserved."""
        # Optionally clear input fields on entry screen if desired
        return {
            entry_screen_group_comp: gr.update(visible=True),
            client_page_group_comp: gr.update(visible=False),
            provider_page_group_comp: gr.update(visible=False),
            input_account_address_comp: gr.update(value=""),  # Clear input fields on return
            input_private_key_comp: gr.update(value=""),  # Clear input fields on return
            # user_private_key_state: None, # Optionally clear state too
            # user_account_address_state: None,
        }

    async def get_contract_status(contract_address: str, private_key: str, account_address: str):
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
                provider=deployer_account
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
                return "Service not started", 0, service_period_blocks, 0, is_disputed, total_amount
            
            blocks_elapsed = current_block - service_start_block
            blocks_remaining = max(0, service_period_blocks - blocks_elapsed)
            
            status = "In Progress"
            if blocks_remaining == 0:
                status = "Completed"
            elif is_disputed:
                status = "Disputed"
            elif not is_deposited:
                status = "Awaiting Deposit"
            
            return status, blocks_elapsed, service_period_blocks, blocks_remaining, is_disputed, total_amount
            
        except Exception as e:
            print(f"Error getting contract status: {e}")
            traceback.print_exc()
            return f"Error: {str(e)}", 0, 0, 0, False, 0

    async def handle_dispute_action(contract_address: str, private_key: str, account_address: str) -> str:
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
                provider=deployer_account
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

    def update_countdown(
        contract_address: str,
        private_key: str,
        account_address: str
    ):
        """Updates the countdown display"""
        if not contract_address:
            return "No contract deployed", "", gr.update(visible=False), "No amount to display"
            
        status, blocks_elapsed, total_blocks, blocks_remaining, is_disputed, total_amount = asyncio.run(
            get_contract_status(
                contract_address,
                private_key,
                account_address
            )
        )
        
        progress = f"Blocks elapsed: {blocks_elapsed} / {total_blocks}"
        # Calculate refund amount with proper STRK decimal handling (18 decimals)
        if blocks_elapsed > 0 and total_blocks > 0:
            earned_amount = (total_amount * blocks_elapsed) // total_blocks
            earned_amount_strk = earned_amount / (10**18)
            total_amount_strk = total_amount / (10**18)  # Convert from wei to STRK
            amount_refund = f"Amount to refund : {total_amount_strk - earned_amount_strk:.6f} STRK"
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
        if not all([
            private_key, account_address, provider_key_hash, verifier_address,
            key_registry_address, strk_token_address, provider_address, listing_id
        ]):
            return "Error: All fields are required", None, None

        try:
            # Ensure hex strings start with 0x
            provider_key_hash = provider_key_hash if provider_key_hash.startswith("0x") else f"0x{provider_key_hash}"
            verifier_address = verifier_address if verifier_address.startswith("0x") else f"0x{verifier_address}"
            key_registry_address = key_registry_address if key_registry_address.startswith("0x") else f"0x{key_registry_address}"
            strk_token_address = strk_token_address if strk_token_address.startswith("0x") else f"0x{strk_token_address}"
            provider_address = provider_address if provider_address.startswith("0x") else f"0x{provider_address}"
            
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

    # --- Action Handler for Deployment (Provider Page) ---
    def handle_deploy_falcon_registry_action(current_pk_state, current_aa_state):
        """
        Handles the deployment, taking credentials from gr.State.
        """
        if not current_pk_state or not current_aa_state:
            return "Error: Private Key or Account Address not set. Please go back to the main screen and configure them."

        print(
            f"Deploying Falcon Key Registry. Account: {current_aa_state[:10]}... PK used (not shown)"
        )

        # Constructor args are empty for this example
        constructor_args = []

        # Call the async deployment function from cairo_interactions
        result_message, tx_hash = asyncio.run(
            deploy_new_contract_instance(
                FALCON_KEY_REGISTRY_CONTRACT_HASH,
                current_pk_state,  # Pass private key from state
                current_aa_state,  # Pass account address from state
                constructor_args,
            )
        )

        if tx_hash:  # Assuming tx_hash is returned as None on error from deploy_new_contract_instance
            return f"Deployment Initiated!\nContract Address (or precomputed): {result_message}\nTransaction Hash: {tx_hash}"
        else:
            return f"Deployment Failed: {result_message}"

    # --- UI Structure ---
    # Screen 1: Entry Screen (with credential inputs)
    with gr.Group(visible=True) as es_group_ui:
        entry_screen_group_comp = es_group_ui  # Assign the actual component
        gr.Markdown("<h1 style='text-align: center;'>Account Configuration</h1>")
        gr.Markdown(
            "Please enter your StarkNet account details. These will be used to sign transactions."
        )
        # Assign input components to variables defined earlier
        # input_account_address_comp.render()
        # input_private_key_comp.render()

        gr.Markdown(
            "<h1 style='text-align: center; margin-top: 30px; margin-bottom: 20px;'>Choose Your Role</h1>"
        )
        with gr.Row(equal_height=False):
            with gr.Column(scale=1, min_width=250):
                client_btn = gr.Button("Client", variant="primary")
            with gr.Column(scale=1, min_width=250):
                provider_btn = gr.Button("Provider", variant="primary")

        # Custom CSS for button size (optional, from your previous code)
        gr.HTML("""
        <style>
            .gradio-container .gr-button { 
                min-height: 100px !important; /* Adjusted height */
                font-size: 1.2em !important; 
                display: flex;
                justify-content: center;
                align-items: center;
            }
        </style>""")

    # Screen 2: Client Page (Initially Hidden)
    with gr.Group(visible=False) as cp_group_ui:
        client_page_group_comp = cp_group_ui
        with gr.Column():
            gr.Markdown("<h1 style='text-align: center;'>Client Page</h1>")
            
            # Deploy Escrow Section
            with gr.Accordion("Deploy Escrow Contract", open=True):
                gr.Markdown("Deploy a new escrow contract to secure your service agreement.")
                
                # Input fields for constructor arguments
                provider_key_hash_input = gr.Textbox(
                    label="Provider's Key Hash (hex)",
                    placeholder="0x...",
                    info="The hash of the provider's public key"
                )
                total_amount_input = gr.Number(
                    label="Total Amount (STRK)",
                    value=1,
                    minimum=0,
                    info="Amount of STRK tokens to be held in escrow"
                )
                service_period_input = gr.Number(
                    label="Service Period (blocks)",
                    value=100,
                    minimum=1,
                    info="Duration of service in blocks"
                )
                verifier_address_input = gr.Textbox(
                    label="Verifier Contract Address (hex)",
                    placeholder="0x...",
                    info="Address of the Falcon signature verifier contract"
                )
                key_registry_address_input = gr.Textbox(
                    label="Key Registry Contract Address (hex)",
                    placeholder="0x...",
                    info="Address of the Falcon public key registry contract"
                )
                strk_token_address_input = gr.Textbox(
                    label="STRK Token Contract Address (hex)",
                    placeholder="0x...",
                    info="Address of the STRK token contract"
                )
                provider_address_input = gr.Textbox(
                    label="Provider Address (hex)",
                    placeholder="0x...",
                    info="Starknet address of the service provider"
                )
                listing_id_input = gr.Textbox(
                    label="Listing ID",
                    placeholder="Enter the listing ID",
                    info="Identifier for this service agreement"
                )
                
                deploy_escrow_btn = gr.Button("🚀 Deploy Escrow")
                deploy_escrow_output = gr.Textbox(
                    label="Deployment Status", 
                    lines=4,
                    interactive=False
                )

            # Contract Status Section
            with gr.Accordion("Contract Status", open=True):
                status_text = gr.Textbox(
                    label="Status",
                    interactive=False,
                    value="No contract deployed"
                )
                progress_text = gr.Textbox(
                    label="Progress",
                    interactive=False,
                    value=""
                )
                amount_refund = gr.Textbox(
                    label="Amount Status",
                    interactive=False,
                    value="No amount to display"
                )
                dispute_btn = gr.Button(
                    "🚫 Dispute Contract",
                    visible=False
                )
                dispute_output = gr.Textbox(
                    label="Dispute Status",
                    interactive=False,
                    visible=True
                )

            gr.Markdown("---")  # Separator
            back_btn_client = gr.Button("⬅️ Back to Home")

    # Screen 3: Provider Page (Initially Hidden)
    with gr.Group(visible=False) as pp_group_ui:
        provider_page_group_comp = pp_group_ui  # Assign
        with gr.Column():
            gr.Markdown("<h1 style='text-align: center;'>Provider Page</h1>")
            # Deploy Falcon Key Registry Section
            with gr.Accordion("Deploy Falcon Key Registry Contract", open=True):
                # Input fields for constructor arguments could go here if needed
                # e.g., constructor_arg1_input = gr.Textbox(label="Constructor Arg 1")
                deploy_falcon_btn = gr.Button("🚀 Deploy Falcon Key Registry")
                deploy_falcon_output = gr.Textbox(
                    label="Deployment Status", lines=4, interactive=False
                )

            gr.Markdown("---")  # Separator
            # Add more provider-specific actions here

            back_btn_provider = gr.Button("⬅️ Back to Home")

    # --- Event Handlers for Navigation & Actions ---

    # Outputs for navigation from entry screen must include the state variables to update them
    navigation_outputs_from_entry = [
        entry_screen_group_comp,
        client_page_group_comp,
        provider_page_group_comp,
        user_private_key_state,  # Include state variable in outputs
        user_account_address_state,  # Include state variable in outputs
    ]
    # Outputs for navigating back to entry screen (clears input fields)
    navigation_outputs_to_entry = [
        entry_screen_group_comp,
        client_page_group_comp,
        provider_page_group_comp,
        input_account_address_comp,  # To clear its value
        input_private_key_comp,  # To clear its value
        # Note: user_private_key_state and user_account_address_state are NOT listed here
        # so their values will persist when going back to entry. If you want to clear them,
        # add them to this list and modify show_entry_screen_action to return None for them.
    ]

    client_btn.click(
        fn=show_client_page_action,
        inputs=[
            input_private_key_comp,
            input_account_address_comp,
        ],  # Get values from textboxes
        outputs=navigation_outputs_from_entry,
    )

    provider_btn.click(
        fn=show_provider_page_action,
        inputs=[
            input_private_key_comp,
            input_account_address_comp,
        ],  # Get values from textboxes
        outputs=navigation_outputs_from_entry,
    )

    back_btn_client.click(
        fn=show_entry_screen_action, inputs=None, outputs=navigation_outputs_to_entry
    )

    back_btn_provider.click(
        fn=show_entry_screen_action, inputs=None, outputs=navigation_outputs_to_entry
    )

    # Event handler for the deployment button on the Provider page
    deploy_falcon_btn.click(
        fn=handle_deploy_falcon_registry_action,
        inputs=[
            user_private_key_state,
            user_account_address_state,
        ],  # Pass state to the action
        outputs=[deploy_falcon_output],
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
            service_period_state
        ]
    )

    # Event handler for dispute button
    dispute_btn.click(
        fn=lambda x,y,z: asyncio.run(handle_dispute_action(x,y,z)),
        inputs=[
            deployed_contract_address_state,
            user_private_key_state,
            user_account_address_state
        ],
        outputs=[dispute_output]
    )

    # Setup auto-updating countdown
    demo.load(
        fn=update_countdown,
        inputs=[
            deployed_contract_address_state,
            user_private_key_state,
            user_account_address_state
        ],
        outputs=[status_text, progress_text, dispute_btn, amount_refund],
        every=5  # Update every 5 seconds
    )

if __name__ == "__main__":
    # Make sure NODE_URL in cairo_interactions.py is set!
    if NODE_URL == "YOUR_STARKNET_NODE_URL":  # Basic check
        print("\n\nCRITICAL: NODE_URL is not set in scripts/cairo_interactions.py!")
        print("Please configure it before running the application.\n\n")
    
    demo.launch()
