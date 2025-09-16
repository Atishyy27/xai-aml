# file: app.py
import gradio as gr
from backend.main import app as fastapi_app

# Create the Gradio interface
gradio_ui = gr.Blocks()

# Mount the FastAPI app onto the Gradio interface.
# This 'app' variable is what Hugging Face will automatically find and launch.
app = gr.mount_gradio_app(app=fastapi_app, blocks=gradio_ui, path="/")

# DO NOT add app.launch() or gradio_ui.launch() here.