from Documents.models import Document
from .constants import STUDENT_STAGE_SEQUENCE, STUDENT_STAGE_SEQUENCE_BY_COUNTRY
from .notifications import notify_stage_advanced, notify_final_completion


def advance_stage(application):
    from Applications.constants import STUDENT_STAGE_SEQUENCE_BY_COUNTRY

    sequence = STUDENT_STAGE_SEQUENCE_BY_COUNTRY[application.country]
    current_index = sequence.index(application.stage)

    if current_index < len(sequence) - 1:
        application.stage = sequence[current_index + 1]
        application.save()




def advance_stage_if_complete(application):
    sequence = STUDENT_STAGE_SEQUENCE.get(application.country, [])
    current_stage = application.current_stage

    # get documents for current stage
    docs = application.documents.filter(
        requirement__stage=current_stage
    )

    if not docs.exists():
        return

    if docs.filter(status__in=["MISSING", "REJECTED"]).exists():
        return  # not complete yet

    try:
        idx = sequence.index(current_stage)
        application.current_stage = sequence[idx + 1]
        application.save(update_fields=["current_stage"])
    except IndexError:
        # Final stage completed
        application.status = "SUBMITTED"
        application.save(update_fields=["status"])


def get_stage_sequence(country):
    if country == "UK":
        return ["ADMISSION", "CAS", "VISA"]
    return ["ADMISSION", "VISA"]




# def try_advance_stage(application):
#     """
#     Advances stage ONLY if all documents
#     for the current stage are uploaded.
#     """
#     current_stage = application.stage

#     missing_docs = Document.objects.filter(
#         application=application,
#         requirement__stage=current_stage,
#     ).exclude(status="UPLOADED")

#     if missing_docs.exists():
#         return False

#     return application.advance_stage()



def try_advance_stage(application):
    """
    Handles stage advancement for STUDENT visas
    and completion logic for NON-STUDENT visas.
    """

    # ======================================================
    # 🧳 NON-STUDENT VISA → FLAT COMPLETION FLOW
    # ======================================================
    if application.visa_type != "STUDENT":

        required_docs = application.documents.filter(
            requirement__is_mandatory=True
        )

        if required_docs.filter(status__in=["MISSING", "REJECTED"]).exists():
            return {
                "stage_advanced": False,
                "final_stage_completed": False,
                "stage": application.stage,
                "progress": application.progress,
            }

        # ✅ FINAL COMPLETION
        application.progress = 100
        application.save(update_fields=["progress"])

        notify_final_completion(application)

        return {
            "stage_advanced": False,
            "final_stage_completed": True,
            "stage": application.stage,
            "progress": 100,
        }

    # ======================================================
    # 🎓 STUDENT VISA → STAGE-BASED FLOW
    # ======================================================
    current_stage = application.stage

    required_docs = application.documents.filter(
        requirement__stage=current_stage,
        requirement__is_mandatory=True,
    )

    if required_docs.filter(status__in=["MISSING", "REJECTED"]).exists():
        return {
            "stage_advanced": False,
            "final_stage_completed": False,
            "stage": application.stage,
            "progress": application.progress,
        }

    advanced = application.advance_stage()

    if not advanced:
        # FINAL STAGE (Visa)
        application.progress = 100
        application.save(update_fields=["progress"])

        notify_final_completion(application)

        return {
            "stage_advanced": False,
            "final_stage_completed": True,
            "stage": application.stage,
            "progress": 100,
        }

    notify_stage_advanced(application)

    return {
        "stage_advanced": True,
        "final_stage_completed": False,
        "stage": application.stage,
        "progress": application.progress,
    }


