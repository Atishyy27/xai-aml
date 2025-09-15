import gradio as gr
from backend.main import app as fastapi_app

# This line tells Gradio to run your existing FastAPI app.
# Your entire API will be available at the root path of the Space.
app = gr.mount_gradio_app(fastapi_app, gr.Blocks(title="XAI-AML API"), "/")

# You can optionally add a simple Gradio interface here for testing,
# but it's not required for the API to work.