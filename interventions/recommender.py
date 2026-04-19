"""
Intervention Recommender — Severity-graded response plans.

Maps classified crowd states to tiered intervention actions.
Each recommendation includes a priority level, responsible party,
and expected outcome to support decision-making.
"""


class InterventionRecommender:
    """Produces structured intervention plans based on crowd state."""

    def __init__(self):
        self.interventions = {
            "Stable": {
                "level": "ROUTINE",
                "color": "#22c55e",
                "icon": "✅",
                "actions": [
                    {
                        "priority": "Low",
                        "action": "Continue standard monitoring at all entry and exit points.",
                        "owner": "Operations",
                        "outcome": "Maintain situational awareness.",
                    },
                    {
                        "priority": "Low",
                        "action": "Verify communication channels are operational.",
                        "owner": "Communications",
                        "outcome": "Ensure readiness for state escalation.",
                    },
                ],
            },
            "Compressing": {
                "level": "ADVISORY",
                "color": "#f59e0b",
                "icon": "⚠️",
                "actions": [
                    {
                        "priority": "Medium",
                        "action": "Open auxiliary exits to relieve pressure buildup.",
                        "owner": "Crowd Control",
                        "outcome": "Increase outflow capacity by 30–50%.",
                    },
                    {
                        "priority": "Medium",
                        "action": "Restrict entry flow at major access points using metered entry.",
                        "owner": "Gate Teams",
                        "outcome": "Reduce inflow rate to match current capacity.",
                    },
                    {
                        "priority": "Medium",
                        "action": "Deploy stewards to high-density zones for visual monitoring.",
                        "owner": "Field Stewards",
                        "outcome": "Early detection of localized compression.",
                    },
                    {
                        "priority": "Low",
                        "action": "Pre-stage emergency services on standby.",
                        "owner": "Emergency Services",
                        "outcome": "Reduce response time if escalation occurs.",
                    },
                ],
            },
            "Volatile": {
                "level": "URGENT",
                "color": "#ef4444",
                "icon": "🚨",
                "actions": [
                    {
                        "priority": "Critical",
                        "action": "HALT all entry immediately — close gates and barriers.",
                        "owner": "Gate Teams",
                        "outcome": "Stop density increase at source.",
                    },
                    {
                        "priority": "Critical",
                        "action": "Open ALL emergency exits and widen egress corridors.",
                        "owner": "Crowd Control",
                        "outcome": "Maximize outflow to decompress crowd body.",
                    },
                    {
                        "priority": "High",
                        "action": "Broadcast calm dispersal messages on PA and mobile alerts.",
                        "owner": "Communications",
                        "outcome": "Guide orderly movement toward exits.",
                    },
                    {
                        "priority": "High",
                        "action": "Alert emergency services — transition from standby to ACTIVE.",
                        "owner": "Emergency Services",
                        "outcome": "Medical and rescue teams positioned at exits.",
                    },
                ],
            },
            "Agitated": {
                "level": "EMERGENCY",
                "color": "#9333ea",
                "icon": "🆘",
                "actions": [
                    {
                        "priority": "Critical",
                        "action": "Activate Emergency Protocol Alpha — full crowd emergency.",
                        "owner": "Incident Commander",
                        "outcome": "Unified command structure for multi-agency response.",
                    },
                    {
                        "priority": "Critical",
                        "action": "Isolate sectors to prevent surge propagation across zones.",
                        "owner": "Crowd Control",
                        "outcome": "Contain pressure waves within manageable zones.",
                    },
                    {
                        "priority": "Critical",
                        "action": "Direct flow toward wide-area assembly points using barriers.",
                        "owner": "Field Stewards",
                        "outcome": "Reduce density at chokepoints.",
                    },
                    {
                        "priority": "High",
                        "action": "Deploy medical triage at designated safe zones.",
                        "owner": "Emergency Services",
                        "outcome": "Immediate treatment for crush injuries.",
                    },
                ],
            },
            "Fragmenting": {
                "level": "CAUTION",
                "color": "#06b6d4",
                "icon": "🔀",
                "actions": [
                    {
                        "priority": "High",
                        "action": "Guide subgroups to separate reunion areas to prevent re-compression.",
                        "owner": "Field Stewards",
                        "outcome": "Prevent counter-flow collisions at exits.",
                    },
                    {
                        "priority": "Medium",
                        "action": "Identify and remove physical blockage points causing uneven dispersal.",
                        "owner": "Crowd Control",
                        "outcome": "Smooth outflow distribution.",
                    },
                    {
                        "priority": "Medium",
                        "action": "Monitor for secondary compression at alternative exits.",
                        "owner": "Operations",
                        "outcome": "Prevent cascading compression at egress points.",
                    },
                ],
            },
        }

    def get_recommendations(self, state):
        """Return the full intervention plan for a state."""
        base_state = state.split(" (")[0]
        plan = self.interventions.get(base_state)
        if plan:
            return plan
        return self.interventions["Stable"]
