from kernel.logger import get_logger
from kernel.capabilities.models import ApprovalLevel, RiskLevel, CapabilityDefinition

logger = get_logger(__name__)

class ApprovalEngine:
    """
    Evaluates capabilities to ensure they have the necessary authorization
    to be executed by the system autonomously.
    """
    def __init__(self):
        # We can eventually tie this to a user session or workspace permission state.
        pass

    def evaluate(self, definition: CapabilityDefinition, context_permissions: list[str]) -> bool:
        """
        Evaluate if a capability can be executed given the current context permissions.
        Returns True if execution is allowed, False if explicit user approval is required.
        """
        logger.debug(
            "approval_engine.evaluate", 
            capability=definition.capability, 
            approval=definition.approval,
            risk=definition.risk
        )

        if definition.approval == ApprovalLevel.NONE:
            return True
            
        if definition.approval == ApprovalLevel.READ:
            # READ actions are generally safe to run autonomously
            return True
            
        if definition.approval == ApprovalLevel.WRITE:
            # WRITE actions might need 'auto_write' context permission
            if "auto_write" in context_permissions or definition.risk == RiskLevel.LOW:
                return True
            return False
            
        if definition.approval == ApprovalLevel.EXECUTE:
            if "auto_execute" in context_permissions:
                return True
            return False
            
        if definition.approval == ApprovalLevel.ADMIN:
            # ADMIN always requires explicit user confirmation
            return False

        return False

approval_engine = ApprovalEngine()
