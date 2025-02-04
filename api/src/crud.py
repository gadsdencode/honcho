import uuid
import datetime
from typing import Optional, Sequence

from openai import OpenAI

from sqlalchemy import select, Select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from . import models, schemas

openai_client = OpenAI()

def get_session(db: Session, app_id: str, session_id: uuid.UUID, user_id: Optional[str] = None) -> Optional[models.Session]:
    stmt = select(models.Session).where(models.Session.app_id == app_id).where(models.Session.id == session_id)
    if user_id is not None:
        stmt = stmt.where(models.Session.user_id == user_id)
    session = db.scalars(stmt).one_or_none()
    return session

def get_sessions(
        db: Session, app_id: str, user_id: str, location_id: str | None = None
) -> Select:
    stmt = (
        select(models.Session)
        .where(models.Session.app_id == app_id)
        .where(models.Session.user_id == user_id)
        .where(models.Session.is_active.is_(True))
        .order_by(models.Session.created_at)
    )

    if location_id is not None:
        stmt = stmt.where(models.Session.location_id == location_id)

    return stmt

def create_session(
    db: Session, session: schemas.SessionCreate, app_id: str, user_id: str
) -> models.Session:
    honcho_session = models.Session(
        app_id=app_id,
        user_id=user_id,
        location_id=session.location_id,
        h_metadata=session.metadata,
    )
    db.add(honcho_session)
    db.commit()
    db.refresh(honcho_session)
    return honcho_session


def update_session(
    db: Session, session: schemas.SessionUpdate, app_id: str, user_id: str, session_id: uuid.UUID
) -> bool:
    honcho_session = get_session(db, app_id=app_id, session_id=session_id, user_id=user_id)
    if honcho_session is None:
        raise ValueError("Session not found or does not belong to user")
    if session.metadata is not None: # Need to explicitly be there won't make it empty by default
        honcho_session.h_metadata = session.metadata
    db.commit()
    db.refresh(honcho_session)
    return honcho_session

def delete_session(db: Session, app_id: str, user_id: str, session_id: uuid.UUID) -> bool:
    stmt = (
        select(models.Session)
        .where(models.Session.id == session_id)
        .where(models.Session.app_id == app_id)
        .where(models.Session.user_id == user_id)
    )
    honcho_session = db.scalars(stmt).one_or_none()
    if honcho_session is None:
        return False
    honcho_session.is_active = False
    db.commit()
    return True

def create_message(
        db: Session, message: schemas.MessageCreate, app_id: str, user_id: str, session_id: uuid.UUID
) -> models.Message:
    honcho_session = get_session(db, app_id=app_id, session_id=session_id, user_id=user_id)
    if honcho_session is None:
        raise ValueError("Session not found or does not belong to user")

    honcho_message = models.Message(
        session_id=session_id,
        is_user=message.is_user,
        content=message.content,
    )
    db.add(honcho_message)
    db.commit()
    db.refresh(honcho_message)
    return honcho_message

def get_messages(
    db: Session, app_id: str, user_id: str, session_id: uuid.UUID
) -> Select:
    stmt = (
        select(models.Message)
        .join(models.Session, models.Session.id == models.Message.session_id)
        .where(models.Session.app_id == app_id)
        .where(models.Session.user_id == user_id)
        .where(models.Message.session_id == session_id)
        .order_by(models.Message.created_at)
    )
    return stmt

def get_message(
        db: Session, app_id: str, user_id: str, session_id: uuid.UUID, message_id: uuid.UUID     
) -> Optional[models.Message]:
    stmt = (
        select(models.Message)
        .join(models.Session, models.Session.id == models.Message.session_id)
        .where(models.Session.app_id == app_id)
        .where(models.Session.user_id == user_id)
        .where(models.Message.session_id == session_id)
        .where(models.Message.id == message_id)

    )
    return db.scalars(stmt).one_or_none()

########################################################
# metamessage methods
########################################################

