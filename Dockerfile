# Use the same Python version as your project
FROM python:3.10

# Set the working directory inside the container
WORKDIR /code

# Copy and install requirements first to leverage Docker cache
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the rest of your application code
COPY . /code/

# Command to run your FastAPI app
# NOTE: Hugging Face requires the port to be 7860
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]