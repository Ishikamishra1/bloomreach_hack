"""
/scan endpoints — starts a TheraScout opportunity scan and lets the
frontend poll for its result.

POST /scan             -> starts a new scan, returns an execution id
GET  /scan/{execution_id} -> returns status ("RUNNING" | "SUCCEEDED" | "FAILED")
                             and, once done, the ranked opportunities + report link
"""
import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import boto3

router = APIRouter()
sfn = boto3.client("stepfunctions")

STATE_MACHINE_ARN = os.environ.get("STATE_MACHINE_ARN", "")


class ScanRequest(BaseModel):
    therapeutic_area: str = "Colorectal Cancer"


@router.post("")
def start_scan(request: ScanRequest):
    if not STATE_MACHINE_ARN:
        raise HTTPException(status_code=500, detail="STATE_MACHINE_ARN not configured")

    response = sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps({"therapeutic_area": request.therapeutic_area}),
    )
    return {"execution_arn": response["executionArn"]}


@router.get("/{execution_id}")
def get_scan_status(execution_id: str):
    execution_arn = f"{STATE_MACHINE_ARN.replace(':stateMachine:', ':execution:')}:{execution_id}"

    try:
        response = sfn.describe_execution(executionArn=execution_arn)
    except sfn.exceptions.ExecutionDoesNotExist:
        raise HTTPException(status_code=404, detail="Scan not found")

    status = response["status"]
    result = {"status": status}

    if status == "SUCCEEDED":
        result["output"] = json.loads(response.get("output", "{}"))
    elif status == "FAILED":
        result["error"] = response.get("cause", "Unknown failure")

    return result
