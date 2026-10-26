import csv
import io
from datetime import datetime
from pathlib import Path
from typing import Generator

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, String, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

BASE_DIR = Path(__file__).resolve().parents[1]
DATABASE_URL = f"sqlite:///{BASE_DIR / 'internflow.db'}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    description: Mapped[str | None] = mapped_column(String(1000))
    candidates: Mapped[list["Candidate"]] = relationship(back_populates="project")

class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    status: Mapped[str] = mapped_column(String(30), default="onboarding")
    demo_email: Mapped[bool] = mapped_column(default=False)
    mentor: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    project: Mapped[Project] = relationship(back_populates="candidates")
    reviews: Mapped[list["Review"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")

class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    reviewer: Mapped[str | None] = mapped_column(String(120))
    meeting_link: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(String(4000))
    feedback_status: Mapped[str] = mapped_column(String(30), default="not_generated")
    candidate: Mapped[Candidate] = relationship(back_populates="reviews")

class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"), unique=True)
    content: Mapped[str] = mapped_column(String(8000))
    status: Mapped[str] = mapped_column(String(30), default="pending_approval")
    demo_generated: Mapped[bool] = mapped_column(default=True)
    revision: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    candidate_id: str
    full_name: str
    email: str
    project: str
    status: str
    demo_email: bool
    mentor: str | None
    review_count: int = 0

class CandidateCreate(BaseModel):
    candidate_id: str = Field(pattern=r"^INT[0-9]{3}$")
    full_name: str = Field(min_length=2, max_length=120)
    email: str
    project: str

class ReviewOut(BaseModel):
    id: int
    candidate_id: str
    full_name: str
    project: str
    scheduled_at: datetime | None
    status: str
    reviewer: str | None
    meeting_link: str | None
    feedback_status: str

class ProjectOut(BaseModel):
    id: int
    name: str
    status: str
    candidate_count: int
    description: str | None

class FeedbackOut(BaseModel):
    id: int
    review_id: int
    candidate_id: str
    content: str
    status: str
    demo_generated: bool
    revision: int

class EmailSimulationOut(BaseModel):
    status: str
    integration_mode: str
    recipient: str
    subject: str
    message: str

class DashboardOut(BaseModel):
    total_candidates: int
    active_internships: int
    awaiting_onboarding: int
    upcoming_reviews: int
    completed_reviews: int
    overdue_reviews: int
    feedback_awaiting_approval: int
    emails_simulated: int
    demo_mode: bool
    project_distribution: list[dict[str, int | str]]

app = FastAPI(title="InternFlow AI API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])

def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        yield db

def seed(db: Session) -> None:
    names = ["Automation System", "Data Analytics", "Machine Learning", "Cybersecurity", "Cloud Computing", "Python Automation", "Generative AI"]
    projects = {p.name: p for p in db.scalars(select(Project)).all()}
    for name in names:
        if name not in projects:
            projects[name] = Project(name=name)
            db.add(projects[name])
    db.flush()
    records = [
        ("INT002", "Logesh", "logeshvm2585m@gmail.com", "Automation System"),
        ("INT003", "Rahul Verma", "rahul.verma@example.com", "Data Analytics"),
        ("INT004", "Sneha Reddy", "sneha.reddy@example.com", "Machine Learning"),
        ("INT005", "Arjun Kumar", "arjun.kumar2@example.com", "Cybersecurity"),
        ("INT006", "Divya Patel", "divya.patel@example.com", "Cloud Computing"),
        ("INT007", "Karthik Raj", "karthik.raj@example.com", "Python Automation"),
        ("INT008", "Ananya Singh", "ananya.singh@example.com", "Generative AI"),
    ]
    existing = {c.candidate_id for c in db.scalars(select(Candidate)).all()}
    for cid, name, email, project in records:
        if cid not in existing:
            db.add(Candidate(candidate_id=cid, full_name=name, email=email, project=projects[project], demo_email=email.endswith("@example.com")))
    db.flush()
    seeded_reviews = {"INT003": datetime(2026, 10, 30, 6, 30), "INT004": datetime(2026, 10, 31, 4, 30), "INT005": datetime(2026, 10, 31, 5, 30), "INT006": datetime(2026, 10, 31, 6, 30), "INT007": datetime(2026, 11, 1, 4, 30), "INT008": datetime(2026, 11, 1, 5, 30)}
    for cid, scheduled_at in seeded_reviews.items():
        candidate = db.scalar(select(Candidate).where(Candidate.candidate_id == cid))
        if candidate and not db.scalar(select(Review).where(Review.candidate_id == candidate.id)):
            db.add(Review(candidate=candidate, scheduled_at=scheduled_at))
    db.commit()

@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "demo"}

@app.get("/api/dashboard", response_model=DashboardOut)
def dashboard(db: Session = Depends(get_db)) -> DashboardOut:
    candidates = db.scalars(select(Candidate)).all()
    reviews = db.scalars(select(Review)).all()
    distribution = [{"project": p.name, "count": len(p.candidates)} for p in db.scalars(select(Project).order_by(Project.name)).all() if p.candidates]
    return DashboardOut(total_candidates=len(candidates), active_internships=sum(c.status == "active" for c in candidates), awaiting_onboarding=sum(c.status == "onboarding" for c in candidates), upcoming_reviews=sum(r.status == "scheduled" and r.scheduled_at is not None for r in reviews), completed_reviews=sum(r.status == "completed" for r in reviews), overdue_reviews=0, feedback_awaiting_approval=sum(r.feedback_status == "pending_approval" for r in reviews), emails_simulated=0, demo_mode=True, project_distribution=distribution)

@app.get("/api/candidates", response_model=list[CandidateOut])
def candidates(search: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[CandidateOut]:
    query = select(Candidate).order_by(Candidate.candidate_id)
    if search:
        query = query.where((Candidate.candidate_id.contains(search)) | (Candidate.full_name.contains(search)) | (Candidate.email.contains(search)))
    result = []
    for c in db.scalars(query).all():
        result.append(CandidateOut(candidate_id=c.candidate_id, full_name=c.full_name, email=c.email, project=c.project.name, status=c.status, demo_email=c.demo_email, mentor=c.mentor, review_count=len(c.reviews)))
    return result

@app.post("/api/candidates", response_model=CandidateOut, status_code=201)
def create_candidate(payload: CandidateCreate, db: Session = Depends(get_db)) -> CandidateOut:
    if db.scalar(select(Candidate).where(Candidate.candidate_id == payload.candidate_id)):
        raise HTTPException(409, "Candidate ID already exists")
    project = db.scalar(select(Project).where(Project.name == payload.project))
    if not project:
        raise HTTPException(400, "Project does not exist")
    c = Candidate(candidate_id=payload.candidate_id, full_name=payload.full_name, email=payload.email, project=project, demo_email=payload.email.endswith("@example.com"))
    db.add(c); db.commit(); db.refresh(c)
    return CandidateOut(candidate_id=c.candidate_id, full_name=c.full_name, email=c.email, project=c.project.name, status=c.status, demo_email=c.demo_email, mentor=c.mentor)

@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(candidate_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    candidate = db.scalar(select(Candidate).where(Candidate.candidate_id == candidate_id))
    if not candidate:
        raise HTTPException(404, "Candidate not found")
    db.delete(candidate)
    db.commit()
    return {"status": "deleted", "candidate_id": candidate_id}

@app.put("/api/candidates/{candidate_id}", response_model=CandidateOut)
def update_candidate(candidate_id: str, payload: CandidateCreate, db: Session = Depends(get_db)) -> CandidateOut:
    candidate = db.scalar(select(Candidate).where(Candidate.candidate_id == candidate_id))
    if not candidate:
        raise HTTPException(404, "Candidate not found")
    if payload.candidate_id != candidate_id:
        raise HTTPException(400, "Candidate ID cannot be changed")
    project = db.scalar(select(Project).where(Project.name == payload.project))
    if not project:
        raise HTTPException(400, "Project does not exist")
    candidate.full_name = payload.full_name
    candidate.email = payload.email
    candidate.project = project
    candidate.demo_email = payload.email.endswith("@example.com")
    db.commit(); db.refresh(candidate)
    return CandidateOut(candidate_id=candidate.candidate_id, full_name=candidate.full_name, email=candidate.email, project=candidate.project.name, status=candidate.status, demo_email=candidate.demo_email, mentor=candidate.mentor, review_count=len(candidate.reviews))

@app.get("/api/reviews", response_model=list[ReviewOut])
def reviews(db: Session = Depends(get_db)) -> list[ReviewOut]:
    return [ReviewOut(id=r.id, candidate_id=r.candidate.candidate_id, full_name=r.candidate.full_name, project=r.candidate.project.name, scheduled_at=r.scheduled_at, status=r.status, reviewer=r.reviewer, meeting_link=r.meeting_link, feedback_status=r.feedback_status) for r in db.scalars(select(Review).order_by(Review.scheduled_at)).all()]

@app.get("/api/projects", response_model=list[ProjectOut])
def projects(db: Session = Depends(get_db)) -> list[ProjectOut]:
    return [ProjectOut(id=p.id, name=p.name, status=p.status, candidate_count=len(p.candidates), description=p.description) for p in db.scalars(select(Project).order_by(Project.name)).all()]

@app.post("/api/feedback/{review_id}/generate", response_model=FeedbackOut)
def generate_feedback(review_id: int, db: Session = Depends(get_db)) -> FeedbackOut:
    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(404, "Review not found")
    feedback = db.scalar(select(Feedback).where(Feedback.review_id == review_id))
    source = review.notes.strip() if review.notes else "No mentor observations have been recorded yet."
    content = f"Demo-generated review feedback for {review.candidate.full_name}.\n\nEvidence recorded: {source}\n\nStrengths: No strengths inferred without documented evidence.\nAreas for improvement: Capture concrete tasks, milestones, and outcomes in the next review.\nNext actions: Confirm the next project milestone with the mentor.\nUncertainties: Project objectives and reviewer notes are incomplete."
    if feedback:
        feedback.content = content
        feedback.status = "pending_approval"
        feedback.revision += 1
    else:
        feedback = Feedback(review_id=review_id, content=content)
        db.add(feedback)
    review.feedback_status = "pending_approval"
    db.commit(); db.refresh(feedback)
    return FeedbackOut(id=feedback.id, review_id=review_id, candidate_id=review.candidate.candidate_id, content=feedback.content, status=feedback.status, demo_generated=feedback.demo_generated, revision=feedback.revision)

@app.post("/api/feedback/{feedback_id}/approve", response_model=FeedbackOut)
def approve_feedback(feedback_id: int, db: Session = Depends(get_db)) -> FeedbackOut:
    feedback = db.get(Feedback, feedback_id)
    if not feedback:
        raise HTTPException(404, "Feedback not found")
    feedback.status = "approved"
    review = db.get(Review, feedback.review_id)
    if review:
        review.feedback_status = "approved"
    db.commit(); db.refresh(feedback)
    return FeedbackOut(id=feedback.id, review_id=feedback.review_id, candidate_id=review.candidate.candidate_id, content=feedback.content, status=feedback.status, demo_generated=feedback.demo_generated, revision=feedback.revision)

@app.post("/api/emails/simulate/{candidate_id}", response_model=EmailSimulationOut)
def simulate_email(candidate_id: str, db: Session = Depends(get_db)) -> EmailSimulationOut:
    candidate = db.scalar(select(Candidate).where(Candidate.candidate_id == candidate_id))
    if not candidate:
        raise HTTPException(404, "Candidate not found")
    return EmailSimulationOut(status="simulated", integration_mode="demo", recipient=candidate.email, subject="InternFlow AI review update (demo)", message=f"No real email was sent. This is a demo notification for {candidate.full_name}.")

@app.get("/api/reports/candidates.csv")
def candidate_report(db: Session = Depends(get_db)) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Candidate ID", "Full name", "Email", "Project", "Status", "Review count"])
    for candidate in db.scalars(select(Candidate).order_by(Candidate.candidate_id)).all():
        writer.writerow([candidate.candidate_id, candidate.full_name, candidate.email, candidate.project.name, candidate.status, len(candidate.reviews)])
    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=internflow-candidates.csv"})
