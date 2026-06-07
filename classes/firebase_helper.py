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
        project_id: str = "",
        use_storage=False,
        use_firestore=False,
        storage_bucket="",
    ):
        self.cred = credentials.Certificate(credentials_filepath)
        opts = {}
        if project_id:
            opts["projectId"] = project_id
        if use_storage and storage_bucket:
            opts["storageBucket"] = storage_bucket

        if project_id:
            self.app = initialize_app(self.cred, opts, name=project_id)
        elif len(opts.keys()) > 0:
            self.app = initialize_app(self.cred, opts)
        else:
            self.app = initialize_app(self.cred)

        self.db = firestore.client(app=self.app) if use_firestore else None

    #! STORAGE
    def upload_storage(self, file_path: str, destination_blob_name: str):
        bucket = storage.bucket(app=self.app)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(file_path)
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
