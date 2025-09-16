# file: app.py
import gradio as gr
from backend.main import app as fastapi_app

# 1. Create the main Gradio interface that will act as the server
gradio_app = gr.Blocks()

# 2. Mount your FastAPI application onto the Gradio server
app = gr.mount_gradio_app(gradio_app, fastapi_app, path="/")

# 3. Launch the Gradio interface, which now also serves your FastAPI app
gradio_app.launch()