import os
import logging
import firebase_admin as fba

from fastapi import Request, HTTPException, Depends
from firebase_admin import auth
from ..utils import Constants

logger = logging.getLogger(Constants.UVICORN)


class HobuBackend:
    _instance = None
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", None)
    if not creds:
        logger.info("GOOGLE_APPLICATION_CREDENTIALS not set; relying on ADC.")
    else:
        logger.info(f"GOOGLE_APPLICATION_CREDENTIALS set; using credentials: {creds}")

    app = fba.initialize_app()

    @staticmethod
    async def authenticate(request: Request):
        token = request.headers.get("Authorization", None)
        if token is None:
            raise HTTPException(
                status_code=401, detail="Authorization token in header is missing"
            )

        try:
            token = token.replace("Bearer ", "")
            decoded_token = auth.verify_id_token(token)
            return decoded_token
        except Exception as e:
            raise HTTPException(status_code=401, detail=str(e))


def get_current_user(token: dict = Depends(HobuBackend.authenticate)):
    return token
