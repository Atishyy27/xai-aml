import gradio as gr
from backend.main import app as fastapi_app

# Mount the FastAPI app onto a Gradio Blocks interface
demo = gr.mount_gradio_app(fastapi_app, gr.Blocks(title="XAI-AML API"), "/")

# This is the new, crucial line that starts the server
demo.launch()