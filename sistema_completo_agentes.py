"""Entrypoint compatible para Streamlit.

Mantiene el comando histórico:

    streamlit run sistema_completo_agentes.py

La implementación real vive en `ai_support/ui/streamlit_app.py`.
"""

from dotenv import load_dotenv

from ai_support.ui.streamlit_app import main


load_dotenv()


if __name__ == "__main__":
    main()
