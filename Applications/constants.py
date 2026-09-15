STUDENT_STAGE_SEQUENCE = {
    # UK's CAS stage has been collapsed into VISA (CAS letter is now a
    # VISA-stage requirement) - all three countries share the same
    # two-stage pipeline.
    "UK": ["ADMISSION", "VISA"],
    "CANADA": ["ADMISSION", "VISA"],
    "USA": ["ADMISSION", "VISA"],
}





STAGE_ADMISSION = "ADMISSION"
STAGE_CAS = "CAS"
STAGE_VISA = "VISA"

STUDENT_STAGE_SEQUENCE_BY_COUNTRY = {
    # UK's CAS stage has been collapsed into VISA.
    "UK": [
        STAGE_ADMISSION,
        STAGE_VISA,
    ],
    "CANADA": [
        STAGE_ADMISSION,
        STAGE_VISA,
    ],
    "USA": [
        STAGE_ADMISSION,
        STAGE_VISA,
    ],
}
