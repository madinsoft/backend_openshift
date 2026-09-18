import os
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://tracker_user:StrongPassword123!@localhost:5432/timetracker_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)

    time_logs = relationship("TimeLogModel", back_populates="user")


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(String(255), nullable=True)

    tasks = relationship("TaskModel", back_populates="project")


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), index=True, nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    project = relationship("ProjectModel", back_populates="tasks")
    time_logs = relationship("TimeLogModel", back_populates="task")


class TimeLogModel(Base):
    __tablename__ = "time_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    logged_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("UserModel", back_populates="time_logs")
    task = relationship("TaskModel", back_populates="time_logs")


Base.metadata.create_all(bind=engine)


class UserCreate(BaseModel):
    username: str
    email: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    title: str
    project_id: int


class TaskResponse(BaseModel):
    id: int
    title: str
    project_id: int
    model_config = ConfigDict(from_attributes=True)


class TimeLogCreate(BaseModel):
    user_id: int
    task_id: int
    duration_minutes: int


class TimeLogResponse(BaseModel):
    id: int
    user_id: int
    task_id: int
    duration_minutes: int
    logged_at: datetime
    model_config = ConfigDict(from_attributes=True)


app = FastAPI(title="Time Tracker API", version="1.0.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok"}


@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["Users"])
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(UserModel).filter(UserModel.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    new_user = UserModel(username=user.username, email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/users", response_model=List[UserResponse], tags=["Users"])
def list_users(db: Session = Depends(get_db)):
    return db.query(UserModel).all()


@app.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, tags=["Projects"])
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    db_project = db.query(ProjectModel).filter(ProjectModel.name == project.name).first()
    if db_project:
        raise HTTPException(status_code=400, detail="Project name already exists")
    new_project = ProjectModel(name=project.name, description=project.description)
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return new_project


@app.get("/projects", response_model=List[ProjectResponse], tags=["Projects"])
def list_projects(db: Session = Depends(get_db)):
    return db.query(ProjectModel).all()


@app.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, tags=["Tasks"])
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    project = db.query(ProjectModel).filter(ProjectModel.id == task.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    new_task = TaskModel(title=task.title, project_id=task.project_id)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.get("/tasks", response_model=List[TaskResponse], tags=["Tasks"])
def list_tasks(project_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(TaskModel)
    if project_id is not None:
        query = query.filter(TaskModel.project_id == project_id)
    return query.all()


@app.post("/timelogs", response_model=TimeLogResponse, status_code=status.HTTP_201_CREATED, tags=["TimeLogs"])
def create_timelog(log: TimeLogCreate, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == log.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    task = db.query(TaskModel).filter(TaskModel.id == log.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    new_log = TimeLogModel(
        user_id=log.user_id,
        task_id=log.task_id,
        duration_minutes=log.duration_minutes
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    return new_log


@app.get("/timelogs", response_model=List[TimeLogResponse], tags=["TimeLogs"])
def list_timelogs(
    user_id: Optional[int] = None,
    task_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(TimeLogModel)
    if user_id is not None:
        query = query.filter(TimeLogModel.user_id == user_id)
    if task_id is not None:
        query = query.filter(TimeLogModel.task_id == task_id)
    return query.all()
