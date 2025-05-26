import gradio as gr
import asyncio

# Import functions from your scripts directory
from cairo_interactions import (
    deploy_new_contract_instance,
    FALCON_KEY_REGISTRY_CONTRACT_HASH,
    NODE_URL,
)

# --- Gradio UI Definition ---
with gr.Blocks(...) as demo:
    # --- State Variables to hold credentials ---
    user_private_key_state = gr.State(None)
    user_account_address_state = gr.State(None)

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
            input_account_address_comp: gr.update(
                value=""
            ),  # Clear input fields on return
            input_private_key_comp: gr.update(value=""),  # Clear input fields on return
            # user_private_key_state: None, # Optionally clear state too
            # user_account_address_state: None,
        }

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
        client_page_group_comp = cp_group_ui  # Assign
        with gr.Column():
            gr.Markdown("<h1 style='text-align: center;'>Client Page</h1>")
            gr.Markdown("This is where client-specific interactions will go.")
            # Add client-specific components here
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

if __name__ == "__main__":
    # Make sure NODE_URL in cairo_interactions.py is set!
    if NODE_URL == "YOUR_STARKNET_NODE_URL":  # Basic check
        print("\n\nCRITICAL: NODE_URL is not set in scripts/cairo_interactions.py!")
        print("Please configure it before running the application.\n\n")
    demo.launch()
