from strands.models import BedrockModel

MODEL_ID = "us.anthropic.claude-sonnet-4-6"


def load_model() -> BedrockModel:
    """
    Get Bedrock model client.
    Uses IAM authentication via the execution role.
    """
    return BedrockModel(model_id=MODEL_ID)
