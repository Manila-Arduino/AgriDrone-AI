from datetime import datetime, timezone
from google.protobuf.timestamp_pb2 import Timestamp
from time import time
import uuid
from typing import Optional, Type, TypeVar, Union
from firebase_admin import credentials, storage, initialize_app, firestore
from pydantic import BaseModel

T = TypeVar("T")


class Firebase:
    def __init__(
        self,
        credentials_filepath: str,
        use_storage=False,
        use_firestore=False,
        storage_bucket="",
    ):
        self.cred = credentials.Certificate(credentials_filepath)
        initialize_app(
            self.cred,
            {"storageBucket": storage_bucket} if use_storage else None,
        )
        self.db = firestore.client() if use_firestore else None

    #! STORAGE
    def upload_storage(
        self, file_path: str, destination_blob_name: str, make_public=True
    ):
        bucket = storage.bucket()
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path)
        if make_public:
            blob.make_public()

        return blob.public_url

    #! FIRESTORE
    def read_firestore(self, doc_path: str, data_type: Type[T]) -> Optional[T]:
        if self.db is None:
            raise ValueError("Firestore is not initialized.")

        doc_ref = self.db.document(doc_path)
        data = doc_ref.get().to_dict()

        if data is None:
            return None

        return data_type(**data)

    def write_firestore(self, doc_path: str, data: Union[BaseModel, dict]):
        if self.db is None:
            raise ValueError("Firestore is not initialized.")

        doc_ref = self.db.document(doc_path)
        if isinstance(data, BaseModel):
            doc_ref.set(data.model_dump(exclude_unset=True))
        else:
            doc_ref.set(data)

    def update_firestore(self, doc_path: str, data: Union[BaseModel, dict]):
        if self.db is None:
            raise ValueError("Firestore is not initialized.")

        doc_ref = self.db.document(doc_path)
        if isinstance(data, BaseModel):
            doc_ref.update(data.model_dump(exclude_unset=True))
        else:
            doc_ref.update(data)

    def exists_firestore(self, doc_path: str) -> bool:
        if self.db is None:
            raise ValueError("Firestore is not initialized.")

        doc_ref = self.db.document(doc_path)
        return doc_ref.get().exists

    #! SERVER TIMESTAMP
    def timestamp(self):
        return datetime.now(timezone.utc)

    #! UUID
    def uuid(self) -> str:
        return uuid.uuid4().hex
