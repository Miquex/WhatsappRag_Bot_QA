"""Main entry point for the WhatsApp Agent FastAPI application.

This module initializes the FastAPI application, sets up logging,
and includes the necessary API routers.
"""
from app.core.logging import setup_logger
from fastapi import FastAPI
from app.api.webhook import router
import uvicorn

setup_logger()

app = FastAPI(title='My whatsApp Agent', description='AI agent to Whatsapp', version='0.0.1')
app.include_router(router)


from typing import Dict


@app.get('/health')
def check_health() -> Dict[str, str]:
    """Checks the health of the application.

    Returns:
        Dict[str, str]: A dictionary containing a health status message.
    """
    return {'message': "I'm alive "}


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=True)
