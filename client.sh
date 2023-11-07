# Ensure that we are working from the project dir
pushd PROJECT_PATH
# Activate virtual enviroment
source .venv/bin/activate
# Run client wrapper
python3 src/das_client_wrapper.py
