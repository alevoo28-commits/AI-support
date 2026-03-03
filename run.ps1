$env:PYTHONPATH = $PSScriptRoot
& "$PSScriptRoot\.venv\Scripts\streamlit.exe" run "$PSScriptRoot\ai_support\ui\streamlit_app.py" @args
