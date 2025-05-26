import gradio as gr
import asyncio

# Import functions from your scripts directory
from cairo_interactions import (
    deploy_new_contract_instance,
    FALCON_KEY_REGISTRY_CONTRACT_HASH,
    FALCON_ADDRESS_BASED_VERIFIER_CONTRACT_HASH,
    ESCROW_CONTRACT_HASH,
    NODE_URL,
    call_register_public_key,
    call_escrow_claim,
)
import utils
from falcon import SecretKey
from generate_inputs import generate_attestation


def sepolia_url_from_contract_address(contract_address):
    url = f"https://sepolia.starkscan.co/contract/{contract_address}"
    return url


def mainnnet_url_from_contract_address(contract_address):
    url = f"https://starkscan.co/contract/{contract_address}"
    return url


# --- Gradio UI Definition ---
with gr.Blocks(theme=gr.themes.Soft()) as demo:  # Added a soft theme for better visuals
    # --- State Variables to hold credentials ---
    user_private_key_state = gr.State(None)
    user_account_address_state = gr.State(None)

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
        }

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
                    abi=utils.FALCON_KEY_REGISTRY_ABI,
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
                    abi=utils.FALCON_VERIFIER_ABI,
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