def get_metamessages(db: Session, app_id: str, user_id: str, session_id: uuid.UUID, message_id: Optional[uuid.UUID], metamessage_type: Optional[str] = None) -> Select:
    stmt = (
        select(models.Metamessage)
        .join(models.Message, models.Message.id == models.Metamessage.message_id)
        .join(models.Session, models.Message.session_id == models.Session.id)
        .where(models.Session.app_id == app_id)
        .where(models.Session.user_id == user_id)
        .where(models.Message.session_id == session_id)
        .order_by(models.Metamessage.created_at)
    )
    if message_id is not None:
        stmt = stmt.where(models.Metamessage.message_id == message_id)
    if metamessage_type is not None:
        stmt = stmt.where(models.Metamessage.metamessage_type == metamessage_type)
    return stmt

def get_metamessage(
        db: Session, app_id: str, user_id: str, session_id: uuid.UUID, message_id: uuid.UUID, metamessage_id: uuid.UUID
) -> Optional[models.Metamessage]: 
    stmt = (
         select(models.Metamessage)
        .join(models.Message, models.Message.id == models.Metamessage.message_id)
        .join(models.Session, models.Message.session_id == models.Session.id)
        .where(models.Session.app_id == app_id)
        .where(models.Session.user_id == user_id)
        .where(models.Message.session_id == session_id)
        .where(models.Metamessage.message_id == message_id)
        .where(models.Metamessage.id == metamessage_id)
       
    )
    return db.scalars(stmt).one_or_none()

def create_metamessage(
    db: Session,
    metamessage: schemas.MetamessageCreate,
    app_id: str,
    user_id: str,
    session_id: uuid.UUID,
):
    message = get_message(db, app_id=app_id, session_id=session_id, user_id=user_id, message_id=metamessage.message_id)
    if message is None:
        raise ValueError("Session not found or does not belong to user")

    honcho_metamessage = models.Metamessage(
        message_id=metamessage.message_id,
        metamessage_type=metamessage.metamessage_type,
        content=metamessage.content,
    )

    db.add(honcho_metamessage)
    db.commit()
    db.refresh(honcho_metamessage)
    return honcho_metamessage

########################################################
# collection methods
########################################################

# Should be very similar to the session methods

def get_collections(db: Session, app_id: str, user_id: str) -> Select:
    """Get a distinct list of the names of collections associated with a user"""
    stmt = (
        select(models.Collection)
        .where(models.Collection.app_id == app_id)
        .where(models.Collection.user_id == user_id)
        .order_by(models.Collection.created_at)
    )
    return stmt

def get_collection_by_id(db: Session, app_id: str, user_id: str, collection_id: uuid.UUID) -> Optional[models.Collection]:
    stmt = ( 
        select(models.Collection)
        .where(models.Collection.app_id == app_id)
        .where(models.Collection.user_id == user_id)
        .where(models.Collection.id == collection_id)
    )
    collection = db.scalars(stmt).one_or_none()
    return collection

def get_collection_by_name(db: Session, app_id: str, user_id: str, name: str) -> Optional[models.Collection]:
    stmt = ( 
        select(models.Collection)
        .where(models.Collection.app_id == app_id)
        .where(models.Collection.user_id == user_id)
        .where(models.Collection.name == name)
    )
    collection = db.scalars(stmt).one_or_none()
    return collection

def create_collection(
    db: Session, collection: schemas.CollectionCreate, app_id: str, user_id: str
) -> models.Collection:
    honcho_collection = models.Collection(
        app_id=app_id,
        user_id=user_id,
        name=collection.name,
    )
    try:
        db.add(honcho_collection)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Collection already exists")
    db.refresh(honcho_collection)
    return honcho_collection

def update_collection(
        db: Session, collection: schemas.CollectionUpdate, app_id: str, user_id: str, collection_id: uuid.UUID
) -> models.Collection:
    honcho_collection = get_collection_by_id(db, app_id=app_id, user_id=user_id, collection_id=collection_id)
    if honcho_collection is None:
        raise ValueError("collection not found or does not belong to user")
    try:
        honcho_collection.name = collection.name
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Collection already exists")
    db.refresh(honcho_collection)
    return honcho_collection

def delete_collection(
    db: Session, app_id: str, user_id: str, collection_id: uuid.UUID
) -> bool:
    """
    Delete a Collection and all documents associated with it. Takes advantage of
    the orm cascade feature
    """
    stmt = (
        select(models.Collection)
        .where(models.Collection.id == collection_id)
        .where(models.Collection.app_id == app_id)
        .where(models.Collection.user_id == user_id)
    )
    honcho_collection = db.scalars(stmt).one_or_none()
    if honcho_collection is None:
        return False
    db.delete(honcho_collection)
    db.commit()
    return True

