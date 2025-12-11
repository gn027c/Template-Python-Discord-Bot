
"""
Copyright (c) 2024 GN027C (GNBot)
Licensed under the Apache License 2.0.
Based on work by Krypton.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    def __init__(self):
        self.token = os.getenv("TOKEN")
        self.prefix = os.getenv("PREFIX", "/") # Default to slash if not specified
        self.invite_link = os.getenv("INVITE_LINK")
        self.application_id = os.getenv("APPLICATION_ID")
        self.owner_ids = set() # Can be expanded to load from env if needed

    def validate(self):
        """Checks if essential configuration is present."""
        if not self.token:
            raise ValueError("Token not found in environment variables.")
        # Add more validation if needed

config = Config()
