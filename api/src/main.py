import uuid
from fastapi import Depends, FastAPI, HTTPException, APIRouter, Request
from typing import Optional, Sequence
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from fastapi_pagination import Page, add_pagination
from fastapi_pagination.ext.sqlalchemy import paginate

from . import crud, models, schemas
from .db import SessionLocal, engine

models.Base.metadata.create_all(bind=engine) # Scaffold Database if not already done

app = FastAPI()

router = APIRouter(prefix="/apps/{app_id}/users/{user_id}")

# Create a Limiter instance
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

# Add SlowAPI middleware to the application
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


add_pagination(app)

def get_db():
    """FastAPI Dependency Generator for Database"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

########################################################
# Session Routes
########################################################

@router.get("/sessions", response_model=Page[schemas.Session])
def get_sessions(
    request: Request,
    app_id: str,
    user_id: str,
    location_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get All Sessions for a User

    Args:
        app_id (str): The ID of the app representing the client application using honcho
        user_id (str): The User ID representing the user, managed by the user
        location_id (str, optional): Optional Location ID representing the location of a session

    Returns:
        list[schemas.Session]: List of Session objects 

    """
    return paginate(db, crud.get_sessions(db, app_id=app_id, user_id=user_id, location_id=location_id))


@router.post("/sessions", response_model=schemas.Session)
def create_session(
        request: Request, app_id: str, user_id: str, session: schemas.SessionCreate, db: Session = Depends(get_db)
):
    """Create a Session for a User
        
    Args:
        app_id (str): The ID of the app representing the client application using honcho
        user_id (str): The User ID representing the user, managed by the user
        session (schemas.SessionCreate): The Session object containing any metadata and a location ID

    Returns:
        schemas.Session: The Session object of the new Session
        
    """
    value = crud.create_session(db, app_id=app_id, user_id=user_id, session=session)
    return value

@router.put("/sessions/{session_id}", response_model=schemas.Session)
def update_session(
    request: Request, 
    app_id: str,
    user_id: str,
    session_id: uuid.UUID,
    session: schemas.SessionUpdate,
    db: Session = Depends(get_db),
    ):
    """Update the metadata of a Session
    
    Args:
        app_id (str): The ID of the app representing the client application using honcho
        user_id (str): The User ID representing the user, managed by the user
        session_id (int): The ID of the Session to update
        session (schemas.SessionUpdate): The Session object containing any new metadata

    Returns:
        schemas.Session: The Session object of the updated Session

    """
    if session.metadata is None:
        raise HTTPException(status_code=400, detail="Session metadata cannot be empty") # TODO TEST if I can set the metadata to be blank with this 
    try:
        return crud.update_session(db, app_id=app_id, user_id=user_id, session_id=session_id, session=session) 
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

