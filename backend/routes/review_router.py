from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.dependencies import get_db
from database.review_storage_service import (
    get_code_reviews, 
    get_code_review_by_id,
    get_code_review_by_commit
)
from schemas.review_schema import CodeReviewResponse


router = APIRouter(
    prefix="/reviews",
    tags=["reviews"]
)


@router.get(
    "/{owner}/{repo}/{pr_number}",
    response_model=list[CodeReviewResponse]
)
def get_reviews(
    owner: str,
    repo: str,
    pr_number: int,
    db: Session = Depends(get_db)
):
    repository = f"{owner}/{repo}"

    return get_code_reviews(
        db=db,
        repository=repository,
        pr_number=pr_number
    )


@router.get(
    "/id/{review_id}",
    response_model=CodeReviewResponse
)
def get_review(
    review_id: int,
    db: Session = Depends(get_db)
):
    return get_code_review_by_id(
        db=db,
        review_id=review_id
    )

@router.get(
    "/{owner}/{repo}/{pr_number}/{commit_sha}",
    response_model=CodeReviewResponse
)
def get_commit_history(
    owner: str,
    repo: str,
    pr_number: int,
    commit_sha: str,
    db: Session = Depends(get_db)
):
    repository = f"{owner}/{repo}"
    commit_history = get_code_review_by_commit(
        db=db,
        repository=repository,
        pr_number=pr_number,
        commit_sha=commit_sha
    )

    if not commit_history:
        raise HTTPException(
            status_code=404, 
            detail=f"Data not found for commit {commit_sha}"
        )
    
    return commit_history