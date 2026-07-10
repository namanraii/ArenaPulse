"""Demo-grade fallback data for ArenaPulse.

The production path uses Neo4j, Postgres, Redis, and Gemini. Hackathon demos still
need to run when a judge has none of those services configured, so this module
provides deterministic, realistic AT&T Stadium sample data behind the same API
shape.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models import (
    ChatResponse,
    NavigationRequest,
    NavigationResponse,
    OpsAction,
    OpsActionPriority,
    OpsActionStatus,
    PathNode,
)

STADIUM_ZONES: list[dict] = [
    {"name": "Zone_1", "label": "North Plaza", "capacity": 8200, "density": 0.62},
    {"name": "Zone_2", "label": "East Concourse", "capacity": 7600, "density": 0.88},
    {"name": "Zone_3", "label": "South Ramp", "capacity": 6900, "density": 0.54},
    {"name": "Zone_4", "label": "West Gate Queue", "capacity": 9200, "density": 0.91},
    {"name": "Zone_5", "label": "Transit Bridge", "capacity": 6000, "density": 0.47},
    {"name": "Zone_6", "label": "Accessible Services", "capacity": 2200, "density": 0.39},
    {"name": "Zone_7", "label": "Food Court", "capacity": 5500, "density": 0.81},
    {"name": "Zone_8", "label": "Merchandise", "capacity": 3100, "density": 0.45},
]


def demo_navigation(request: NavigationRequest) -> NavigationResponse:
    """Return a deterministic route that showcases congestion-aware routing."""
    destination = request.destination_intent.lower()
    wants_restroom = any(word in destination for word in ("restroom", "bathroom", "toilet"))
    wants_transit = any(word in destination for word in ("transit", "metro", "bus", "transport"))

    if wants_restroom:
        end = PathNode(
            name="Accessible_Restroom_E2", type="RestRoom", distance_m=35, estimated_time_s=45
        )
        explanation = {
            "en": "Use the east concourse ramp, then turn left at Section 212. This step-free route avoids the crowded West Gate queue and reaches the accessible restroom in about 4 minutes.",
            "es": "Usa la rampa del pasillo este y gira a la izquierda en la Seccion 212. Esta ruta sin escalones evita la fila congestionada de West Gate y llega al bano accesible en unos 4 minutos.",
            "fr": "Prenez la rampe du hall est, puis tournez a gauche a la section 212. Cet itineraire sans marche evite la file dense de West Gate et rejoint les toilettes accessibles en environ 4 minutes.",
        }
    elif wants_transit:
        end = PathNode(
            name="Trinity_Rail_Shuttle", type="TransitStop", distance_m=70, estimated_time_s=90
        )
        explanation = {
            "en": "Head through the South Ramp toward Gate D, then follow signs to the Trinity Rail shuttle. It is currently less crowded than rideshare pickup and keeps you on a step-free path.",
            "es": "Ve por la rampa sur hacia Gate D y sigue las senales al shuttle Trinity Rail. Ahora esta menos lleno que la zona de rideshare y mantiene una ruta sin escalones.",
            "fr": "Passez par la rampe sud vers Gate D, puis suivez les panneaux pour la navette Trinity Rail. Elle est moins chargee que la zone VTC et reste sans marche.",
        }
    else:
        end = PathNode(name="Gate_D", type="Gate", distance_m=60, estimated_time_s=75)
        explanation = {
            "en": "Follow the South Ramp toward Gate D. ArenaPulse is avoiding Zone 4 because density is above 90%, so this route is safer and only adds about 1 minute.",
            "es": "Sigue la rampa sur hacia Gate D. ArenaPulse evita Zone 4 porque la densidad supera el 90%, asi que esta ruta es mas segura y solo agrega cerca de 1 minuto.",
            "fr": "Suivez la rampe sud vers Gate D. ArenaPulse evite Zone 4 car la densite depasse 90 %, ce trajet est donc plus sur et ajoute environ 1 minute.",
        }

    path = [
        PathNode(name=request.start_location, type="Section", distance_m=0, estimated_time_s=0),
        PathNode(name="Zone_3", type="Zone", distance_m=120, estimated_time_s=135),
        PathNode(name="Gate_D_Connector", type="Zone", distance_m=95, estimated_time_s=110),
        end,
    ]
    return NavigationResponse(
        path=path,
        total_distance_m=sum(node.distance_m or 0 for node in path),
        total_time_s=sum(node.estimated_time_s or 0 for node in path),
        step_free=request.step_free,
        explanation=explanation.get(request.language, explanation["en"]),
        avoid_reason="Avoided Zone_4 because live density is 91% and rising.",
    )


def demo_chat(message: str, language: str = "en") -> ChatResponse:
    lower = message.lower()
    if any(word in lower for word in ("restroom", "bathroom", "bano", "toilet")):
        text = {
            "en": "The nearest accessible restroom is by Section 212. Take the east concourse ramp; current walk time is about 4 minutes.",
            "es": "El bano accesible mas cercano esta junto a la Seccion 212. Toma la rampa del pasillo este; el tiempo actual es de unos 4 minutos.",
            "fr": "Les toilettes accessibles les plus proches sont pres de la section 212. Prenez la rampe du hall est; comptez environ 4 minutes.",
        }
        intent = "facilities"
    elif any(word in lower for word in ("metro", "bus", "train", "transit", "leave")):
        text = {
            "en": "Gate D is the best exit for transit right now. The rail shuttle wait is 7 minutes, while rideshare pickup is congested.",
            "es": "Gate D es la mejor salida para transporte ahora. El shuttle al tren tarda 7 minutos, mientras la zona de rideshare esta congestionada.",
            "fr": "Gate D est la meilleure sortie pour le transport actuellement. La navette ferroviaire attend 7 minutes, la zone VTC est saturee.",
        }
        intent = "transit"
    elif any(word in lower for word in ("help", "medical", "injured", "emergency")):
        text = {
            "en": "If this is urgent, alert the nearest steward now. The closest first-aid point is Medical_North near Section 118.",
            "es": "Si es urgente, avisa ahora al voluntario mas cercano. El punto medico mas cercano es Medical_North junto a la Seccion 118.",
            "fr": "Si c'est urgent, prevenez immediatement le steward le plus proche. Le poste de secours le plus proche est Medical_North pres de la section 118.",
        }
        intent = "emergency"
    else:
        text = {
            "en": "I can help with step-free routes, exits, restrooms, transit, match-day policies, and live crowd-safe guidance.",
            "es": "Puedo ayudar con rutas sin escalones, salidas, banos, transporte, reglas del dia de partido y guia segura segun la multitud.",
            "fr": "Je peux aider avec les trajets sans marche, sorties, toilettes, transport, regles de match et conseils selon l'affluence.",
        }
        intent = "general"

    return ChatResponse(
        response=text.get(language, text["en"]),
        sources=[
            {"type": "demo_knowledge_graph", "venue": "AT&T Stadium", "confidence": "grounded"}
        ],
        detected_intent=intent,
        language=language,
    )


def demo_ops_actions() -> list[OpsAction]:
    now = datetime.now(timezone.utc)
    return [
        OpsAction(
            id=1,
            title="Open overflow Gate D and redirect West Gate queue",
            description="Zone_4 is at 91% density with a positive 6% per minute trend.",
            reasoning="Severity is critical, 8,372 fans are affected, and Gate D has spare capacity with a step-free connector.",
            priority=OpsActionPriority.CRITICAL,
            status=OpsActionStatus.PENDING,
            recommended_by="OpsCommanderAgent",
            created_at=now,
            affected_zones=["Zone_4", "Gate_C"],
            affected_population=8372,
            time_to_impact_min=3.0,
        ),
        OpsAction(
            id=2,
            title="Send bilingual volunteer team to East Concourse",
            description="Spanish-language assistance requests increased near Zone_2 after halftime.",
            reasoning="Multilingual support reduces wayfinding friction before the Zone_2 crowd reaches high density.",
            priority=OpsActionPriority.HIGH,
            status=OpsActionStatus.PENDING,
            recommended_by="ConciergeAgent",
            created_at=now,
            affected_zones=["Zone_2"],
            affected_population=2140,
            time_to_impact_min=8.0,
        ),
        OpsAction(
            id=3,
            title="Promote rail shuttle on digital boards",
            description="Rideshare pickup is projected to exceed queue capacity within 12 minutes.",
            reasoning="Rail shuttle wait is 7 minutes and reduces estimated CO2 by 62% versus rideshare for the same corridor.",
            priority=OpsActionPriority.MEDIUM,
            status=OpsActionStatus.PENDING,
            recommended_by="SustainabilityAgent",
            created_at=now,
            affected_zones=["Zone_5"],
            affected_population=1280,
            time_to_impact_min=12.0,
        ),
    ]
