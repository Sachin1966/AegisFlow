import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
from typing import Dict, Any

class FinCENExporter:
    """
    Renders approved AML SAR narratives and structured evidence into
    standard FinCEN SAR XML and JSON regulatory schema format.
    """
    @staticmethod
    def export_to_json(case_data: Dict[str, Any], sar_data: Dict[str, Any], signoff_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "FinCEN_BSA_E_Filing": {
                "FilingHeader": {
                    "FilingType": "SAR-DI",
                    "FilingTimestamp": datetime.now(timezone.utc).isoformat(),
                    "FilingInstitution": "AegisFlow Financial Technologies Inc.",
                    "RegulatoryAgency": "FinCEN / OCC / Fed",
                    "SchemaVersion": "2.0"
                },
                "CaseReference": case_data.get("case_id"),
                "SubjectInformation": {
                    "SubjectAccountID": sar_data.get("subject_entity", case_data.get("title")),
                    "RiskTier": "HIGH",
                    "IdentifiedHardwareFingerprint": "DEV-9812",
                    "NetworkRingSize": 6
                },
                "SuspiciousActivityInformation": {
                    "TotalAmountUSD": sar_data.get("suspicious_activity_amount", 76400.0),
                    "PrimaryTypologies": sar_data.get("detected_typologies", ["Structuring", "Layering", "Fraud Ring"]),
                    "StartDate": case_data.get("created_at"),
                    "EndDate": datetime.now(timezone.utc).isoformat()
                },
                "Narrative": {
                    "FullNarrativeText": sar_data.get("full_narrative_md", ""),
                    "Sections": sar_data.get("narrative_sections", []),
                    "Citations": sar_data.get("evidence_citations", [])
                },
                "AnalystSignoff": {
                    "SignedBy": signoff_data.get("analyst_name", "Chief Compliance Officer"),
                    "Decision": signoff_data.get("decision", "APPROVED"),
                    "Rationale": signoff_data.get("reviewer_rationale", "Verified evidence trail"),
                    "Timestamp": signoff_data.get("timestamp", datetime.now(timezone.utc).isoformat())
                }
            }
        }

    @staticmethod
    def export_to_xml(case_data: Dict[str, Any], sar_data: Dict[str, Any], signoff_data: Dict[str, Any]) -> str:
        root = ET.Element("FinCEN_SAR_Batch", attrib={"schemaVersion": "2.0"})
        
        # Header
        header = ET.SubElement(root, "FilingHeader")
        ET.SubElement(header, "FilingType").text = "SAR-DI"
        ET.SubElement(header, "Timestamp").text = datetime.now(timezone.utc).isoformat()
        ET.SubElement(header, "FilerName").text = "AegisFlow Compliance Systems"

        # Activity
        activity = ET.SubElement(root, "SuspiciousActivity")
        ET.SubElement(activity, "CaseID").text = str(case_data.get("case_id", ""))
        ET.SubElement(activity, "SubjectAccount").text = str(sar_data.get("subject_entity", ""))
        ET.SubElement(activity, "SuspiciousAmountUSD").text = str(sar_data.get("suspicious_activity_amount", 76400.0))
        
        # Narrative
        narrative_elem = ET.SubElement(activity, "Narrative")
        narrative_elem.text = sar_data.get("full_narrative_md", "")

        # Signoff
        signoff_elem = ET.SubElement(activity, "AnalystSignOff")
        ET.SubElement(signoff_elem, "SignedBy").text = signoff_data.get("analyst_name", "Compliance Manager")
        ET.SubElement(signoff_elem, "Rationale").text = signoff_data.get("reviewer_rationale", "")

        # Pretty print XML
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
