from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from datetime import datetime, timedelta
from pydantic import BaseModel,EmailStr
from fastapi.encoders import jsonable_encoder
from database import SessionLocal, engine, Base
from langchain_core.prompts import ChatPromptTemplate
import jwt
from databases.models import TeacherInfo,HistoryUser
from sqlalchemy.orm import Session
import getpass
import os
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

if not os.environ.get("GOOGLE_API_KEY"):
  os.environ["GOOGLE_API_KEY"] = "AIzaSyBNXuiBn15oSCnVdORkUX3miiVswuJqANs"

from langchain.chat_models import init_chat_model


model = init_chat_model(
                        "models/gemini-2.5-pro",
                        model_provider="Google_genai",
                        temperature=0.9,)


SECRET_KEY = "its my secret key "
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


Base.metadata.create_all(bind=engine)

app = FastAPI()

    
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
            db.close()
class user(BaseModel):
    user_name:str
    email:str        


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

@app.post("/get_token/")
async def get_token(data: user, ctx: Session = Depends(get_db)):
    user = ctx.query(TeacherInfo).filter(TeacherInfo.email== data.email).first()
    if not user:
        user = TeacherInfo(email=data.email, name=data.user_name)
        ctx.add(user)
        ctx.commit()
        ctx.refresh(user)

    token_data = {
        "email": data.email,
        "name": data.user_name,
        "id":user.id
        
    }
    token = create_access_token(token_data, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return {"token": token} 

class QueryRequest(BaseModel):
    token: str
    question: str  


@app.get("/verify_token")
def verify_token(token:str):
    try:
        JWT_token=jwt.decode(token,SECRET_KEY,algorithms=[ALGORITHM])
        return JWT_token
    except :
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )    
    
@app.post("/query")
def query(request: QueryRequest, ctx: Session = Depends(get_db)):

    try:
        token_data = verify_token(token=request.token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = token_data.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found in token")

    try:
        messages = [
            SystemMessage(content="""
You are a medical domain assistant. First, determine if the user's question is related to the medical field.

- If it is NOT a medical question, respond with ONLY: "NOT_MEDICAL".
- If it IS a medical question, respond with a helpful and accurate medical answer.

Only respond in one of the two ways:
1. "NOT_MEDICAL"
2. A full medical answer.
"""),
            HumanMessage(content=request.question)
        ]

        result = model.invoke(messages)
        response_text = result.content.strip()

        print("Model response:", response_text)

        if response_text.upper() == "NOT_MEDICAL":
            raise HTTPException(
                status_code=400,
                detail="Only medical-related questions are allowed."
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model error: {str(e)}")

    # Save interaction to DB
    try:
        conversation = {
            "User_QUERY": request.question,
            "AI_RESPONSE": response_text
        }

        history_record = ctx.query(HistoryUser).filter(HistoryUser.user_id == user_id).first()

        if history_record:
            history_record.interaction.append(conversation)
        else:
            history_entry = HistoryUser(
                user_id=user_id,
                interaction=[conversation]
            )
            ctx.add(history_entry)

        ctx.commit()
    except Exception as e:
        ctx.rollback()
        print("DB commit failed:", str(e))
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"response": response_text}

def get_article_history(db, user_id: int):
    return db.query(HistoryUser).filter_by(user_id=user_id).order_by(HistoryUser.user_id.desc()).all()
@app.get("/articles/{article_id}/history")
def read_article_history(user_id: int, db: Session = Depends(get_db)):
    history = get_article_history(db, user_id)
    return history