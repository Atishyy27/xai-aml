# file: app.py
import gradio as gr
from backend.main import app as fastapi_app

# Create the Gradio interface
gradio_ui = gr.Blocks()

# Mount the FastAPI app onto the Gradio interface.
# The FastAPI app is the FIRST argument. The Gradio UI is the SECOND.
app = gr.mount_gradio_app(app=fastapi_app, blocks=gradio_ui, path="/")

# Launch the server with the correct settings for Hugging Face
gradio_ui.launch(server_name="0.0.0.0", server_port=7860)