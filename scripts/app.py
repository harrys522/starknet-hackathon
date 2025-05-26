# app.py
import gradio as gr
import asyncio  # Required for running async functions with Gradio
from cairo_interactions import (
    deploy_new_contract_instance,
    FALCON_KEY_REGISTRY_CLASS_HASH_HEX,
)


def handle_deploy_falcon_registry():
    # For now, we'll deploy with no constructor arguments.
    # If your Falcon Key Registry constructor needs arguments,
    # you'll need to add input fields in Gradio to collect them.
    print(
        f"Attempting to deploy Falcon Key Registry with class hash: {FALCON_KEY_REGISTRY_CLASS_HASH_HEX}"
    )

    # Define constructor arguments here if any. Example:
    # constructor_args = [some_owner_address, initial_param]
    constructor_args = []  # No constructor arguments for this example

    # Call the async deployment function
    # asyncio.run() will execute the async function and block until it completes.
    result_message, tx_hash = asyncio.run(
        deploy_new_contract_instance(
            FALCON_KEY_REGISTRY_CLASS_HASH_HEX, constructor_args
        )
    )

    if tx_hash:
        return f"Deployment Initiated!\nContract Address (or precomputed): {result_message}\nTransaction Hash: {tx_hash}"
    else:
        return f"Deployment Failed: {result_message}"

    # --- Gradio UI Definition (inside `with gr.Blocks(...) as demo:`) ---
    # ... (keep entry_screen_group and client_page_group as is) ...

    # Screen 3: Provider Page (Initially Hidden)
    with gr.Group(visible=False) as pp_group:
        provider_page_group = pp_group  # Assign to global hint
        with gr.Column():
            gr.Markdown("<h1 style='text-align: center;'>Provider Page</h1>")
            gr.Markdown("Provider-specific actions will go here.")

            with gr.Accordion("Deploy New Contracts", open=False):
                gr.Markdown("### Deploy Falcon Key Registry")
                # Add input fields for constructor arguments here if needed
                # Example: owner_address_input = gr.Textbox(label="Owner Address (for constructor)")
                deploy_falcon_btn = gr.Button("🚀 Deploy Falcon Key Registry Contract")
                deploy_falcon_output = gr.Textbox(
                    label="Deployment Status", lines=3, interactive=False
                )

            # Add more provider-specific components here later
            back_btn_provider = gr.Button("⬅️ Back to Home")


# --- UI Element Definitions (will be assigned inside Blocks) ---
# These are declared here so the functions can reference them before they are fully defined
# in the Gradio Blocks context. This is a common pattern for complex Gradio apps.
entry_screen_group = None
client_page_group = None
provider_page_group = None


# --- Page Navigation Functions ---
# These functions return a dictionary mapping components to their new states.
def show_client_page_fn():
    print("Navigating to Client Page")
    return {
        entry_screen_group: gr.update(visible=False),
        client_page_group: gr.update(visible=True),
        provider_page_group: gr.update(visible=False),
    }


def show_provider_page_fn():
    print("Navigating to Provider Page")
    return {
        entry_screen_group: gr.update(visible=False),
        client_page_group: gr.update(visible=False),
        provider_page_group: gr.update(visible=True),
    }


def show_entry_screen_fn():
    print("Navigating to Entry Screen")
    return {
        entry_screen_group: gr.update(visible=True),
        client_page_group: gr.update(visible=False),
        provider_page_group: gr.update(visible=False),
    }


# --- Gradio UI Definition ---
with gr.Blocks(
    theme=gr.themes.Soft(
        primary_hue=gr.themes.colors.blue, secondary_hue=gr.themes.colors.sky
    ),
    title="Cairo App Navigator",
) as demo:
    # Assign components to the globally hinted variables
    # This allows the navigation functions (defined above) to correctly target these components.

    # Screen 1: Entry Screen
    with gr.Group(visible=True) as es_group:
        entry_screen_group = es_group  # Assign to global hint
        gr.Markdown(
            "<h1 style='text-align: center; margin-bottom: 20px;'>Choose Your Role</h1>"
        )
        with gr.Row(
            equal_height=False
        ):  # Using columns for better button sizing control
            with gr.Column(
                scale=1, min_width=250
            ):  # Each column takes roughly half the space
                client_btn = gr.Button(
                    "Client",
                    variant="primary",
                    # elem_classes="large-button" # For potential custom CSS
                    # scale=2 # Makes button taller if row allows
                )
            with gr.Column(scale=1, min_width=250):
                provider_btn = gr.Button(
                    "Provider",
                    variant="primary",
                    # elem_classes="large-button"
                    # scale=2
                )
        gr.HTML("""
        <style>
            /* Attempt to make buttons larger and more square-like */
            /* Gradio's default button styling can be restrictive */
            .gradio-container .gr-button { 
                min-height: 150px !important; /* Make buttons taller */
                font-size: 1.5em !important; /* Larger text */
                display: flex;
                justify-content: center;
                align-items: center;
            }
        </style>
        """)

    # Screen 2: Client Page (Initially Hidden)
    with gr.Group(visible=False) as cp_group:
        client_page_group = cp_group  # Assign to global hint
        with gr.Column():
            gr.Markdown("<h1 style='text-align: center;'>Client Page</h1>")
            gr.Markdown("This is where client-specific interactions will go.")
            # Add more client-specific components here later
            back_btn_client = gr.Button("⬅️ Back to Home")

    # Screen 3: Provider Page (Initially Hidden)
    with gr.Group(visible=False) as pp_group:
        provider_page_group = pp_group  # Assign to global hint
        with gr.Column():
            gr.Markdown("<h1 style='text-align: center;'>Provider Page</h1>")
            gr.Markdown("This is where provider-specific interactions will go.")
            # Add more provider-specific components here later
            back_btn_provider = gr.Button("⬅️ Back to Home")

    # --- Event Handlers for Navigation ---
    # When a button is clicked, its corresponding function is called.
    # The function returns a dictionary specifying which components to update and how.

    # Client button navigates to the client page
    client_btn.click(
        fn=show_client_page_fn,
        inputs=None,  # No inputs needed for this navigation
        outputs=[entry_screen_group, client_page_group, provider_page_group],
    )

    # Provider button navigates to the provider page
    provider_btn.click(
        fn=show_provider_page_fn,
        inputs=None,
        outputs=[entry_screen_group, client_page_group, provider_page_group],
    )

    # Back button on client page navigates to the entry screen
    back_btn_client.click(
        fn=show_entry_screen_fn,
        inputs=None,
        outputs=[entry_screen_group, client_page_group, provider_page_group],
    )

    # Back button on provider page navigates to the entry screen
    back_btn_provider.click(
        fn=show_entry_screen_fn,
        inputs=None,
        outputs=[entry_screen_group, client_page_group, provider_page_group],
    )

if __name__ == "__main__":
    demo.launch()
    # For development with auto-reloading:
    # Run `gradio app.py` in your terminal