########################################################
# document methods
########################################################

# Should be similar to the messages methods outside of query

def get_documents(
    db: Session, app_id: str, user_id: str, collection_id: uuid.UUID
) -> Select:
    stmt = (
        select(models.Document)
        .join(models.Collection, models.Collection.id == models.Document.collection_id)
        .where(models.Collection.app_id == app_id)
        .where(models.Collection.user_id == user_id)
        .where(models.Document.collection_id == collection_id)
        .order_by(models.Document.created_at)
    )
    return stmt

def get_document(
        db: Session, app_id: str, user_id: str, collection_id: uuid.UUID, document_id: uuid.UUID 
) -> Optional[models.Document]:
    stmt = ( 
        select(models.Document)
        .join(models.Collection, models.Collection.id == models.Document.collection_id)
        .where(models.Collection.app_id == app_id)
        .where(models.Collection.user_id == user_id)
        .where(models.Document.collection_id == collection_id)
        .where(models.Document.id == document_id)
    )

    document = db.scalars(stmt).one_or_none()
    return document


def query_documents(db: Session, app_id: str, user_id: str, collection_id: uuid.UUID, query: str, top_k: int = 5) -> Sequence[models.Document]:
    response = openai_client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    embedding_query = response.data[0].embedding
    stmt = (
            select(models.Document)
            .join(models.Collection, models.Collection.id == models.Document.collection_id)
            .where(models.Collection.app_id == app_id)
            .where(models.Collection.user_id == user_id)
            .where(models.Document.collection_id == collection_id)
            .order_by(models.Document.embedding.cosine_distance(embedding_query))
            .limit(top_k)
            )
    # if metadata is not None:
        # stmt = stmt.where(models.Document.h_metadata.contains(metadata))
    return db.scalars(stmt).all()

def create_document(
        db: Session, document: schemas.DocumentCreate, app_id: str, user_id: str, collection_id: uuid.UUID
) -> models.Document:
    """Embed a message as a vector and create a document"""
    collection = get_collection_by_id(db, app_id=app_id, collection_id=collection_id, user_id=user_id)
    if collection is None:
        raise ValueError("Session not found or does not belong to user")

    response = openai_client.embeddings.create(
            input=document.content, 
            model="text-embedding-3-small"
    )

    embedding = response.data[0].embedding

    honcho_document = models.Document(
        collection_id=collection_id,
        content=document.content,
        h_metadata=document.metadata,
        embedding=embedding
    )
    db.add(honcho_document)
    db.commit()
    db.refresh(honcho_document)
    return honcho_document

def update_document(
        db: Session, document: schemas.DocumentUpdate, app_id: str, user_id: str, collection_id: uuid.UUID, document_id: uuid.UUID
) -> bool:
    honcho_document = get_document(db, app_id=app_id, collection_id=collection_id, user_id=user_id, document_id=document_id)
    if honcho_document is None:
        raise ValueError("Session not found or does not belong to user")
    if document.content is not None:
        honcho_document.content = document.content
        response = openai_client.embeddings.create(
                    input=document.content, 
                    model="text-embedding-3-small"
            )
        embedding = response.data[0].embedding
        honcho_document.embedding = embedding
        honcho_document.created_at = datetime.datetime.now()

    if document.metadata is not None:
        honcho_document.h_metadata = document.metadata
    db.commit()
    db.refresh(honcho_document)
    return honcho_document

def delete_document(db: Session, app_id: str, user_id: str, collection_id: uuid.UUID, document_id: uuid.UUID) -> bool:
    stmt = (
        select(models.Document)
        .join(models.Collection, models.Collection.id == models.Document.collection_id)
        .where(models.Collection.app_id == app_id)
        .where(models.Collection.user_id == user_id)
        .where(models.Document.collection_id == collection_id)
        .where(models.Document.id == document_id)
    )
    document = db.scalars(stmt).one_or_none()
    if document is None:
        return False
    db.delete(document)
    db.commit()
    return True