@router.delete("/sessions/{session_id}")
def delete_session(
    request: Request, 
    app_id: str,
    user_id: str,
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    ):
    """Delete a session by marking it as inactive

    Args:
        app_id (str): The ID of the app representing the client application using honcho
        user_id (str): The User ID representing the user, managed by the user
        session_id (int): The ID of the Session to delete

    Returns:
        dict: A message indicating that the session was deleted

    Raises:
        HTTPException: If the session is not found

    """
    response = crud.delete_session(db, app_id=app_id, user_id=user_id, session_id=session_id)
    if response:
        return {"message": "Session deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@router.get("/sessions/{session_id}", response_model=schemas.Session)
def get_session(request: Request, app_id: str, user_id: str, session_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a specific session for a user by ID

    Args:
        app_id (str): The ID of the app representing the client application using honcho
        user_id (str): The User ID representing the user, managed by the user
        session_id (int): The ID of the Session to retrieve

    Returns: 
        schemas.Session: The Session object of the requested Session

    Raises:
        HTTPException: If the session is not found
    """
    honcho_session = crud.get_session(db, app_id=app_id, session_id=session_id, user_id=user_id)
    if honcho_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return honcho_session

########################################################
# Message Routes
########################################################

@router.post(
    "/sessions/{session_id}/messages",
    response_model=schemas.Message
)
def create_message_for_session(
    request: Request, 
    app_id: str,
    user_id: str,
    session_id: uuid.UUID,
    message: schemas.MessageCreate,
    db: Session = Depends(get_db),
):
    """Adds a message to a session

    Args:
        app_id (str): The ID of the app representing the client application using honcho
        user_id (str): The User ID representing the user, managed by the user
        session_id (int): The ID of the Session to add the message to
        message (schemas.MessageCreate): The Message object to add containing the message content and type

    Returns:
        schemas.Message: The Message object of the added message

    Raises:
        HTTPException: If the session is not found

    """
    try:
        return crud.create_message(db, message=message, app_id=app_id, user_id=user_id, session_id=session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

@router.get(
    "/sessions/{session_id}/messages", 
    response_model=Page[schemas.Message]
)
def get_messages_for_session(
    request: Request, 
    app_id: str,
    user_id: str,
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Get all messages for a session
    
    Args:
        app_id (str): The ID of the app representing the client application using honcho
        user_id (str): The User ID representing the user, managed by the user
        session_id (int): The ID of the Session to retrieve

    Returns:
        list[schemas.Message]: List of Message objects

    Raises:
        HTTPException: If the session is not found

    """
    try: 
        return paginate(db, crud.get_messages(db, app_id=app_id, user_id=user_id, session_id=session_id))
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

@router.get(
    "sessions/{session_id}/messages/{message_id}",
    response_model=schemas.Message
)
def get_message(
    request: Request,
    app_id: str,
    user_id: str,
    session_id: uuid.UUID,
    message_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    
    """
    honcho_message = crud.get_message(db, app_id=app_id, session_id=session_id, user_id=user_id, message_id=message_id)
    if honcho_message is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return honcho_message

########################################################
# metamessage routes
########################################################

@router.post(
    "/sessions/{session_id}/metamessages",
    response_model=schemas.Metamessage
)
def create_metamessage(
    request: Request, 
    app_id: str,
    user_id: str,
    session_id: uuid.UUID,
    metamessage: schemas.MetamessageCreate,
    db: Session = Depends(get_db),
):
    """Adds a message to a session

    Args:
        app_id (str): The ID of the app representing the client application using honcho
        user_id (str): The User ID representing the user, managed by the user
        session_id (int): The ID of the Session to add the message to
        message (schemas.MessageCreate): The Message object to add containing the message content and type

    Returns:
        schemas.Message: The Message object of the added message

    Raises:
        HTTPException: If the session is not found

    """
    try:
        return crud.create_metamessage(db, metamessage=metamessage, app_id=app_id, user_id=user_id, session_id=session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

@router.get(
    "/sessions/{session_id}/metamessages", 
    response_model=Page[schemas.Metamessage]
)
def get_metamessages(
    request: Request, 
    app_id: str,
    user_id: str,
    session_id: uuid.UUID,
    message_id: Optional[uuid.UUID] = None, 
    metamessage_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get all messages for a session
    
    Args:
        app_id (str): The ID of the app representing the client application using honcho
        user_id (str): The User ID representing the user, managed by the user
        session_id (int): The ID of the Session to retrieve

    Returns:
        list[schemas.Message]: List of Message objects

    Raises:
        HTTPException: If the session is not found

    """
    try: 
        return paginate(db, crud.get_metamessages(db, app_id=app_id, user_id=user_id, session_id=session_id, message_id=message_id, metamessage_type=metamessage_type))
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")

@router.get("/sessions/{session_id}/metamessages/{metamessage_id}", response_model=schemas.Metamessage)
def get_metamessage(request: Request, app_id: str, user_id: str, session_id: uuid.UUID, message_id: uuid.UUID, metamessage_id: uuid.UUID, db: Session = Depends(get_db)):
    """Get a specific session for a user by ID

    Args:
        app_id (str): The ID of the app representing the client application using honcho
        user_id (str): The User ID representing the user, managed by the user
        session_id (int): The ID of the Session to retrieve

    Returns: 
        schemas.Session: The Session object of the requested Session

    Raises:
        HTTPException: If the session is not found
    """
    honcho_metamessage = crud.get_metamessage(db, app_id=app_id, session_id=session_id, user_id=user_id, message_id=message_id, metamessage_id=metamessage_id)
    if honcho_metamessage is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return honcho_metamessage

########################################################
# collection routes
########################################################

@router.get("/collections/all", response_model=Page[schemas.Collection])
def get_collections(
    request: Request,
    app_id: str,
    user_id: str,
    db: Session = Depends(get_db),
):
    return paginate(db, crud.get_collections(db, app_id=app_id, user_id=user_id))

@router.get("/collections/id/{collection_id}", response_model=schemas.Collection)
def get_collection_by_id(
    request: Request,
    app_id: str,
    user_id: str,
    collection_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> schemas.Collection:
    honcho_collection = crud.get_collection_by_id(db, app_id=app_id, user_id=user_id, collection_id=collection_id)
    if honcho_collection is None:
        raise HTTPException(status_code=404, detail="collection not found or does not belong to user")
    return honcho_collection

@router.get("/collections/name/{name}", response_model=schemas.Collection)
def get_collection_by_name(
    request: Request,
    app_id: str,
    user_id: str,
    name: str,
    db: Session = Depends(get_db)
) -> schemas.Collection:
    honcho_collection = crud.get_collection_by_name(db, app_id=app_id, user_id=user_id, name=name)
    if honcho_collection is None:
        raise HTTPException(status_code=404, detail="collection not found or does not belong to user")
    return honcho_collection

@router.post("/collections", response_model=schemas.Collection)
def create_collection(
    request: Request,
    app_id: str,
    user_id: str,
    collection: schemas.CollectionCreate,
    db: Session = Depends(get_db)
):
    try:
        return crud.create_collection(db, collection=collection, app_id=app_id, user_id=user_id)
    except ValueError:
        raise HTTPException(status_code=406, detail="Error invalid collection configuration - name may already exist")

@router.put("/collections/{collection_id}", response_model=schemas.Collection)
def update_collection(
    request: Request,
    app_id: str,
    user_id: str,
    collection_id: uuid.UUID,
    collection: schemas.CollectionUpdate,
    db: Session = Depends(get_db)
):
    if collection.name is None:
        raise HTTPException(status_code=400, detail="invalid request - name cannot be None")
    try:
        honcho_collection = crud.update_collection(db, collection=collection, app_id=app_id, user_id=user_id, collection_id=collection_id)
    except ValueError:
        raise HTTPException(status_code=406, detail="Error invalid collection configuration - name may already exist")
    return honcho_collection

@router.delete("/collections/{collection_id}")
def delete_collection(
    request: Request,
    app_id: str,
    user_id: str,
    collection_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    response = crud.delete_collection(db, app_id=app_id, user_id=user_id, collection_id=collection_id)
    if response:
        return {"message": "Collection deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="collection not found or does not belong to user")

########################################################
# Document routes
########################################################

@router.get("/collections/{collection_id}/documents", response_model=Page[schemas.Document])
def get_documents(
    request: Request,
    app_id: str,
    user_id: str,
    collection_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    try:
        return paginate(db, crud.get_documents(db, app_id=app_id, user_id=user_id, collection_id=collection_id))
    except ValueError: # TODO can probably remove this exception ok to return empty here
        raise HTTPException(status_code=404, detail="collection not found or does not belong to user")

router.get("/collections/{collection_id}/documents/{document_id}", response_model=schemas.Document)
def get_document(
    request: Request,
    app_id: str,
    user_id: str,
    collection_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    honcho_document = crud.get_document(db, app_id=app_id, user_id=user_id, collection_id=collection_id, document_id=document_id)
    if honcho_document is None:
        raise HTTPException(status_code=404, detail="document not found or does not belong to user")
    return honcho_document


@router.get("/collections/{collection_id}/query", response_model=Sequence[schemas.Document])
def query_documents(
    request: Request,
    app_id: str,
    user_id: str,
    collection_id: uuid.UUID,
    query: str,
    top_k: int = 5,
    db: Session = Depends(get_db)
):
    if top_k is not None and top_k > 50:
        top_k = 50 # TODO see if we need to paginate this 
    return crud.query_documents(db=db, app_id=app_id, user_id=user_id, collection_id=collection_id, query=query, top_k=top_k)

@router.post("/collections/{collection_id}/documents", response_model=schemas.Document)
def create_document(
    request: Request,
    app_id: str,
    user_id: str,
    collection_id: uuid.UUID,
    document: schemas.DocumentCreate,
    db: Session = Depends(get_db)
):
    try:
        return crud.create_document(db, document=document, app_id=app_id, user_id=user_id, collection_id=collection_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="collection not found or does not belong to user")

@router.put("/collections/{collection_id}/documents/{document_id}", response_model=schemas.Document)
def update_document(
    request: Request,
    app_id: str,
    user_id: str,
    collection_id: uuid.UUID,
    document_id: uuid.UUID,
    document: schemas.DocumentUpdate,
    db: Session = Depends(get_db)
):
   if document.content is None and document.metadata is None:
        raise HTTPException(status_code=400, detail="content and metadata cannot both be None")
   return crud.update_document(db, document=document, app_id=app_id, user_id=user_id, collection_id=collection_id, document_id=document_id) 

@router.delete("/collections/{collection_id}/documents/{document_id}")
def delete_document(
    request: Request,
    app_id: str,
    user_id: str,
    collection_id: uuid.UUID,
    document_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    response = crud.delete_document(db, app_id=app_id, user_id=user_id, collection_id=collection_id, document_id=document_id)
    if response:
        return {"message": "Document deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="document not found or does not belong to user")

app.include_router(router)
