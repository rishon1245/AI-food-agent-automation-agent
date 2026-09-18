import os
import logging

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


logger = logging.getLogger(__name__)


SCOPES = [
    "https://www.googleapis.com/auth/drive"
]


class DriveUploader:

    def __init__(self):

        self.client_file = os.getenv(
            "GOOGLE_OAUTH_CLIENT_FILE",
            "credentials/client_secret.json"
        )

        self.token_file = os.getenv(
            "GOOGLE_OAUTH_TOKEN_FILE",
            "credentials/token.json"
        )

        self.folder_id = os.getenv(
            "GOOGLE_DRIVE_FOLDER_ID"
        )

        if not self.folder_id:
            raise ValueError(
                "GOOGLE_DRIVE_FOLDER_ID is not configured in .env"
            )

        self.service = self._authenticate()

    # ========================================================
    # GOOGLE AUTHENTICATION
    # ========================================================

    def _authenticate(self):

        creds = None

        # Existing token
        if os.path.exists(self.token_file):

            creds = Credentials.from_authorized_user_file(
                self.token_file,
                SCOPES
            )

        # Token invalid/expired
        if not creds or not creds.valid:

            if (
                creds
                and creds.expired
                and creds.refresh_token
            ):

                from google.auth.transport.requests import Request

                creds.refresh(Request())

            else:

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.client_file,
                    SCOPES
                )

                creds = flow.run_local_server(
                    port=0
                )

            # Save token
            token_directory = os.path.dirname(
                self.token_file
            )

            if token_directory:
                os.makedirs(
                    token_directory,
                    exist_ok=True
                )

            with open(
                self.token_file,
                "w"
            ) as token:

                token.write(
                    creds.to_json()
                )

        return build(
            "drive",
            "v3",
            credentials=creds
        )

    # ========================================================
    # FIND EXISTING FILE
    # ========================================================

    def _find_existing_file(self, file_name):

        # Escape single quotes for Drive query
        safe_name = file_name.replace(
            "'",
            "''"
        )

        query = (
            f"name = '{safe_name}' "
            f"and '{self.folder_id}' in parents "
            f"and trashed = false"
        )

        results = self.service.files().list(
            q=query,
            spaces="drive",
            fields="files(id,name,webViewLink)",
            pageSize=10
        ).execute()

        files = results.get(
            "files",
            []
        )

        if files:
            return files[0]

        return None

    # ========================================================
    # UPLOAD / REPLACE
    # ========================================================

    def upload(
        self,
        file_path,
        file_name
    ):

        logger.info(
            "Checking Drive for existing file: %s",
            file_name
        )

        existing_file = self._find_existing_file(
            file_name
        )

        media = MediaFileUpload(
            str(file_path),
            mimetype="image/jpeg",
            resumable=True
        )

        # ----------------------------------------------------
        # EXISTING FILE → REPLACE
        # ----------------------------------------------------

        if existing_file:

            file_id = existing_file["id"]

            logger.info(
                "Existing file found. Replacing: %s",
                file_name
            )

            updated_file = self.service.files().update(
                fileId=file_id,
                media_body=media,
                fields="id,name,webViewLink"
            ).execute()

            logger.info(
                "Successfully replaced: %s",
                file_name
            )

            web_link = updated_file.get(
                "webViewLink"
            )

            if not web_link:

                web_link = (
                    "https://drive.google.com/file/d/"
                    + updated_file["id"]
                    + "/view"
                )

            return web_link

        # ----------------------------------------------------
        # FILE DOES NOT EXIST → CREATE
        # ----------------------------------------------------

        logger.info(
            "No existing file found. Creating new file: %s",
            file_name
        )

        metadata = {
            "name": file_name,
            "parents": [
                self.folder_id
            ]
        }

        uploaded_file = self.service.files().create(
            body=metadata,
            media_body=media,
            fields="id,name,webViewLink"
        ).execute()

        logger.info(
            "Successfully uploaded new file: %s",
            file_name
        )

        web_link = uploaded_file.get(
            "webViewLink"
        )

        if not web_link:

            web_link = (
                "https://drive.google.com/file/d/"
                + uploaded_file["id"]
                + "/view"
            )

        return web_link