def try_advance_stageWorking(application):
    """
    Advances application stage ONLY if all required documents
    for the current stage are uploaded.
    Returns a dict consumed by frontend.
    """

    current_stage = application.stage

    # Documents required for THIS stage
    required_docs = application.documents.filter(
        requirement__stage=current_stage,
        requirement__is_mandatory=True,
    )

    # Still missing something → do nothing
    if required_docs.filter(status__in=["MISSING", "REJECTED"]).exists():
        return {
            "stage_advanced": False,
            "final_stage_completed": False,
            "stage": application.stage,
            "progress": application.progress,
        }

    # 🚀 Try to advance
    advanced = application.advance_stage()

    if not advanced:
        # This means we were already at FINAL stage
        application.progress = 100
        application.save(update_fields=["progress"])

        # ✅ FINAL COMPLETION NOTIFICATION
        notify_final_completion(application)

        return {
            "stage_advanced": False,
            "final_stage_completed": True,
            "stage": application.stage,
            "progress": 100,
        }

    # ✅ STAGE ADVANCED → SEND NOTIFICATION
    notify_stage_advanced(application)

    return {
        "stage_advanced": True,
        "final_stage_completed": False,
        "stage": application.stage,
        "progress": application.progress,
    }

def try_advance_stageLatest(application):
    """
    Checks if all required documents for the current stage are uploaded.
    Advances stage if possible.

    Returns a structured result for frontend consumption.
    """

    current_stage = application.stage

    # Are there any missing docs for this stage?
    remaining = application.documents.filter(
        requirement__stage=current_stage,
        status__in=["MISSING", "REJECTED"]
    ).exists()

    # ❌ Cannot advance
    if remaining:
        return {
            "stage_advanced": False,
            "final_stage_completed": False,
            "stage": application.stage,
            "progress": application.progress,
        }

    # ✅ Try to advance
    advanced = application.advance_stage()
    notify_stage_advanced(application)
   
    

    # Final stage completed (Visa stage done)
    final_completed = (
        advanced is False and application.progress == 100
    )
    

    return {
        "stage_advanced": advanced,
        "final_stage_completed": final_completed,
        "stage": application.stage,
        "progress": application.progress,
    }

    notify_final_completion(application)
    


def try_advance_stageWW(application):
    """
    Advances application stage if all required docs for current stage are uploaded.
    Returns True if stage advanced, else False.
    """
    current_stage = application.stage

    required_docs = application.documents.filter(
        requirement__stage=current_stage,
        requirement__is_mandatory=True
    )

    if not required_docs.exists():
        return False

    if not required_docs.exclude(status="UPLOADED").exists():
        return application.advance_stage()

    return False

    application.progress = 100
    application.status = "ASSIGNED"  # optional but recommended
    application.save(update_fields=["progress", "status"])

    return {
        "stage_advanced": False,
        "final_stage_completed": True,
    }



def try_advance_stagelast(application):
    stage_sequence = get_stage_sequence(application.country)
    current_stage = application.stage

    # All required docs for current stage
    required_docs = application.documents.filter(
        requirement__stage=current_stage,
        requirement__is_mandatory=True
    )

    if required_docs.exists() and all(
        doc.status == "UPLOADED" for doc in required_docs
    ):
        next_stage = application.get_next_stage()
        if next_stage:
            application.stage = next_stage
            application.save(update_fields=["stage"])
            return True  # ✅ STAGE ADVANCED

    return False  # ❌ STAGE DID NOT ADVANCE

    current_index = stage_sequence.index(current_stage)

    # Move to next stage if exists
    if current_index + 1 < len(stage_sequence):
        application.stage = stage_sequence[current_index + 1]

    # Update progress
    application.progress = int(
        ((current_index + 1) / len(stage_sequence)) * 100
    )

    application.save(update_fields=["stage", "progress"])


def try_advance_stagell(application):
    stage_sequence = get_stage_sequence(application.country)
    current_stage = application.stage

    # All required docs for current stage
    required_docs = application.documents.filter(
        requirement__stage=current_stage,
        requirement__is_mandatory=True
    )

    if not required_docs.exists():
        return

    all_uploaded = required_docs.exclude(status="UPLOADED").exists() is False

    if not all_uploaded:
        return

    current_index = stage_sequence.index(current_stage)

    # Move to next stage if exists
    if current_index + 1 < len(stage_sequence):
        application.stage = stage_sequence[current_index + 1]

    # Update progress
    application.progress = int(
        ((current_index + 1) / len(stage_sequence)) * 100
    )

    application.save(update_fields=["stage", "progress"])


