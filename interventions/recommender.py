class InterventionRecommender:
    def __init__(self):
        self.interventions = {
            "Stable": [
                "Monitor standard entry points.",
                "Maintain regular flow."
            ],
            "Compressing": [
                "Open auxiliary exits to relieve pressure.",
                "Restrict entry flow at major access points.",
                "Deploy stewards to high-density zones."
            ],
            "Volatile": [
                "IMMEDIATE ACTION: Halt entry completely.",
                "Open ALL emergency exits.",
                "Broadcast calm dispersal messages.",
                "Alert emergency services (Standby)."
            ],
            "Agitated": [
                "Emergency Protocol Alpha.",
                "Isolate sectors to prevent surge spread.",
                "Direct flow to wide-area assembly points."
            ],
            "Fragmenting": [
                "Guide subgroups to separate reunion areas.",
                "Identify and remove blockage points."
            ]
        }

    def get_recommendations(self, state):
        return self.interventions.get(state, ["No specific recommendations."])
