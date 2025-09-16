# file: app.py
import gradio as gr
from backend.main import app as fastapi_app

# 1. Create the Gradio interface object
gradio_ui = gr.Blocks()

# 2. Mount the FastAPI app onto the Gradio UI.
#    The FastAPI app is the FIRST argument. The Gradio UI is the SECOND.
app = gr.mount_gradio_app(blocks=gradio_ui, app=fastapi_app, path="/")

# 3. Launch the Gradio UI object itself.
gradio_ui.launch()